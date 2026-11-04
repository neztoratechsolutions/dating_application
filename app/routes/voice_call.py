# ==========================================================
# VOICE CALL ROUTER
# ==========================================================

from datetime import datetime, timezone, date
from decimal import Decimal
from typing import Optional

from sqlalchemy import func
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    BackgroundTasks,
    status,
)
from sqlalchemy.orm import Session

from database import get_db, SessionLocal

from models.voice_call import VoiceCall
from models.users import User
from models.user_status import UserStatus
from models.wallet import Wallet

from schemas.voice_call import (
    VoiceCallInitiate,
    VoiceCallCreate,
    VoiceCallUpdate,
    VoiceCallResponse,
)


router = APIRouter(
    prefix="/voice-calls",
    tags=["Voice Calls"]
)


# ==========================================================
# CONSTANTS
# ==========================================================

FREE_CALL_DURATION_SECONDS = 2
PAID_CALL_COINS = 200


# ==========================================================
# GENERATE VOICE CALL ID
#
# Example:
# VOICE-2026-09-16-01
# VOICE-2026-09-16-02
# ==========================================================

def generate_call_id(db: Session):

    today = datetime.now(timezone.utc).date()

    date_part = today.strftime("%Y-%m-%d")

    prefix = f"VOICE-{date_part}-"

    last_call = (
        db.query(VoiceCall)
        .filter(
            VoiceCall.call_id.like(f"{prefix}%")
        )
        .order_by(
            VoiceCall.id.desc()
        )
        .first()
    )

    if last_call:

        try:
            last_number = int(
                last_call.call_id.split("-")[-1]
            )

            next_number = last_number + 1

        except (ValueError, AttributeError):

            next_number = 1

    else:

        next_number = 1

    return f"{prefix}{next_number:02d}"


# ==========================================================
# CHECK USER / CALLER / RECEIVER
# ==========================================================

def validate_customer_creator(
    db: Session,
    customer_id: int,
    creator_id: int,
    caller_id: int,
    receiver_id: int,
):

    customer = (
        db.query(User)
        .filter(
            User.id == customer_id
        )
        .first()
    )

    if not customer:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    creator = (
        db.query(User)
        .filter(
            User.id == creator_id
        )
        .first()
    )

    if not creator:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Creator not found"
        )

    caller = (
        db.query(User)
        .filter(
            User.id == caller_id
        )
        .first()
    )

    if not caller:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Caller not found"
        )

    receiver = (
        db.query(User)
        .filter(
            User.id == receiver_id
        )
        .first()
    )

    if not receiver:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receiver not found"
        )

    if customer.role != "customer":

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Customer ID must belong to a customer"
        )

    if creator.role != "creator":

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Creator ID must belong to a creator"
        )

    if caller_id != customer_id:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Caller must be the customer"
        )

    if receiver_id != creator_id:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Receiver must be the creator"
        )

    return customer, creator, caller, receiver


# ==========================================================
# CHECK WHETHER CUSTOMER ALREADY USED FREE CALL
# ==========================================================

def has_used_free_call(
    db: Session,
    customer_id: int
):

    free_call = (
        db.query(VoiceCall)
        .filter(
            VoiceCall.customer_id == customer_id,
            VoiceCall.is_free_call.is_(True)
        )
        .first()
    )

    return free_call is not None


# ==========================================================
# GET CUSTOMER WALLET
# ==========================================================

def get_customer_wallet(
    db: Session,
    customer_id: int
):

    wallet = (
        db.query(Wallet)
        .filter(
            Wallet.user_id == customer_id
        )
        .with_for_update()
        .first()
    )

    if not wallet:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer wallet not found"
        )

    return wallet


# ==========================================================
# AUTO END FIRST FREE CALL AFTER 2 SECONDS
# ==========================================================

def auto_end_free_call(call_id: str):

    import time

    time.sleep(
        FREE_CALL_DURATION_SECONDS
    )

    db = SessionLocal()

    try:

        call = (
            db.query(VoiceCall)
            .filter(
                VoiceCall.call_id == call_id
            )
            .first()
        )

        if not call:
            return

        # Only end if call is still ongoing
        if call.status != "ongoing":
            return

        if not call.start_time:
            return

        end_time = datetime.now(
            timezone.utc
        )

        start_time = call.start_time

        if start_time.tzinfo is None:

            start_time = start_time.replace(
                tzinfo=timezone.utc
            )

        duration_seconds = (
            end_time - start_time
        ).total_seconds()

        # Maximum free call = 2 seconds
        duration_seconds = min(
            duration_seconds,
            FREE_CALL_DURATION_SECONDS
        )

        duration_hours = round(
            duration_seconds / 3600,
            2
        )

        call.end_time = end_time

        call.duration = Decimal(
            str(duration_hours)
        )

        call.status = "ended"

        db.commit()

    except Exception:

        db.rollback()

    finally:

        db.close()


