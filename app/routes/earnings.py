# from datetime import datetime, timedelta, date
# from decimal import Decimal

# from fastapi import APIRouter, Depends, HTTPException, status
# from pydantic import BaseModel, Field
# from sqlalchemy import func
# from sqlalchemy.orm import Session

# from database import get_db
# from models.earnings import Earning
# from models.voice_call import VoiceCall
# from models.video_call import VideoCall


# router = APIRouter(
#     prefix="/earnings",
#     tags=["Earnings"]
# )


# # =========================================================
# # SCHEMA
# # =========================================================

# class WithdrawRequest(BaseModel):
#     amount: Decimal = Field(..., gt=0)


# # =========================================================
# # GET CREATOR EARNINGS
# # =========================================================

# @router.get("/{user_id}")
# def get_creator_earnings(
#     user_id: int,
#     db: Session = Depends(get_db)
# ):
#     earning = (
#         db.query(Earning)
#         .filter(Earning.user_id == user_id)
#         .first()
#     )

#     if not earning:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Earnings data not found"
#         )

#     # -----------------------------------------------------
#     # LAST 7 DAYS
#     # -----------------------------------------------------

#     today = date.today()
#     start_date = today - timedelta(days=6)

#     # Initialize all 7 days with 0
#     daily_earnings = {}

#     for i in range(7):
#         current_date = start_date + timedelta(days=i)

#         daily_earnings[current_date] = Decimal("0.00")

#     # -----------------------------------------------------
#     # VOICE CALL REVENUE
#     # -----------------------------------------------------

#     voice_calls = (
#         db.query(VoiceCall)
#         .filter(
#             VoiceCall.creator_id == user_id,
#             VoiceCall.created_at >= datetime.combine(
#                 start_date,
#                 datetime.min.time()
#             ),
#             VoiceCall.status.in_(["completed", "ongoing"])
#         )
#         .all()
#     )

#     for call in voice_calls:

#         if not call.revenue:
#             continue

#         call_date = call.created_at.date()

#         if call_date in daily_earnings:
#             daily_earnings[call_date] += Decimal(str(call.revenue))

#     # -----------------------------------------------------
#     # VIDEO CALL REVENUE
#     # -----------------------------------------------------

#     video_calls = (
#         db.query(VideoCall)
#         .filter(
#             VideoCall.creator_id == user_id,
#             VideoCall.created_at >= datetime.combine(
#                 start_date,
#                 datetime.min.time()
#             ),
#             VideoCall.status.in_(["completed", "ongoing"])
#         )
#         .all()
#     )

#     for call in video_calls:

#         if not call.revenue:
#             continue

#         call_date = call.created_at.date()

#         if call_date in daily_earnings:
#             daily_earnings[call_date] += Decimal(str(call.revenue))

#     # -----------------------------------------------------
#     # CHART RESPONSE
#     # -----------------------------------------------------

#     last_7_days = []

#     for current_date, amount in daily_earnings.items():

#         last_7_days.append({
#             "date": current_date.strftime("%Y-%m-%d"),
#             "day": current_date.strftime("%a"),
#             "amount": float(amount)
#         })

#     # -----------------------------------------------------
#     # RESPONSE
#     # -----------------------------------------------------

#     return {
#         "status_code": 200,
#         "message": "Earnings fetched successfully",
#         "data": {
#             "user_id": user_id,
#             "total_earned": float(earning.total_earned or 0),
#             "available_payout": float(earning.balance or 0),
#             "withdrawal_amount": float(
#                 earning.withdrawal_amount or 0
#             ),
#             "last_7_days": last_7_days
#         }
#     }


# # =========================================================
# # WITHDRAW EARNINGS
# # =========================================================

# @router.post("/{user_id}/withdraw")
# def withdraw_earnings(
#     user_id: int,
#     request: WithdrawRequest,
#     db: Session = Depends(get_db)
# ):

#     earning = (
#         db.query(Earning)
#         .filter(Earning.user_id == user_id)
#         .first()
#     )

#     if not earning:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Earnings data not found"
#         )

#     available_balance = Decimal(
#         str(earning.balance or 0)
#     )

#     withdraw_amount = Decimal(
#         str(request.amount)
#     )

#     # -----------------------------------------------------
#     # BALANCE VALIDATION
#     # -----------------------------------------------------

#     if withdraw_amount > available_balance:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Insufficient available balance"
#         )

#     # -----------------------------------------------------
#     # UPDATE EARNINGS
#     # -----------------------------------------------------

#     earning.balance = available_balance - withdraw_amount

#     earning.withdrawal_amount = (
#         Decimal(str(earning.withdrawal_amount or 0))
#         + withdraw_amount
#     )

#     db.commit()
#     db.refresh(earning)

