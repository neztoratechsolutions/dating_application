
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Optional
import csv
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import SessionLocal

from models.voice_call import VoiceCall
from models.video_call import VideoCall
from models.gift_details import GiftDetail
from models.chat_history import ChatCallLog
from models.game_details import GameSetting, GamePaymentDetail
from models.Withdrawal import Withdrawal


router = APIRouter(
    prefix="/revenue",
    tags=["Revenue Dashboard"]
)


# =========================================================
# DATABASE
# =========================================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =========================================================
# HELPERS
# =========================================================

def to_float(value):
    if value is None:
        return 0.0
    return float(value)


def utc_start(target_date: date):
    return datetime.combine(
        target_date,
        time.min,
        tzinfo=timezone.utc
    )


def utc_end(target_date: date):
    return utc_start(target_date + timedelta(days=1))


def percentage_change(current, previous):
    current = float(current or 0)
    previous = float(previous or 0)

    if previous == 0:
        return 100.0 if current > 0 else 0.0

    return round(
        ((current - previous) / previous) * 100,
        2
    )


def get_period_dates(period, start_date=None, end_date=None):
    today = datetime.now(timezone.utc).date()

    if period == "today":
        return today, today

    if period == "last_7_days":
        return today - timedelta(days=6), today

    if period == "last_30_days":
        return today - timedelta(days=29), today

    if period == "this_month":
        return today.replace(day=1), today

    if period == "custom":
        if not start_date or not end_date:
            raise HTTPException(
                status_code=400,
                detail="start_date and end_date are required for custom range"
            )

        if start_date > end_date:
            raise HTTPException(
                status_code=400,
                detail="start_date cannot be greater than end_date"
            )

        return start_date, end_date

    raise HTTPException(
        status_code=400,
        detail="Invalid period. Use today, last_7_days, last_30_days, this_month or custom"
    )


# =========================================================
# REVENUE SOURCE QUERIES
# =========================================================

def get_revenue_entries(
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
):
    entries = []

    start_dt = utc_start(start_date) if start_date else None
    end_dt = utc_end(end_date) if end_date else None

    def add_entry(source, amount, created_at):
        if amount is None or created_at is None:
            return

        amount = to_float(amount)

        if amount <= 0:
            return

        entries.append({
            "date": created_at.date().isoformat(),
            "source": source,
            "amount": round(amount, 2)
        })

    # -----------------------------------------------------
    # VOICE CALL
    # -----------------------------------------------------

    voice_query = db.query(VoiceCall).filter(
        VoiceCall.status == "completed"
    )

    if hasattr(VoiceCall, "is_free_call"):
        voice_query = voice_query.filter(
            VoiceCall.is_free_call.is_(False)
        )

    if start_dt:
        voice_query = voice_query.filter(
            VoiceCall.created_at >= start_dt
        )

    if end_dt:
        voice_query = voice_query.filter(
            VoiceCall.created_at < end_dt
        )

    for item in voice_query.all():
        add_entry(
            "Voice Call",
            item.revenue,
            item.created_at
        )

    # -----------------------------------------------------
    # VIDEO CALL
    # -----------------------------------------------------

    video_query = db.query(VideoCall).filter(
        VideoCall.status == "completed"
    )

    if start_dt:
        video_query = video_query.filter(
            VideoCall.created_at >= start_dt
        )

    if end_dt:
        video_query = video_query.filter(
            VideoCall.created_at < end_dt
        )

    for item in video_query.all():
        add_entry(
            "Video Call",
            item.revenue,
            item.created_at
        )

    # -----------------------------------------------------
    # CHAT
    # -----------------------------------------------------

    chat_query = db.query(ChatCallLog).filter(
        ChatCallLog.status == "completed"
    )

    if start_dt:
        chat_query = chat_query.filter(
            ChatCallLog.created_at >= start_dt
        )

    if end_dt:
        chat_query = chat_query.filter(
            ChatCallLog.created_at < end_dt
        )

    for item in chat_query.all():
        add_entry(
            "Chat",
            item.amount,
            item.created_at
        )

    # -----------------------------------------------------
    # GIFTS
    # -----------------------------------------------------

    gift_query = db.query(GiftDetail)

    if start_dt:
        gift_query = gift_query.filter(
            GiftDetail.created_at >= start_dt
        )

    if end_dt:
        gift_query = gift_query.filter(
            GiftDetail.created_at < end_dt
        )

    for item in gift_query.all():
        add_entry(
            "Gifts",
            item.earnings,
            item.created_at
        )

    # -----------------------------------------------------
    # COLOUR CONNECT / SCRATCH GAME
    # GamePaymentDetail.paid = entry fee collected
    # -----------------------------------------------------

    game_query = (
        db.query(GamePaymentDetail, GameSetting.name)
        .join(
            GameSetting,
            GamePaymentDetail.game_id == GameSetting.id
        )
        .filter(
            func.lower(GamePaymentDetail.status) == "success"
        )
    )

    if start_dt:
        game_query = game_query.filter(
            GamePaymentDetail.paid_date >= start_dt
        )

    if end_dt:
        game_query = game_query.filter(
            GamePaymentDetail.paid_date < end_dt
        )

    for payment, game_name in game_query.all():
        normalized_name = (game_name or "").strip().lower()

        if "colour connect" in normalized_name or "color connect" in normalized_name:
            source = "Colour Connect"

        elif "scratch" in normalized_name:
            source = "Scratch Game"

        else:
            continue

        add_entry(
            source,
            payment.paid,
            payment.paid_date
        )

    return entries