# ==========================================================
# INITIATE VOICE CALL
# ==========================================================

@router.post(
    "/initiate",
    response_model=VoiceCallResponse,
    status_code=status.HTTP_201_CREATED
)
def initiate_voice_call(
    data: VoiceCallInitiate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):

    # ------------------------------------------------------
    # GET CALLER
    # ------------------------------------------------------

    caller = (
        db.query(User)
        .filter(
            User.id == data.caller_id
        )
        .first()
    )

    if not caller:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Caller not found"
        )

    # ------------------------------------------------------
    # GET RECEIVER
    # ------------------------------------------------------

    receiver = (
        db.query(User)
        .filter(
            User.id == data.receiver_id
        )
        .first()
    )

    if not receiver:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receiver not found"
        )

    # ------------------------------------------------------
    # CALLER MUST BE CUSTOMER
    # ------------------------------------------------------

    if caller.role != "customer":

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only customer can initiate a voice call"
        )

    # ------------------------------------------------------
    # RECEIVER MUST BE CREATOR
    # ------------------------------------------------------

    if receiver.role != "creator":

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Voice call receiver must be a creator"
        )

    # ------------------------------------------------------
    # CHECK ACTIVE CALL
    # ------------------------------------------------------

    active_call = (
        db.query(VoiceCall)
        .filter(
            VoiceCall.status.in_(
                ["ringing", "ongoing"]
            )
        )
        .filter(
            (
                (VoiceCall.caller_id == data.caller_id)
                &
                (VoiceCall.receiver_id == data.receiver_id)
            )
            |
            (
                (VoiceCall.caller_id == data.receiver_id)
                &
                (VoiceCall.receiver_id == data.caller_id)
            )
        )
        .first()
    )

    if active_call:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An active call already exists between these users"
        )

    # ------------------------------------------------------
    # CHECK FIRST FREE CALL
    # ------------------------------------------------------

    free_call_already_used = has_used_free_call(
        db,
        data.caller_id
    )

    is_free_call = not free_call_already_used

    # ------------------------------------------------------
    # FOR PAID CALL
    #
    # We only CHECK wallet here.
    # Actual deduction happens when accepted.
    # ------------------------------------------------------

    if not is_free_call:

        wallet = (
            db.query(Wallet)
            .filter(
                Wallet.user_id == data.caller_id
            )
            .first()
        )

        if not wallet:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer wallet not found"
            )

        if wallet.coins < PAID_CALL_COINS:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You need at least 200 coins to make a call"
            )

    # ------------------------------------------------------
    # CUSTOMER / CREATOR MAPPING
    # ------------------------------------------------------

    customer_id = caller.id
    creator_id = receiver.id

    # ------------------------------------------------------
    # GENERATE CALL ID
    # ------------------------------------------------------

    call_id = generate_call_id(db)

    # ------------------------------------------------------
    # CREATE CALL
    # ------------------------------------------------------

    new_call = VoiceCall(

        call_id=call_id,

        customer_id=customer_id,

        creator_id=creator_id,

        caller_id=data.caller_id,

        receiver_id=data.receiver_id,

        start_time=None,

        end_time=None,

        duration=Decimal("0.00"),

        coins=0,

        revenue=Decimal("0.00"),

        status="ringing",

        is_free_call=is_free_call
    )

    db.add(new_call)

    db.commit()

    db.refresh(new_call)

    return new_call


# ==========================================================
# CREATE VOICE CALL
# ==========================================================

