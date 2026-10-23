from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import SessionLocal

from models.users import User
from models.user_status import UserStatus
from models.earnings import Earning
from models.kyc_detail import KYCDetail


router = APIRouter(
    prefix="/admin",
    tags=["Admin Dashboard"]
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
# ADMIN DASHBOARD
# =========================================================

@router.get("/dashboard")
def get_admin_dashboard(
    db: Session = Depends(get_db)
):

    # =====================================================
    # TOTAL USERS
    # =====================================================

    total_users = (
        db.query(func.count(User.id))
        .scalar()
    )

    # =====================================================
    # TOTAL CREATORS
    # =====================================================

    total_creators = (
        db.query(func.count(User.id))
        .filter(User.role == "creator")
        .scalar()
    )

    # =====================================================
    # LIVE NOW
    # =====================================================

    live_now = (
        db.query(func.count(UserStatus.id))
        .join(
            User,
            User.id == UserStatus.user_id
        )
        .filter(
            UserStatus.is_online == True
        )
        .scalar()
    )

    # =====================================================
    # REVENUE
    # =====================================================
    # Currently using total_earned from earnings table
    # because there is no separate daily transaction table.

    revenue_result = (
        db.query(
            func.coalesce(
                func.sum(Earning.total_earned),
                0
            )
        )
        .scalar()
    )

    revenue_today = float(
        revenue_result or 0
    )

    # =====================================================
    # PENDING KYC
    # =====================================================

    pending_kyc = (
        db.query(func.count(KYCDetail.id))
        .filter(
            KYCDetail.status == "Pending"
        )
        .scalar()
    )

    # =====================================================
    # WITHDRAWALS
    # =====================================================
    # No withdrawal table currently available.

    withdrawals = 0

    # =====================================================
    # TOP CREATORS
    # =====================================================

    top_creators = (
        db.query(
            Earning,
            User
        )
        .join(
            User,
            Earning.user_id == User.id
        )
        .filter(
            User.role == "creator"
        )
        .order_by(
            Earning.total_earned.desc()
        )
        .limit(5)
        .all()
    )

    top_creator_list = []

    for rank, (earning, user) in enumerate(
        top_creators,
        start=1
    ):

        top_creator_list.append({
            "rank": rank,
            "user_id": user.id,
            "name": user.display_name,
            "total_earned": float(
                earning.total_earned or 0
            )
        })

    # =====================================================
    # REVENUE TREND
    # =====================================================

    revenue_trend = []

    today = datetime.now().date()

    for i in range(6, -1, -1):

        current_date = today - timedelta(days=i)

        revenue_trend.append({
            "date": current_date.isoformat(),
            "day": current_date.strftime("%a"),
            "earnings": revenue_today
        })

    # =====================================================
    # RESPONSE
    # =====================================================

    return {
        "status_code": 200,
        "message": "Admin dashboard retrieved successfully",

        "data": {

            "summary": {
                "total_users": total_users or 0,
                "creators": total_creators or 0,
                "live_now": live_now or 0,
                "revenue_today": revenue_today,
                "pending_kyc": pending_kyc or 0,
                "withdrawals": withdrawals
            },

            "revenue_trend": revenue_trend,

            "top_creators_today": top_creator_list
        }
    }