#     return {
#         "status_code": 200,
#         "message": "Withdrawal successful",
#         "data": {
#             "user_id": user_id,
#             "withdrawn_amount": float(withdraw_amount),
#             "total_earned": float(
#                 earning.total_earned or 0
#             ),
#             "available_payout": float(
#                 earning.balance or 0
#             ),
#             "withdrawal_amount": float(
#                 earning.withdrawal_amount or 0
#             )
#         }
#     }

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from decimal import Decimal
from datetime import datetime, timezone

from database import SessionLocal
from models.earnings import Earning
from models.withdraw import WithdrawalRequest
from models.gift_details import GiftDetail

router = APIRouter(
    prefix="/earnings",
    tags=["Earnings"]
)


# --------------------------------------------------
# DATABASE SESSION
# --------------------------------------------------

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# --------------------------------------------------
# GET USER EARNINGS AND WITHDRAWAL HISTORY
# --------------------------------------------------


@router.get("/{user_id}")
def get_earnings(
    user_id: int,
    db: Session = Depends(get_db)
):

    # --------------------------------------------------
    # GET USER EARNINGS
    # --------------------------------------------------

    earning = (
        db.query(Earning)
        .filter(
            Earning.user_id == user_id
        )
        .first()
    )

    if not earning:

        raise HTTPException(
            status_code=404,
            detail="Earnings record not found"
        )

    # --------------------------------------------------
    # GET GIFT EARNINGS
    # GiftDetail.user_id = Creator ID
    # GiftDetail.earnings = Creator gift earnings
    # --------------------------------------------------

    gift_earnings = (
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

    gift_earnings = Decimal(
        str(gift_earnings or 0)
    )

    # --------------------------------------------------
    # GET WITHDRAWAL HISTORY
    # --------------------------------------------------

    withdrawal_requests = (
        db.query(WithdrawalRequest)
        .filter(
            WithdrawalRequest.user_id == user_id
        )
        .order_by(
            WithdrawalRequest.requested_at.desc()
        )
        .all()
    )

    withdrawal_history = []

    for request in withdrawal_requests:

        withdrawal_history.append({

            "withdrawal_id": request.id,

            "user_id": request.user_id,

            "requested_amount": float(
                request.amount or 0
            ),

            "status": request.status,

            "requested_at": (
                request.requested_at.isoformat()
                if request.requested_at
                else None
            ),

            "approved_at": (
                request.approved_at.isoformat()
                if request.approved_at
                else None
            ),

            "rejected_at": (
                request.rejected_at.isoformat()
                if request.rejected_at
                else None
            )

        })

    # --------------------------------------------------
    # RESPONSE
    # --------------------------------------------------

    return {

        "status_code": 200,

        "message": "Earnings fetched successfully",

        "data": {

            "user_id": user_id,

            # Existing total earnings
            "total_earned": float(
                earning.total_earned or 0
            ),

            # Total earnings from gifts received
            "gift_earnings": float(
                gift_earnings
            ),

            # Existing withdrawal amount
            "withdrawal_amount": float(
                earning.withdrawal_amount or 0
            ),

            # Existing available payout
            "available_payout": float(
                earning.balance or 0
            ),

            # Withdrawal history
            "withdrawal_history": withdrawal_history

        }

    }



# --------------------------------------------------
# USER REQUEST WITHDRAWAL
# --------------------------------------------------

@router.post("/{user_id}/withdraw")
def request_withdrawal(
    user_id: int,
    amount: Decimal,
    db: Session = Depends(get_db)
):

    if amount <= Decimal("0"):
        raise HTTPException(
            status_code=400,
            detail="Withdrawal amount must be greater than zero"
        )

    if amount.as_tuple().exponent < -2:
        raise HTTPException(
            status_code=400,
            detail="Withdrawal amount cannot have more than 2 decimal places"
        )

    try:

        # Lock the user's earnings row
        earning = (
            db.query(Earning)
            .filter(
                Earning.user_id == user_id
            )
            .with_for_update()
            .first()
        )

        if not earning:
            raise HTTPException(
                status_code=404,
                detail="Earnings record not found"
            )

        available_balance = Decimal(
            str(earning.balance or 0)
        )

        # Calculate existing pending requests
        pending_amount = (
            db.query(
                func.coalesce(
                    func.sum(WithdrawalRequest.amount),
                    0
                )
            )
            .filter(
                WithdrawalRequest.user_id == user_id,
                WithdrawalRequest.status == "pending"
            )
            .scalar()
        )

        pending_amount = Decimal(
            str(pending_amount or 0)
        )

        remaining_balance = (
            available_balance - pending_amount
        )

        if amount > remaining_balance:

            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Insufficient available balance",
                    "available_balance": float(
                        available_balance
                    ),
                    "pending_withdrawal": float(
                        pending_amount
                    ),
                    "remaining_balance": float(
                        remaining_balance
                    )
                }
            )

        # Create withdrawal request
        withdrawal = WithdrawalRequest(
            user_id=user_id,
            amount=amount,
            status="pending"
        )

        db.add(withdrawal)

        db.commit()

        db.refresh(withdrawal)

        return {
            "message": "Withdrawal request submitted successfully",
            "withdrawal_id": withdrawal.id,
            "user_id": user_id,
            "requested_amount": float(
                withdrawal.amount
            ),
            "status": withdrawal.status,
            "requested_at": (
                withdrawal.requested_at.isoformat()
                if withdrawal.requested_at
                else None
            ),
            "available_balance": float(
                available_balance
            )
        }

    except HTTPException:
        db.rollback()
        raise

    except SQLAlchemyError as e:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Database error while creating withdrawal request"
        )