@router.post(
    "/",
    response_model=VoiceCallResponse,
    status_code=status.HTTP_201_CREATED
)
def create_voice_call(
    data: VoiceCallCreate,
    db: Session = Depends(get_db)
):

    customer, creator, caller, receiver = (
        validate_customer_creator(
            db=db,
            customer_id=data.customer_id,
            creator_id=data.creator_id,
            caller_id=data.caller_id,
            receiver_id=data.receiver_id
        )
    )

    # ------------------------------------------------------
    # CHECK PREVIOUS FREE CALL
    # ------------------------------------------------------

    free_call_already_used = has_used_free_call(
        db,
        data.customer_id
    )

    is_free_call = not free_call_already_used

    # ------------------------------------------------------
    # PAID CALL WALLET CHECK
    # ------------------------------------------------------

    if not is_free_call:

        wallet = (
            db.query(Wallet)
            .filter(
                Wallet.user_id == data.customer_id
            )
            .first()
        )

        if not wallet:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer wallet not found"
            )

        if wallet.coins < PAID_CALL_COINS:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You need at least 200 coins to make a call"
            )

    # ------------------------------------------------------
    # CREATE
    # ------------------------------------------------------

    new_call = VoiceCall(

        call_id=generate_call_id(db),

        customer_id=data.customer_id,

        creator_id=data.creator_id,

        caller_id=data.caller_id,

        receiver_id=data.receiver_id,

        start_time=data.start_time,

        end_time=data.end_time,

        duration=data.duration,

        coins=0,

        revenue=data.revenue,

        status=data.status,

        is_free_call=is_free_call
    )

    db.add(new_call)

    db.commit()

    db.refresh(new_call)

    return new_call


# ==========================================================
# GET ALL VOICE CALLS
# ==========================================================

@router.get(
    "/",
    response_model=list[VoiceCallResponse]
)
def get_all_voice_calls(

    call_date: Optional[date] = None,

    start_date: Optional[date] = None,

    end_date: Optional[date] = None,

    customer_id: Optional[int] = None,

    creator_id: Optional[int] = None,

    caller_id: Optional[int] = None,

    receiver_id: Optional[int] = None,

    call_status: Optional[str] = None,

    db: Session = Depends(get_db)
):

    query = db.query(VoiceCall)

    # ------------------------------------------------------
    # CALL DATE
    # ------------------------------------------------------

    if call_date:

        query = query.filter(
            func.date(
                VoiceCall.created_at
            ) == call_date
        )

    # ------------------------------------------------------
    # START DATE
    # ------------------------------------------------------

    if start_date:

        query = query.filter(
            func.date(
                VoiceCall.created_at
            ) >= start_date
        )

    # ------------------------------------------------------
    # END DATE
    # ------------------------------------------------------

    if end_date:

        query = query.filter(
            func.date(
                VoiceCall.created_at
            ) <= end_date
        )

    # ------------------------------------------------------
    # CUSTOMER
    # ------------------------------------------------------

    if customer_id:

        query = query.filter(
            VoiceCall.customer_id == customer_id
        )

    # ------------------------------------------------------
    # CREATOR
    # ------------------------------------------------------

    if creator_id:

        query = query.filter(
            VoiceCall.creator_id == creator_id
        )

    # ------------------------------------------------------
    # CALLER
    # ------------------------------------------------------

    if caller_id:

        query = query.filter(
            VoiceCall.caller_id == caller_id
        )

    # ------------------------------------------------------
    # RECEIVER
    # ------------------------------------------------------

    if receiver_id:

        query = query.filter(
            VoiceCall.receiver_id == receiver_id
        )

    # ------------------------------------------------------
    # STATUS
    # ------------------------------------------------------

    if call_status:

        query = query.filter(
            VoiceCall.status == call_status
        )

    calls = (
        query
        .order_by(
            VoiceCall.id.desc()
        )
        .all()
    )

    if not calls:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No voice calls found"
        )

    return calls


# ==========================================================
# ACCEPT VOICE CALL
# ==========================================================

@router.post(
    "/{call_id}/accept",
    response_model=VoiceCallResponse
)
def accept_voice_call(
    call_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):

    # ------------------------------------------------------
    # GET CALL
    # ------------------------------------------------------

    call = (
        db.query(VoiceCall)
        .filter(
            VoiceCall.call_id == call_id
        )
        .first()
    )

    if not call:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voice call not found"
        )

    # ------------------------------------------------------
    # CALL MUST BE RINGING
    # ------------------------------------------------------

    if call.status != "ringing":

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only ringing calls can be accepted"
        )

    # ======================================================
    # FREE CALL
    # ======================================================

    if call.is_free_call:

        # First free call
        call.coins = 0

    # ======================================================
    # PAID CALL
    # ======================================================

    else:

        # --------------------------------------------------
        # GET WALLET
        # --------------------------------------------------

        wallet = (
            db.query(Wallet)
            .filter(
                Wallet.user_id == call.customer_id
            )
            .with_for_update()
            .first()
        )

        if not wallet:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer wallet not found"
            )

        # --------------------------------------------------
        # CHECK COINS
        # --------------------------------------------------

        if wallet.coins < PAID_CALL_COINS:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You need at least 200 coins to make a call"
            )

        # --------------------------------------------------
        # DEDUCT 200 COINS
        # --------------------------------------------------

        wallet.coins = (
            wallet.coins - PAID_CALL_COINS
        )

        # --------------------------------------------------
        # UPDATE WALLET TRANSACTION INFO
        # --------------------------------------------------

        wallet.spending = (
            wallet.spending or Decimal("0.00")
        )

        wallet.last_transaction = (
            datetime.now(timezone.utc)
        )

        # --------------------------------------------------
        # STORE CHARGED COINS IN VOICE CALL
        # --------------------------------------------------

        call.coins = PAID_CALL_COINS

    # ======================================================
    # START CALL
    # ======================================================

    start_time = datetime.now(
        timezone.utc
    )

    call.start_time = start_time

    call.status = "ongoing"

    db.commit()

    db.refresh(call)

    # ======================================================
    # FREE CALL AUTO CUT
    # ======================================================

    if call.is_free_call:

        background_tasks.add_task(
            auto_end_free_call,
            call.call_id
        )

    return call


