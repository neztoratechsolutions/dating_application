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


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db():
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@router.get("/dashboard")
def get_admin_dashboard(
    db: Session = Depends(get_db)
):

    try:

        # ====================================================
        # 1. TOTAL USERS
        # ====================================================

        total_users = (
            db.query(func.count(User.id))
            .scalar()
        )

        total_users = int(total_users or 0)


        # ====================================================
        # 2. TOTAL CREATORS
        # ====================================================

        total_creators = (
            db.query(func.count(User.id))
            .filter(
                User.role == "creator"
            )
            .scalar()
        )

        total_creators = int(total_creators or 0)


        # ====================================================
        # 3. LIVE USERS
        # ====================================================

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

        live_now = int(live_now or 0)


        # ====================================================
        # 4. TOTAL REVENUE
        # ====================================================

        revenue_result = (
            db.query(
                func.coalesce(
                    func.sum(Earning.total_earned),
                    0
                )
            )
            .scalar()
        )

        total_revenue = float(
            revenue_result or 0
        )


        # ====================================================
        # 5. PENDING KYC
        # ====================================================

        pending_kyc = (
            db.query(func.count(KYCDetail.id))
            .filter(
                KYCDetail.status == "Pending"
            )
            .scalar()
        )

        pending_kyc = int(
            pending_kyc or 0
        )


        # ====================================================
        # 6. WITHDRAWALS
        # ====================================================

        # Replace this with your actual withdrawal model
        # and query when withdrawal data is available.

        withdrawals = 0


        # ====================================================
        # 7. TOP 5 CREATORS
        # ====================================================

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


        # ====================================================
        # 8. REVENUE TREND - LAST 7 DAYS
        # ====================================================

        revenue_trend = []

        today = datetime.now().date()

        start_date = today - timedelta(days=6)


        # Start of the first day
        start_datetime = datetime.combine(
            start_date,
            datetime.min.time()
        )


        # Start of tomorrow
        end_datetime = datetime.combine(
            today + timedelta(days=1),
            datetime.min.time()
        )


        # ----------------------------------------------------
        # Fetch earnings for the last 7 days
        # ----------------------------------------------------

        earnings_records = (
            db.query(
                Earning.created_at,
                Earning.total_earned
            )
            .filter(
                Earning.created_at >= start_datetime,
                Earning.created_at < end_datetime
            )
            .all()
        )


        # ----------------------------------------------------
        # Group earnings by date
        # ----------------------------------------------------

        daily_earnings = {}


        for earning in earnings_records:

            if earning.created_at:

                earning_date = earning.created_at.date()

                amount = float(
                    earning.total_earned or 0
                )


                if earning_date not in daily_earnings:

                    daily_earnings[earning_date] = 0


                daily_earnings[earning_date] += amount


        # ----------------------------------------------------
        # Generate all 7 dates
        # ----------------------------------------------------

        for i in range(6, -1, -1):

            current_date = today - timedelta(days=i)


            # Get earnings for this particular date
            amount = daily_earnings.get(
                current_date,
                0
            )


            revenue_trend.append({

                "date": current_date.isoformat(),

                "day": current_date.strftime("%a"),

                "earnings": round(
                    amount,
                    2
                )

            })


        # ====================================================
        # 9. RESPONSE
        # ====================================================

        return {

            "status_code": 200,

            "message": "Admin dashboard fetched successfully",

            "data": {

                # --------------------------------------------
                # Dashboard statistics
                # --------------------------------------------

                "total_users": total_users,

                "total_creators": total_creators,

                "live_now": live_now,

                "total_revenue": round(
                    total_revenue,
                    2
                ),

                "pending_kyc": pending_kyc,

                "withdrawals": withdrawals,


                # --------------------------------------------
                # Top creators
                # --------------------------------------------

                "top_creators": top_creator_list,


                # --------------------------------------------
                # Revenue trend
                # --------------------------------------------

                "revenue_trend": revenue_trend

            }

        }


    except Exception as e:

        print(
            "Admin dashboard error:",
            str(e)
        )

        raise HTTPException(

            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

            detail="Failed to fetch admin dashboard"

        )