# --------------------------------------------------
# ADMIN APPROVE WITHDRAWAL
# --------------------------------------------------

@router.post("/withdrawals/{withdrawal_id}/approve")
def approve_withdrawal(
    withdrawal_id: int,
    db: Session = Depends(get_db)
):

    try:

        # Lock withdrawal request
        withdrawal = (
            db.query(WithdrawalRequest)
            .filter(
                WithdrawalRequest.id == withdrawal_id
            )
            .with_for_update()
            .first()
        )

        if not withdrawal:

            raise HTTPException(
                status_code=404,
                detail="Withdrawal request not found"
            )

        if withdrawal.status != "pending":

            raise HTTPException(
                status_code=400,
                detail=f"Withdrawal request is already {withdrawal.status}"
            )

        # Lock user's earnings row
        earning = (
            db.query(Earning)
            .filter(
                Earning.user_id == withdrawal.user_id
            )
            .with_for_update()
            .first()
        )

        if not earning:

            raise HTTPException(
                status_code=404,
                detail="Earnings record not found"
            )

        requested_amount = Decimal(
            str(withdrawal.amount)
        )

        available_balance = Decimal(
            str(earning.balance or 0)
        )

        if requested_amount > available_balance:

            raise HTTPException(
                status_code=400,
                detail="Insufficient earnings balance to approve withdrawal"
            )

        # Deduct amount only after approval
        earning.balance = (
            available_balance - requested_amount
        )

        # Add approved amount to withdrawal total
        earning.withdrawal_amount = (
            Decimal(str(earning.withdrawal_amount or 0))
            + requested_amount
        )

        # Update withdrawal request
        withdrawal.status = "approved"

        withdrawal.approved_at = datetime.now(
            timezone.utc
        )

        db.commit()

        db.refresh(withdrawal)
        db.refresh(earning)

        return {
            "message": "Withdrawal approved successfully",
            "withdrawal_id": withdrawal.id,
            "user_id": withdrawal.user_id,
            "requested_amount": float(
                withdrawal.amount
            ),
            "status": withdrawal.status,
            "approved_at": (
                withdrawal.approved_at.isoformat()
                if withdrawal.approved_at
                else None
            ),
            "remaining_balance": float(
                earning.balance
            ),
            "total_withdrawal_amount": float(
                earning.withdrawal_amount
            )
        }

    except HTTPException:
        db.rollback()
        raise

    except SQLAlchemyError:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Database error while approving withdrawal"
        )


# --------------------------------------------------
# ADMIN REJECT WITHDRAWAL
# --------------------------------------------------

@router.post("/withdrawals/{withdrawal_id}/reject")
def reject_withdrawal(
    withdrawal_id: int,
    db: Session = Depends(get_db)
):

    try:

        withdrawal = (
            db.query(WithdrawalRequest)
            .filter(
                WithdrawalRequest.id == withdrawal_id
            )
            .with_for_update()
            .first()
        )

        if not withdrawal:

            raise HTTPException(
                status_code=404,
                detail="Withdrawal request not found"
            )

        if withdrawal.status != "pending":

            raise HTTPException(
                status_code=400,
                detail=f"Withdrawal request is already {withdrawal.status}"
            )

        # Reject without deducting earnings
        withdrawal.status = "rejected"

        withdrawal.rejected_at = datetime.now(
            timezone.utc
        )

        db.commit()

        db.refresh(withdrawal)

        return {
            "message": "Withdrawal rejected successfully",
            "withdrawal_id": withdrawal.id,
            "user_id": withdrawal.user_id,
            "requested_amount": float(
                withdrawal.amount
            ),
            "status": withdrawal.status,
            "requested_at": (
                withdrawal.requested_at.isoformat()
                if withdrawal.requested_at
                else None
            ),
            "rejected_at": (
                withdrawal.rejected_at.isoformat()
                if withdrawal.rejected_at
                else None
            )
        }

    except HTTPException:
        db.rollback()
        raise

    except SQLAlchemyError:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Database error while rejecting withdrawal"
        )
