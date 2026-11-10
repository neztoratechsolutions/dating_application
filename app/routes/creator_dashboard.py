from datetime import datetime, timedelta, time

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
from models.chat_history import ChatMessage

# Change this import path if your GiftDetail model is located elsewhere.
from models.gift_details import GiftDetail


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
    # DATE
    # =====================================================

    # Ensure server timezone is configured to IST.

    today = datetime.now().date()

    today_start = datetime.combine(
        today,
        time.min
    )

    tomorrow_start = (
        today_start + timedelta(days=1)
    )

    # =====================================================
    # WEEK DATE RANGE
    # =====================================================

    week_start_date = (
        today - timedelta(days=6)
    )

    week_start = datetime.combine(
        week_start_date,
        time.min
    )

    # =====================================================
    # KYC
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
    # CHAT + CALLS EARNINGS
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

        earning_updated_at = (
            earning.updated_at
        )

    else:

        total_earned = 0.00

        balance = 0.00

        withdrawal_amount = 0.00

        earning_updated_at = None

    # =====================================================
    # GIFT COINS EARNINGS
    # =====================================================

    gift_earnings_result = (
        db.query(
            func.coalesce(
                func.sum(GiftDetail.earnings),
                0
            )
        )
        .filter(
            GiftDetail.user_id == user_id
        )
        .scalar()
    )

    gift_earnings = float(
        gift_earnings_result or 0
    )

    # =====================================================
    # TOTAL EARNINGS
    # =====================================================

    total_earnings = (
        total_earned + gift_earnings
    )

    # =====================================================
    # TODAY'S VOICE CALLS
    # =====================================================

    today_voice_calls = (
        db.query(
            func.count(VoiceCall.id)
        )
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
        db.query(
            func.count(VideoCall.id)
        )
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
    # TODAY'S CHAT + CALLS EARNINGS
    # =====================================================
    #
    # Earning.total_earned is cumulative.
    #
    # updated_at does not provide transaction-level
    # earnings history.
    #
    # This approximation displays cumulative earnings
    # on the last updated date only.
    # =====================================================

    today_chat_calls_earnings = 0.00

    if earning_updated_at:

        updated_date = (
            earning_updated_at.date()
        )

        if updated_date == today:

            today_chat_calls_earnings = (
                total_earned
            )

    # =====================================================
    # TODAY'S GIFT COINS EARNINGS
    # =====================================================

    today_gift_earnings_result = (
        db.query(
            func.coalesce(
                func.sum(GiftDetail.earnings),
                0
            )
        )
        .filter(
            GiftDetail.user_id == user_id,

            GiftDetail.created_at >= today_start,

            GiftDetail.created_at < tomorrow_start
        )
        .scalar()
    )

    today_gift_earnings = float(
        today_gift_earnings_result or 0
    )

    # =====================================================
    # TOTAL TODAY'S EARNINGS
    # =====================================================

    today_earnings = (
        today_chat_calls_earnings
        + today_gift_earnings
    )

    # =====================================================
    # FOLLOWERS
    # =====================================================

    followers = (
        db.query(
            func.count(FollowDetail.id)
        )
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
    # WEEKLY CHAT + CALLS EARNINGS
    # =====================================================
    #
    # This is an approximation because the Earning table
    # stores cumulative earnings rather than transactions.
    # =====================================================

    weekly_chat_calls_earnings = 0.00

    if earning_updated_at:

        updated_date = (
            earning_updated_at.date()
        )

        if (
            week_start_date
            <= updated_date
            <= today
        ):

            weekly_chat_calls_earnings = (
                total_earned
            )

    # =====================================================
    # WEEKLY GIFT COINS EARNINGS
    # =====================================================

    weekly_gift_earnings_result = (
        db.query(
            func.coalesce(
                func.sum(GiftDetail.earnings),
                0
            )
        )
        .filter(
            GiftDetail.user_id == user_id,

            GiftDetail.created_at >= week_start,

            GiftDetail.created_at < tomorrow_start
        )
        .scalar()
    )

    weekly_gift_earnings = float(
        weekly_gift_earnings_result or 0
    )

    # =====================================================
    # TOTAL WEEKLY EARNINGS
    # =====================================================

    weekly_earnings = (
        weekly_chat_calls_earnings
        + weekly_gift_earnings
    )

    # =====================================================
    # WEEKLY CHART
    # =====================================================
    #
    # Gift earnings are calculated from GiftDetail.created_at.
    #
    # Chat + Calls chart values remain approximate because
    # Earning has no transaction history.
    # =====================================================

    weekly_chart = []

    for i in range(6, -1, -1):

        chart_date = (
            today - timedelta(days=i)
        )

        chart_start = datetime.combine(
            chart_date,
            time.min
        )

        chart_end = (
            chart_start + timedelta(days=1)
        )

        # ---------------------------------------------
        # CHAT + CALLS CHART EARNINGS
        # ---------------------------------------------

        daily_chat_calls_earnings = 0.00

        if earning_updated_at:

            updated_date = (
                earning_updated_at.date()
            )

            if chart_date == updated_date:

                daily_chat_calls_earnings = (
                    total_earned
                )

        # ---------------------------------------------
        # DAILY GIFT EARNINGS
        # ---------------------------------------------

        daily_gift_result = (
            db.query(
                func.coalesce(
                    func.sum(GiftDetail.earnings),
                    0
                )
            )
            .filter(
                GiftDetail.user_id == user_id,

                GiftDetail.created_at >= chart_start,

                GiftDetail.created_at < chart_end
            )
            .scalar()
        )

        daily_gift_earnings = float(
            daily_gift_result or 0
        )

        # ---------------------------------------------
        # TOTAL DAILY EARNINGS
        # ---------------------------------------------

        daily_total_earnings = (
            daily_chat_calls_earnings
            + daily_gift_earnings
        )

        weekly_chart.append({

            "date": chart_date.isoformat(),

            "day": chart_date.strftime("%a"),

            "chat_calls_earnings": round(
                daily_chat_calls_earnings,
                2
            ),

            "gift_earnings": round(
                daily_gift_earnings,
                2
            ),

            "earnings": round(
                daily_total_earnings,
                2
            )

        })

    # =====================================================
    # TODAY'S RECEIVED MESSAGES
    # =====================================================

    today_messages = (
        db.query(
            func.count(ChatMessage.id)
        )
        .filter(
            ChatMessage.receiver_id == user_id,

            ChatMessage.created_at >= today_start,

            ChatMessage.created_at < tomorrow_start,

            ChatMessage.is_deleted == False
        )
        .scalar()
    )

    today_messages = (
        today_messages or 0
    )

    # =====================================================
    # RESPONSE
    # =====================================================

    return {

        "status_code": 200,

        "message": (
            "Creator dashboard retrieved successfully"
        ),

        "data": {

            # =============================================
            # CREATOR
            # =============================================

            "creator": {

                "user_id": user.id,

                "name": user.display_name,

                "profile_photo": user.profile_photo

            },

            # =============================================
            # KYC
            # =============================================

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

            # =============================================
            # EARNINGS
            # =============================================

            "earnings": {

                "chat_calls_earned": round(
                    total_earned,
                    2
                ),

                "gift_coins_earned": round(
                    gift_earnings,
                    2
                ),

                "total_earned": round(
                    total_earnings,
                    2
                )

            },

            # =============================================
            # TODAY
            # =============================================

            "today": {

                "earnings": round(
                    today_earnings,
                    2
                ),

                "chat_calls_earnings": round(
                    today_chat_calls_earnings,
                    2
                ),

                "gift_earnings": round(
                    today_gift_earnings,
                    2
                ),

                "followers": followers,

                "calls": calls_today,

                "voice_calls": today_voice_calls,

                "video_calls": today_video_calls,

                "rating": rating

            },

            # =============================================
            # WEEKLY
            # =============================================

            "weekly": {

                "earnings": round(
                    weekly_earnings,
                    2
                ),

                "chat_calls_earnings": round(
                    weekly_chat_calls_earnings,
                    2
                ),

                "gift_earnings": round(
                    weekly_gift_earnings,
                    2
                ),

                "chart": weekly_chart

            },

            # =============================================
            # MESSAGES
            # =============================================

            "messages": {

                "new_messages": today_messages

            },

            # =============================================
            # PAYOUT
            # =============================================

            "payout": {

                "balance": round(
                    balance,
                    2
                ),

                "withdrawal_amount": round(
                    withdrawal_amount,
                    2
                )

            }

        }

    }
