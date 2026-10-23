from datetime import datetime, timedelta

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)

from sqlalchemy import func
from sqlalchemy.orm import Session

from database import SessionLocal

from models.users import User
from models.earnings import Earning
from models.kyc_detail import KYCDetail
from models.voice_call import VoiceCall
from models.video_call import VideoCall
from models.review import Review
from models.social_models import FollowDetail


router = APIRouter(
    prefix="/creator",
    tags=["Creator Dashboard"]
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
# CREATOR DASHBOARD
# =========================================================

@router.get("/dashboard/{user_id}")
def get_creator_dashboard(
    user_id: int,
    db: Session = Depends(get_db)
):

    # =====================================================
    # CHECK CREATOR
    # =====================================================

    user = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.role == "creator"
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Creator not found"
        )

    # =====================================================
    # KYC STATUS
    # =====================================================

    kyc = (
        db.query(KYCDetail)
        .filter(
            KYCDetail.user_id == user_id
        )
        .first()
    )

    if not kyc:

        kyc_status = "Pending"
        can_receive_payouts = False

    else:

        kyc_status = kyc.status

        can_receive_payouts = (
            kyc.status == "Approved"
        )

    # =====================================================
    # EARNINGS
    # =====================================================

    earning = (
        db.query(Earning)
        .filter(
            Earning.user_id == user_id
        )
        .first()
    )

    if earning:

        total_earned = float(
            earning.total_earned or 0
        )

        balance = float(
            earning.balance or 0
        )

        withdrawal_amount = float(
            earning.withdrawal_amount or 0
        )

    else:

        total_earned = 0.00
        balance = 0.00
        withdrawal_amount = 0.00

    # =====================================================
    # TODAY
    # =====================================================

    today = datetime.now().date()

    today_start = datetime.combine(
        today,
        datetime.min.time()
    )

    tomorrow_start = (
        today_start + timedelta(days=1)
    )

    # =====================================================
    # TODAY'S VOICE CALLS
    # =====================================================

    today_voice_calls = (
        db.query(func.count(VoiceCall.id))
        .filter(
            VoiceCall.creator_id == user_id,
            VoiceCall.created_at >= today_start,
            VoiceCall.created_at < tomorrow_start
        )
        .scalar()
    )

    today_voice_calls = (
        today_voice_calls or 0
    )

    # =====================================================
    # TODAY'S VIDEO CALLS
    # =====================================================

    today_video_calls = (
        db.query(func.count(VideoCall.id))
        .filter(
            VideoCall.creator_id == user_id,
            VideoCall.created_at >= today_start,
            VideoCall.created_at < tomorrow_start
        )
        .scalar()
    )

    today_video_calls = (
        today_video_calls or 0
    )

    # =====================================================
    # TOTAL CALLS TODAY
    # =====================================================

    calls_today = (
        today_voice_calls +
        today_video_calls
    )

    # =====================================================
    # TODAY'S EARNINGS
    # =====================================================
    # Earning table currently stores cumulative
    # total_earned only.
    #
    # There is no separate earning transaction/history
    # table, so total_earned is used for dashboard testing.

    today_earnings = total_earned

    # =====================================================
    # FOLLOWERS
    # =====================================================

    followers = (
        db.query(func.count(FollowDetail.id))
        .filter(
            FollowDetail.following_id == user_id,
            FollowDetail.follow_status == "following"
        )
        .scalar()
    )

    followers = followers or 0

    # =====================================================
    # RATING
    # =====================================================

    rating_result = (
        db.query(
            func.avg(Review.star_details)
        )
        .filter(
            Review.reviewee_id == user_id
        )
        .scalar()
    )

    if rating_result is None:

        rating = 0.0

    else:

        rating = round(
            float(rating_result),
            1
        )

    # =====================================================
    # WEEKLY EARNINGS
    # =====================================================
    # Current earnings table has only cumulative
    # total_earned. So current total is returned.

    weekly_earnings = total_earned

    # =====================================================
    # WEEKLY CHART
    # =====================================================
    # There is no daily earnings history table.
    # Therefore current total_earned is used for each
    # day for dashboard UI testing.

    weekly_chart = []

    for i in range(6, -1, -1):

        chart_date = (
            today - timedelta(days=i)
        )

        weekly_chart.append({
            "date": chart_date.isoformat(),
            "day": chart_date.strftime("%a"),
            "earnings": total_earned
        })

    # =====================================================
    # NEW MESSAGES
    # =====================================================
    # Chat/message model is not available currently.

    new_messages = 0

    # =====================================================
    # RESPONSE
    # =====================================================

    return {

        "status_code": 200,

        "message": (
            "Creator dashboard retrieved successfully"
        ),

        "data": {

            # =================================================
            # CREATOR
            # =================================================

            "creator": {
                "user_id": user.id,
                "name": user.display_name,
                "profile_photo": user.profile_photo
            },

            # =================================================
            # KYC
            # =================================================

            "kyc": {

                "status": kyc_status,

                "message": (
                    "Complete your KYC"
                    if not can_receive_payouts
                    else "KYC verified"
                ),

                "can_receive_payouts": (
                    can_receive_payouts
                )
            },

            # =================================================
            # TODAY
            # =================================================

            "today": {

                "earnings": today_earnings,

                "followers": followers,

                "calls": calls_today,

                "rating": rating
            },

            # =================================================
            # WEEKLY
            # =================================================

            "weekly": {

                "earnings": weekly_earnings,

                "chart": weekly_chart
            },

            # =================================================
            # MESSAGES
            # =================================================

            "messages": {

                "new_messages": new_messages
            },

            # =================================================
            # PAYOUT
            # =================================================

            "payout": {

                "balance": balance,

                "withdrawal_amount": withdrawal_amount
            }
        }
    }