# =========================================================
# CREATOR PAYOUT HELPERS
# =========================================================

def get_approved_payouts(
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
):
    payout_date = func.coalesce(
        Withdrawal.processed_at,
        Withdrawal.requested_at
    )

    query = db.query(
        func.coalesce(func.sum(Withdrawal.amount), 0)
    ).filter(
        func.lower(Withdrawal.status) == "approved"
    )

    if start_date:
        query = query.filter(
            payout_date >= utc_start(start_date)
        )

    if end_date:
        query = query.filter(
            payout_date < utc_end(end_date)
        )

    return to_float(query.scalar())


def get_pending_withdrawals(db: Session):
    result = db.query(
        func.coalesce(func.sum(Withdrawal.amount), 0),
        func.count(Withdrawal.id)
    ).filter(
        func.lower(Withdrawal.status) == "pending"
    ).first()

    return {
        "amount": round(to_float(result[0]), 2),
        "transactions": result[1] or 0
    }


def get_revenue_total(entries):
    return round(
        sum(item["amount"] for item in entries),
        2
    )


def get_source_summary(entries):
    summary = {}

    for item in entries:
        source = item["source"]

        if source not in summary:
            summary[source] = {
                "source": source,
                "amount": 0.0,
                "transactions": 0
            }

        summary[source]["amount"] += item["amount"]
        summary[source]["transactions"] += 1

    total = get_revenue_total(entries)

    result = []

    for item in summary.values():
        amount = round(item["amount"], 2)

        result.append({
            "source": item["source"],
            "amount": amount,
            "transactions": item["transactions"],
            "percentage": round(
                (amount / total) * 100,
                2
            ) if total else 0.0
        })

    return sorted(
        result,
        key=lambda x: x["amount"],
        reverse=True
    )


def get_daily_summary(entries, start_date, end_date, payouts_by_date=None):
    payouts_by_date = payouts_by_date or {}

    daily = {}

    current_date = start_date

    while current_date <= end_date:
        key = current_date.isoformat()

        daily[key] = {
            "date": key,
            "revenue": 0.0,
            "transactions": 0,
            "creator_payout": round(
                payouts_by_date.get(key, 0.0),
                2
            ),
            "platform_profit": 0.0
        }

        current_date += timedelta(days=1)

    for item in entries:
        key = item["date"]

        if key not in daily:
            continue

        daily[key]["revenue"] += item["amount"]
        daily[key]["transactions"] += 1

    for item in daily.values():
        item["revenue"] = round(item["revenue"], 2)

        item["platform_profit"] = round(
            item["revenue"] - item["creator_payout"],
            2
        )

    return list(daily.values())


def get_payouts_by_date(
    db: Session,
    start_date: date,
    end_date: date
):
    payout_date = func.coalesce(
        Withdrawal.processed_at,
        Withdrawal.requested_at
    )

    rows = db.query(
        func.date(payout_date),
        func.coalesce(func.sum(Withdrawal.amount), 0)
    ).filter(
        func.lower(Withdrawal.status) == "approved",
        payout_date >= utc_start(start_date),
        payout_date < utc_end(end_date)
    ).group_by(
        func.date(payout_date)
    ).all()

    return {
        row[0].isoformat(): to_float(row[1])
        for row in rows
        if row[0] is not None
    }


