
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, aliased

from database import get_db
from models.voice_call import VoiceCall
from models.video_call import VideoCall
from models.users import User
from models.state import State


# ==========================================================
# ROUTERS
# ==========================================================

router = APIRouter(
    prefix="/admin/voice-calls",
    tags=["Admin Voice Calls Dashboard"],
)

video_dashboard_router = APIRouter(
    prefix="/admin/video-calls",
    tags=["Admin Video Calls Dashboard"],
)


ACTIVE_STATUSES = ["ringing", "ongoing"]
FAILED_STATUSES = [
    "failed", "rejected", "missed", "cancelled", "canceled"
]


# ==========================================================
# COMMON HELPERS
# ==========================================================

def utc_now():
    return datetime.now(timezone.utc)


def format_duration(seconds):
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)

    if hours:
        return f"{hours}h {minutes}m {secs}s"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def get_call_seconds(call, now=None):
    """
    Calculate duration from start_time and end_time where available.
    Existing call.duration is assumed to be stored in hours.
    """
    now = now or utc_now()

    if call.start_time:
        start = call.start_time

        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)

        if call.end_time:
            end = call.end_time

            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)
        elif (call.status or "").lower() in ACTIVE_STATUSES:
            end = now
        else:
            end = None

        if end:
            return max(0, int((end - start).total_seconds()))

    return max(0, int(float(call.duration or 0) * 3600))


def get_date_range(date_filter):
    today = utc_now().date()

    if date_filter == "today":
        return today, today
    if date_filter == "last_7_days":
        return today - timedelta(days=6), today
    if date_filter == "last_30_days":
        return today - timedelta(days=29), today

    return None, None


def apply_call_filters(
    query,
    call_model,
    Customer,
    Creator,
    date_filter,
    state_id,
    creator_id,
    call_status,
    search,
):
    start_date, end_date = get_date_range(date_filter)

    if start_date and end_date:
        query = query.filter(
            func.date(call_model.created_at) >= start_date,
            func.date(call_model.created_at) <= end_date,
        )

    if state_id is not None:
        query = query.filter(Creator.state_id == state_id)

    if creator_id is not None:
        query = query.filter(call_model.creator_id == creator_id)

    if call_status:
        query = query.filter(
            func.lower(call_model.status) == call_status.strip().lower()
        )

    if search and search.strip():
        search_value = f"%{search.strip()}%"
        query = query.filter(
            or_(
                call_model.call_id.ilike(search_value)
                if hasattr(call_model, "call_id")
                else call_model.video_call_id.ilike(search_value),
                Customer.display_name.ilike(search_value),
                Creator.display_name.ilike(search_value),
            )
        )

    return query


def build_analytics(db, call_model, now):
    today = now.date()
    chart_start = today - timedelta(days=6)

    chart_calls = (
        db.query(call_model)
        .filter(
            func.date(call_model.created_at) >= chart_start,
            func.date(call_model.created_at) <= today,
        )
        .all()
    )

    daily = {}

    for offset in range(7):
        day = chart_start + timedelta(days=offset)
        daily[day] = {
            "date": day.isoformat(),
            "total_calls": 0,
            "revenue": 0.0,
            "coins": 0,
            "duration_seconds": 0,
        }

    for call in chart_calls:
        if not call.created_at:
            continue

        day = call.created_at.date()

        if day not in daily:
            continue

        daily[day]["total_calls"] += 1
        daily[day]["revenue"] += float(call.revenue or 0)
        daily[day]["coins"] += int(call.coins or 0)
        daily[day]["duration_seconds"] += get_call_seconds(call, now)

    daily_call_volume = []
    revenue_by_calls = []
    average_duration_trend = []

    for item in daily.values():
        total_calls = item["total_calls"]
        duration_seconds = item["duration_seconds"]

        daily_call_volume.append({
            "date": item["date"],
            "total_calls": total_calls,
        })

        revenue_by_calls.append({
            "date": item["date"],
            "revenue": round(item["revenue"], 2),
        })

        average_seconds = (
            duration_seconds / total_calls if total_calls else 0
        )

        average_duration_trend.append({
            "date": item["date"],
            "average_duration_seconds": round(average_seconds, 2),
            "average_duration_minutes": round(average_seconds / 60, 2),
            "average_duration": format_duration(average_seconds),
        })

    return {
        "daily_call_volume": daily_call_volume,
        "revenue_by_calls": revenue_by_calls,
        "average_duration_trend": average_duration_trend,
    }