# ==========================================================
# REJECT VOICE CALL
# ==========================================================

@router.post(
    "/{call_id}/reject",
    response_model=VoiceCallResponse
)
def reject_voice_call(
    call_id: str,
    db: Session = Depends(get_db)
):

    call = (
        db.query(VoiceCall)
        .filter(
            VoiceCall.call_id == call_id
        )
        .first()
    )

    if not call:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voice call not found"
        )

    if call.status != "ringing":

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only ringing calls can be rejected"
        )

    call.status = "rejected"

    call.end_time = datetime.now(
        timezone.utc
    )

    call.duration = Decimal("0.00")

    db.commit()

    db.refresh(call)

    return call


# ==========================================================
# END VOICE CALL
# ==========================================================

@router.post(
    "/{call_id}/end",
    response_model=VoiceCallResponse
)
def end_voice_call(
    call_id: str,
    db: Session = Depends(get_db)
):

    call = (
        db.query(VoiceCall)
        .filter(
            VoiceCall.call_id == call_id
        )
        .first()
    )

    if not call:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voice call not found"
        )

    if call.status != "ongoing":

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only ongoing calls can be ended"
        )

    if not call.start_time:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Call start time not found"
        )

    end_time = datetime.now(
        timezone.utc
    )

    start_time = call.start_time

    if start_time.tzinfo is None:

        start_time = start_time.replace(
            tzinfo=timezone.utc
        )

    duration_seconds = (
        end_time - start_time
    ).total_seconds()

    # ------------------------------------------------------
    # FREE CALL MAXIMUM = 2 SECONDS
    # ------------------------------------------------------

    if call.is_free_call:

        duration_seconds = min(
            duration_seconds,
            FREE_CALL_DURATION_SECONDS
        )

    duration_hours = round(
        duration_seconds / 3600,
        2
    )

    call.end_time = end_time

    call.duration = Decimal(
        str(duration_hours)
    )

    call.status = "ended"

    db.commit()

    db.refresh(call)

    return call


# ==========================================================
# GET SINGLE VOICE CALL
# ==========================================================

@router.get(
    "/{call_id}",
    response_model=VoiceCallResponse
)
def get_voice_call(
    call_id: str,
    db: Session = Depends(get_db)
):

    call = (
        db.query(VoiceCall)
        .filter(
            VoiceCall.call_id == call_id
        )
        .first()
    )

    if not call:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voice call not found"
        )

    return call


# ==========================================================
# UPDATE VOICE CALL
# ==========================================================

@router.put(
    "/{call_id}",
    response_model=VoiceCallResponse
)
def update_voice_call(
    call_id: str,
    data: VoiceCallUpdate,
    db: Session = Depends(get_db)
):

    call = (
        db.query(VoiceCall)
        .filter(
            VoiceCall.call_id == call_id
        )
        .first()
    )

    if not call:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voice call not found"
        )

    update_data = data.model_dump(
        exclude_unset=True
    )

    for key, value in update_data.items():

        setattr(
            call,
            key,
            value
        )

    db.commit()

    db.refresh(call)

    return call


# ==========================================================
# DELETE VOICE CALL
# ==========================================================

@router.delete(
    "/{call_id}"
)
def delete_voice_call(
    call_id: str,
    db: Session = Depends(get_db)
):

    call = (
        db.query(VoiceCall)
        .filter(
            VoiceCall.call_id == call_id
        )
        .first()
    )

    if not call:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voice call not found"
        )

    db.delete(call)

    db.commit()

    return {
        "status": 200,
        "message": "Voice call deleted successfully"
    }