# =========================================================
# REVENUE DASHBOARD API
# =========================================================

@router.get("/")
def get_revenue_dashboard(
    period: str = Query(
        "last_30_days",
        description="today, last_7_days, last_30_days, this_month, custom"
    ),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    export_format: Optional[str] = Query(
        None,
        description="Use csv to download the filtered revenue ledger"
    ),
    db: Session = Depends(get_db)
):
    try:
        today = datetime.now(timezone.utc).date()
        yesterday = today - timedelta(days=1)

        # Selected filter range
        selected_start, selected_end = get_period_dates(
            period,
            start_date,
            end_date
        )

        # -------------------------------------------------
        # SELECTED PERIOD DATA
        # -------------------------------------------------

        selected_entries = get_revenue_entries(
            db,
            selected_start,
            selected_end
        )

        selected_revenue = get_revenue_total(
            selected_entries
        )

        selected_payout = get_approved_payouts(
            db,
            selected_start,
            selected_end
        )

        selected_profit = round(
            selected_revenue - selected_payout,
            2
        )

        # -------------------------------------------------
        # TODAY / YESTERDAY
        # -------------------------------------------------

        today_entries = get_revenue_entries(
            db,
            today,
            today
        )

        yesterday_entries = get_revenue_entries(
            db,
            yesterday,
            yesterday
        )

        today_revenue = get_revenue_total(today_entries)
        yesterday_revenue = get_revenue_total(yesterday_entries)

        day_before = yesterday - timedelta(days=1)

        day_before_entries = get_revenue_entries(
            db,
            day_before,
            day_before
        )

        day_before_revenue = get_revenue_total(
            day_before_entries
        )

        # -------------------------------------------------
        # WEEKLY REVENUE
        # Monday to Sunday
        # -------------------------------------------------

        week_start = today - timedelta(days=today.weekday())
        previous_week_start = week_start - timedelta(days=7)
        previous_week_end = week_start - timedelta(days=1)

        weekly_entries = get_revenue_entries(
            db,
            week_start,
            today
        )

        previous_week_entries = get_revenue_entries(
            db,
            previous_week_start,
            previous_week_end
        )

        weekly_revenue = get_revenue_total(weekly_entries)
        previous_week_revenue = get_revenue_total(
            previous_week_entries
        )

        # -------------------------------------------------
        # MONTHLY REVENUE
        # -------------------------------------------------

        month_start = today.replace(day=1)

        previous_month_last_day = month_start - timedelta(days=1)
        previous_month_start = previous_month_last_day.replace(day=1)

        monthly_entries = get_revenue_entries(
            db,
            month_start,
            today
        )

        previous_month_entries = get_revenue_entries(
            db,
            previous_month_start,
            previous_month_last_day
        )

        monthly_revenue = get_revenue_total(
            monthly_entries
        )

        previous_month_revenue = get_revenue_total(
            previous_month_entries
        )

        # -------------------------------------------------
        # LIFETIME REVENUE
        # -------------------------------------------------

        lifetime_entries = get_revenue_entries(db)

        total_revenue = get_revenue_total(
            lifetime_entries
        )

        total_creator_payouts = get_approved_payouts(db)

        total_platform_profit = round(
            total_revenue - total_creator_payouts,
            2
        )

        # -------------------------------------------------
        # CREATOR PAYOUTS / PENDING WITHDRAWALS
        # -------------------------------------------------

        monthly_creator_payouts = get_approved_payouts(
            db,
            month_start,
            today
        )

        pending_withdrawals = get_pending_withdrawals(db)

        # -------------------------------------------------
        # SOURCE-WISE REVENUE
        # Lifetime breakdown
        # -------------------------------------------------

        revenue_by_source = get_source_summary(
            lifetime_entries
        )

        selected_source_summary = get_source_summary(
            selected_entries
        )

        # -------------------------------------------------
        # DAILY TREND
        # -------------------------------------------------

        payouts_by_date = get_payouts_by_date(
            db,
            selected_start,
            selected_end
        )

        daily_trend = get_daily_summary(
            selected_entries,
            selected_start,
            selected_end,
            payouts_by_date
        )

        # -------------------------------------------------
        # MONTHLY REVENUE & PROFIT
        # Current year Jan to Dec
        # -------------------------------------------------

        year_start = date(today.year, 1, 1)
        year_end = date(today.year, 12, 31)

        year_entries = get_revenue_entries(
            db,
            year_start,
            today
        )

        year_payouts = get_payouts_by_date(
            db,
            year_start,
            today
        )

        monthly_data = []

        for month in range(1, 13):
            month_revenue = sum(
                item["amount"]
                for item in year_entries
                if date.fromisoformat(item["date"]).month == month
            )

            month_payout = sum(
                amount
                for payout_date, amount in year_payouts.items()
                if date.fromisoformat(payout_date).month == month
            )

            monthly_data.append({
                "month": date(today.year, month, 1).strftime("%b"),
                "revenue": round(month_revenue, 2),
                "creator_payout": round(month_payout, 2),
                "platform_profit": round(
                    month_revenue - month_payout,
                    2
                )
            })

        # -------------------------------------------------
        # REVENUE LEDGER
        # -------------------------------------------------

        ledger = []

        for item in sorted(
            selected_entries,
            key=lambda x: x["date"],
            reverse=True
        ):
            ledger.append({
                "date": item["date"],
                "source": item["source"],
                "amount": item["amount"],
                "transactions": 1,

                # Source-wise payout allocation is not stored
                # in the supplied models.
                "creator_payout": None,
                "platform_profit": None
            })

        # -------------------------------------------------
        # CSV EXPORT
        # -------------------------------------------------

        if export_format:
            if export_format.lower() != "csv":
                raise HTTPException(
                    status_code=400,
                    detail="Currently only csv export is supported"
                )

            output = StringIO()
            writer = csv.writer(output)

            writer.writerow([
                "Date",
                "Source",
                "Amount",
                "Transactions",
                "Creator Payout",
                "Platform Profit"
            ])

            for item in ledger:
                writer.writerow([
                    item["date"],
                    item["source"],
                    item["amount"],
                    item["transactions"],
                    item["creator_payout"] or "",
                    item["platform_profit"] or ""
                ])

            output.seek(0)

            filename = (
                f"revenue_ledger_{selected_start}_{selected_end}.csv"
            )

            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={
                    "Content-Disposition": (
                        f'attachment; filename="{filename}"'
                    )
                }
            )

        # -------------------------------------------------
        # FINAL RESPONSE
        # -------------------------------------------------

        return {
            "status": True,
            "message": "Revenue dashboard retrieved successfully",

            "filters": {
                "period": period,
                "start_date": selected_start.isoformat(),
                "end_date": selected_end.isoformat()
            },

            "summary": {
                "todays_revenue": {
                    "amount": round(today_revenue, 2),
                    "change_percentage": percentage_change(
                        today_revenue,
                        yesterday_revenue
                    )
                },

                "yesterdays_revenue": {
                    "amount": round(yesterday_revenue, 2),
                    "change_percentage": percentage_change(
                        yesterday_revenue,
                        day_before_revenue
                    )
                },

                "weekly_revenue": {
                    "amount": round(weekly_revenue, 2),
                    "change_percentage": percentage_change(
                        weekly_revenue,
                        previous_week_revenue
                    )
                },

                "monthly_revenue": {
                    "amount": round(monthly_revenue, 2),
                    "change_percentage": percentage_change(
                        monthly_revenue,
                        previous_month_revenue
                    )
                },

                "total_revenue": {
                    "amount": round(total_revenue, 2),
                    "change_percentage": None
                },

                "platform_profit": {
                    "amount": round(total_platform_profit, 2)
                },

                "creator_payouts": {
                    "amount": round(
                        monthly_creator_payouts,
                        2
                    )
                },

                "pending_withdrawals": pending_withdrawals
            },

            "selected_period": {
                "revenue": round(selected_revenue, 2),
                "creator_payout": round(selected_payout, 2),
                "platform_profit": round(selected_profit, 2)
            },

            "revenue_by_source": revenue_by_source,

            "selected_period_source_breakdown": (
                selected_source_summary
            ),

            "revenue_trend": daily_trend,

            "daily_revenue": [
                {
                    "date": item["date"],
                    "revenue": item["revenue"],
                    "transactions": item["transactions"]
                }
                for item in daily_trend
            ],

            "monthly_revenue_profit": monthly_data,

            "creator_payout_trend": [
                {
                    "date": item["date"],
                    "creator_payout": item["creator_payout"],
                    "platform_profit": item["platform_profit"]
                }
                for item in daily_trend
            ],

            "revenue_ledger": {
                "total_entries": len(ledger),
                "data": ledger
            }
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve revenue dashboard: {str(e)}"
        )