def build_dashboard(
    db,
    call_model,
    call_id_field,
    date_filter,
    state_id,
    creator_id,
    call_status,
    search,
    page,
    limit,
    call_type,
):
    now = utc_now()
    today = now.date()

    Customer = aliased(User)
    Creator = aliased(User)

    query = (
        db.query(call_model, Customer, Creator)
        .join(Customer, call_model.customer_id == Customer.id)
        .join(Creator, call_model.creator_id == Creator.id)
    )

    query = apply_call_filters(
        query=query,
        call_model=call_model,
        Customer=Customer,
        Creator=Creator,
        date_filter=date_filter,
        state_id=state_id,
        creator_id=creator_id,
        call_status=call_status,
        search=search,
    )

    # Today's summary uses the same optional filters,
    # but always restricts the date to today.
    today_query = (
        db.query(call_model, Customer, Creator)
        .join(Customer, call_model.customer_id == Customer.id)
        .join(Creator, call_model.creator_id == Creator.id)
        .filter(func.date(call_model.created_at) == today)
    )

    if state_id is not None:
        today_query = today_query.filter(Creator.state_id == state_id)

    if creator_id is not None:
        today_query = today_query.filter(
            call_model.creator_id == creator_id
        )

    if call_status:
        today_query = today_query.filter(
            func.lower(call_model.status) == call_status.strip().lower()
        )

    if search and search.strip():
        search_value = f"%{search.strip()}%"
        today_query = today_query.filter(
            or_(
                getattr(call_model, call_id_field).ilike(search_value),
                Customer.display_name.ilike(search_value),
                Creator.display_name.ilike(search_value),
            )
        )

    today_records = today_query.all()
    today_calls = [call for call, _, _ in today_records]

    today_seconds = sum(
        get_call_seconds(call, now) for call in today_calls
    )

    average_seconds = (
        today_seconds / len(today_calls) if today_calls else 0
    )

    today_revenue = sum(
        (Decimal(str(call.revenue or 0)) for call in today_calls),
        Decimal("0.00"),
    )

    # Count and paginate the filtered query.
    total_records = query.count()
    total_pages = (total_records + limit - 1) // limit

    rows = (
        query
        .order_by(call_model.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    calls = []

    for call, customer, creator in rows:
        state = None

        if creator and creator.state_id is not None:
            state = (
                db.query(State)
                .filter(State.id == creator.state_id)
                .first()
            )

        seconds = get_call_seconds(call, now)

        calls.append({
            "id": call.id,
            call_id_field: getattr(call, call_id_field),

            "customer_id": call.customer_id,
            "customer_name": customer.display_name if customer else None,

            "creator_id": call.creator_id,
            "creator_name": creator.display_name if creator else None,

            "state_id": creator.state_id if creator else None,
            "state_name": state.state_name if state else None,

            "caller_id": getattr(call, "caller_id", None),
            "receiver_id": getattr(call, "receiver_id", None),

            "start_time": call.start_time,
            "end_time": call.end_time,

            "duration_seconds": seconds,
            "duration": format_duration(seconds),

            "coins": int(call.coins or 0),
            "revenue": round(float(call.revenue or 0), 2),

            "status": call.status,
            "is_free_call": getattr(call, "is_free_call", False),
            "created_at": call.created_at,
            "updated_at": getattr(call, "updated_at", None),
        })

    analytics = build_analytics(db, call_model, now)

    summary = {
        f"total_{call_type}_calls_today": len(today_calls),
        "total_calls": total_records,
        "active_calls": sum(
            1 for call in today_calls
            if (call.status or "").lower() in ACTIVE_STATUSES
        ),
        "failed_calls": sum(
            1 for call in today_calls
            if (call.status or "").lower() in FAILED_STATUSES
        ),
        "total_minutes": round(today_seconds / 60, 2),
        "average_duration_seconds": round(average_seconds, 2),
        "average_duration": format_duration(average_seconds),
        "total_coins": sum(int(call.coins or 0) for call in today_calls),
        "revenue": float(today_revenue),
    }

    return {
        "status": 200,
        "message": f"{call_type.title()} calls dashboard fetched successfully",
        "summary": summary,
        "analytics": analytics,
        "filters": {
            "date_filter": date_filter,
            "state_id": state_id,
            "creator_id": creator_id,
            "call_status": call_status,
            "search": search,
        },
        "pagination": {
            "page": page,
            "limit": limit,
            "total_records": total_records,
            "total_pages": total_pages,
        },
        "calls": calls,
    }


# ==========================================================
# VOICE CALL DASHBOARD
# GET /admin/voice-calls/dashboard
# ==========================================================

@router.get("/dashboard")
def get_voice_calls_dashboard(
    date_filter: str = Query(
        "last_7_days",
        pattern="^(today|last_7_days|last_30_days|all)$",
    ),
    state_id: int | None = Query(None),
    creator_id: int | None = Query(None),
    call_status: str | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return build_dashboard(
        db=db,
        call_model=VoiceCall,
        call_id_field="call_id",
        date_filter=date_filter,
        state_id=state_id,
        creator_id=creator_id,
        call_status=call_status,
        search=search,
        page=page,
        limit=limit,
        call_type="voice",
    )


# ==========================================================
# VIDEO CALL DASHBOARD
# GET /admin/video-calls/dashboard
# ==========================================================

@video_dashboard_router.get("/dashboard")
def get_video_calls_dashboard(
    date_filter: str = Query(
        "last_7_days",
        pattern="^(today|last_7_days|last_30_days|all)$",
    ),
    state_id: int | None = Query(None),
    creator_id: int | None = Query(None),
    call_status: str | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return build_dashboard(
        db=db,
        call_model=VideoCall,
        call_id_field="video_call_id",
        date_filter=date_filter,
        state_id=state_id,
        creator_id=creator_id,
        call_status=call_status,
        search=search,
        page=page,
        limit=limit,
        call_type="video",
    )
