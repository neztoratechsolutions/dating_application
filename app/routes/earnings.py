from datetime import datetime, timedelta, date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models.earnings import Earning
from models.voice_call import VoiceCall
from models.video_call import VideoCall


router = APIRouter(
    prefix="/earnings",
    tags=["Earnings"]
)


# =========================================================
# SCHEMA
# =========================================================

class WithdrawRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)


# =========================================================
# GET CREATOR EARNINGS
# =========================================================

@router.get("/{user_id}")
def get_creator_earnings(
    user_id: int,
    db: Session = Depends(get_db)
):
    earning = (
        db.query(Earning)
        .filter(Earning.user_id == user_id)
        .first()
    )

    if not earning:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Earnings data not found"
        )

    # -----------------------------------------------------
    # LAST 7 DAYS
    # -----------------------------------------------------

    today = date.today()
    start_date = today - timedelta(days=6)

    # Initialize all 7 days with 0
    daily_earnings = {}

    for i in range(7):
        current_date = start_date + timedelta(days=i)

        daily_earnings[current_date] = Decimal("0.00")

    # -----------------------------------------------------
    # VOICE CALL REVENUE
    # -----------------------------------------------------

    voice_calls = (
        db.query(VoiceCall)
        .filter(
            VoiceCall.creator_id == user_id,
            VoiceCall.created_at >= datetime.combine(
                start_date,
                datetime.min.time()
            ),
            VoiceCall.status.in_(["completed", "ongoing"])
        )
        .all()
    )

    for call in voice_calls:

        if not call.revenue:
            continue

        call_date = call.created_at.date()

        if call_date in daily_earnings:
            daily_earnings[call_date] += Decimal(str(call.revenue))

    # -----------------------------------------------------
    # VIDEO CALL REVENUE
    # -----------------------------------------------------

    video_calls = (
        db.query(VideoCall)
        .filter(
            VideoCall.creator_id == user_id,
            VideoCall.created_at >= datetime.combine(
                start_date,
                datetime.min.time()
            ),
            VideoCall.status.in_(["completed", "ongoing"])
        )
        .all()
    )

    for call in video_calls:

        if not call.revenue:
            continue

        call_date = call.created_at.date()

        if call_date in daily_earnings:
            daily_earnings[call_date] += Decimal(str(call.revenue))

    # -----------------------------------------------------
    # CHART RESPONSE
    # -----------------------------------------------------

    last_7_days = []

    for current_date, amount in daily_earnings.items():

        last_7_days.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "day": current_date.strftime("%a"),
            "amount": float(amount)
        })

    # -----------------------------------------------------
    # RESPONSE
    # -----------------------------------------------------

    return {
        "status_code": 200,
        "message": "Earnings fetched successfully",
        "data": {
            "user_id": user_id,
            "total_earned": float(earning.total_earned or 0),
            "available_payout": float(earning.balance or 0),
            "withdrawal_amount": float(
                earning.withdrawal_amount or 0
            ),
            "last_7_days": last_7_days
        }
    }


# =========================================================
# WITHDRAW EARNINGS
# =========================================================

@router.post("/{user_id}/withdraw")
def withdraw_earnings(
    user_id: int,
    request: WithdrawRequest,
    db: Session = Depends(get_db)
):

    earning = (
        db.query(Earning)
        .filter(Earning.user_id == user_id)
        .first()
    )

    if not earning:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Earnings data not found"
        )

    available_balance = Decimal(
        str(earning.balance or 0)
    )

    withdraw_amount = Decimal(
        str(request.amount)
    )

    # -----------------------------------------------------
    # BALANCE VALIDATION
    # -----------------------------------------------------

    if withdraw_amount > available_balance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient available balance"
        )

    # -----------------------------------------------------
    # UPDATE EARNINGS
    # -----------------------------------------------------

    earning.balance = available_balance - withdraw_amount

    earning.withdrawal_amount = (
        Decimal(str(earning.withdrawal_amount or 0))
        + withdraw_amount
    )

    db.commit()
    db.refresh(earning)

    return {
        "status_code": 200,
        "message": "Withdrawal successful",
        "data": {
            "user_id": user_id,
            "withdrawn_amount": float(withdraw_amount),
            "total_earned": float(
                earning.total_earned or 0
            ),
            "available_payout": float(
                earning.balance or 0
            ),
            "withdrawal_amount": float(
                earning.withdrawal_amount or 0
            )
        }
    }