from datetime import datetime, timedelta, time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import SessionLocal

from models.earnings import Earning
from models.gift_revenue import GiftRevenue


router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"]
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
# PLATFORM PERFORMANCE - MONDAY TO SUNDAY
# =========================================================

@router.get("/platform-performance")
def get_platform_performance(
    db: Session = Depends(get_db)
):
    today = datetime.now().date()

    monday = today - timedelta(days=today.weekday())
    next_monday = monday + timedelta(days=7)

    start_datetime = datetime.combine(monday, time.min)
    end_datetime = datetime.combine(next_monday, time.min)

    # -----------------------------------------------------
    # 1. EARNINGS TABLE
    # -----------------------------------------------------

    creator_earnings = (
        db.query(
            func.coalesce(
                func.sum(Earning.total_earned), 0
            )
        )
        .scalar()
    )

    creator_earnings = float(creator_earnings or 0)

    # -----------------------------------------------------
    # 2. GIFT REVENUE TABLE - DAILY DATA
    # -----------------------------------------------------

    gift_results = (
        db.query(
            func.date(
                GiftRevenue.created_at
            ).label("revenue_date"),
            func.coalesce(
                func.sum(GiftRevenue.creator_revenue), 0
            ).label("creator_revenue"),
            func.coalesce(
                func.sum(GiftRevenue.platform_revenue), 0
            ).label("platform_revenue")
        )
        .filter(
            GiftRevenue.created_at >= start_datetime,
            GiftRevenue.created_at < end_datetime
        )
        .group_by(
            func.date(GiftRevenue.created_at)
        )
        .all()
    )

    gift_by_date = {
        str(row.revenue_date): {
            "creator_revenue": float(
                row.creator_revenue or 0
            ),
            "platform_revenue": float(
                row.platform_revenue or 0
            )
        }
        for row in gift_results
    }

    # -----------------------------------------------------
    # 3. WEEKLY BREAKDOWN
    # -----------------------------------------------------

    weekly_data = []

    weekly_creator_revenue = 0.0
    weekly_platform_revenue = 0.0

    for i in range(7):
        current_date = monday + timedelta(days=i)
        date_key = current_date.isoformat()

        gift = gift_by_date.get(
            date_key,
            {
                "creator_revenue": 0.0,
                "platform_revenue": 0.0
            }
        )

        creator_revenue = gift["creator_revenue"]
        platform_revenue = gift["platform_revenue"]

        daily_total = creator_revenue + platform_revenue

        weekly_creator_revenue += creator_revenue
        weekly_platform_revenue += platform_revenue

        weekly_data.append({
            "date": date_key,
            "day": current_date.strftime("%A"),
            "earnings_table": {
                "total_earned": round(
                    creator_earnings, 2
                )
            },
            "gift_revenue_table": {
                "creator_revenue": round(
                    creator_revenue, 2
                ),
                "platform_revenue": round(
                    platform_revenue, 2
                )
            },
            "daily_gift_total": round(
                daily_total, 2
            )
        })

    # -----------------------------------------------------
    # 4. SUMMARY TOTALS
    # -----------------------------------------------------

    total_gift_revenue = (
        weekly_creator_revenue
        + weekly_platform_revenue
    )

    combined_total = (
        creator_earnings
        + total_gift_revenue
    )

    # -----------------------------------------------------
    # 5. RESPONSE
    # -----------------------------------------------------

    return {
        "status_code": 200,
        "message": "Platform performance retrieved successfully",
        "data": {
            "weekly_breakdown": weekly_data,
            "summary": {
                "earnings_table": {
                    "total_earned": round(
                        creator_earnings, 2
                    )
                },
                "gift_revenue_table": {
                    "creator_revenue": round(
                        weekly_creator_revenue, 2
                    ),
                    "platform_revenue": round(
                        weekly_platform_revenue, 2
                    )
                },
                "total_gift_revenue": round(
                    total_gift_revenue, 2
                ),
                "combined_total": round(
                    combined_total, 2
                )
            }
        }
    }

