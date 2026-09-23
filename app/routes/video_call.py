import threading
import time

from datetime import datetime, date, timezone
from decimal import Decimal

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query
)

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from database import get_db

from models.users import User
from models.user_status import UserStatus
from models.video_call import VideoCall
from models.wallet import Wallet

from schemas.video_call import (
    VideoCallInitiate,
    VideoCallCreate,
    VideoCallUpdate,
    VideoCallResponse
)


router = APIRouter(
    prefix="/video-calls",
    tags=["Video Calls"]
)


# ==========================================================
# CONSTANTS
# ==========================================================

FREE_CALL_DURATION_SECONDS = 2
PAID_CALL_COINS = 200


# ==========================================================
# GENERATE VIDEO CALL ID
# FORMAT: VIDEO-YYYY-MM-DD-01
# ==========================================================

def generate_video_call_id(db: Session):

    today = datetime.now(timezone.utc).date()

    date_part = today.strftime("%Y-%m-%d")

    prefix = f"VIDEO-{date_part}-"

    last_call = (
        db.query(VideoCall)
        .filter(
            VideoCall.video_call_id.like(
                f"{prefix}%"
            )
        )
        .order_by(
            VideoCall.id.desc()
        )
        .first()
    )

    if last_call:
        try:
            last_number = int(
                last_call.video_call_id.split("-")[-1]
            )
            next_number = last_number + 1

        except (ValueError, IndexError):
            next_number = 1

    else:
        next_number = 1

    return f"{prefix}{next_number:02d}"


# ==========================================================
# VALIDATE CUSTOMER AND CREATOR
# ==========================================================

def validate_customer_creator(
    db: Session,
    customer_id: int,
    creator_id: int,
    caller_id: int,
    receiver_id: int
):

    customer = db.query(User).filter(
        User.id == customer_id
    ).first()

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    creator = db.query(User).filter(
        User.id == creator_id
    ).first()

    if not creator:
        raise HTTPException(
            status_code=404,
            detail="Creator not found"
        )

    caller = db.query(User).filter(
        User.id == caller_id
    ).first()

    if not caller:
        raise HTTPException(
            status_code=404,
            detail="Caller not found"
        )

    receiver = db.query(User).filter(
        User.id == receiver_id
    ).first()

    if not receiver:
        raise HTTPException(
            status_code=404,
            detail="Receiver not found"
        )

    if customer.role != "customer":
        raise HTTPException(
            status_code=400,
            detail="customer_id must belong to a customer"
        )

    if creator.role != "creator":
        raise HTTPException(
            status_code=400,
            detail="creator_id must belong to a creator"
        )

    valid_direction = (
        caller_id == customer_id
        and receiver_id == creator_id
    ) or (
        caller_id == creator_id
        and receiver_id == customer_id
    )

    if not valid_direction:
        raise HTTPException(
            status_code=400,
            detail="Caller and receiver must be customer and creator"
        )

    return customer, creator, caller, receiver


# ==========================================================
# CHECK FIRST FREE CALL
# ==========================================================

def is_first_free_call(
    db: Session,
    customer_id: int
):

    previous_free_call = (
        db.query(VideoCall)
        .filter(
            VideoCall.customer_id == customer_id,
            VideoCall.is_free_call.is_(True)
        )
        .first()
    )

    return previous_free_call is None


# ==========================================================
# CHECK WALLET FOR PAID CALL
# ==========================================================

def check_wallet_balance(
    db: Session,
    caller_id: int
):

    wallet = (
        db.query(Wallet)
        .filter(
            Wallet.user_id == caller_id
        )
        .first()
    )

    if not wallet:
        raise HTTPException(
            status_code=404,
            detail="Wallet not found"
        )

    if wallet.coins < PAID_CALL_COINS:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient coins. {PAID_CALL_COINS} coins required"
        )

    return wallet


# ==========================================================
# AUTO END FREE VIDEO CALL
# ==========================================================

def auto_end_free_video_call(
    video_call_id: str
):

    time.sleep(
        FREE_CALL_DURATION_SECONDS
    )

    from database import SessionLocal

    db = SessionLocal()

    try:

        video_call = (
            db.query(VideoCall)
            .filter(
                VideoCall.video_call_id == video_call_id
            )
            .first()
        )

        if not video_call:
            return

        if not video_call.is_free_call:
            return

        if video_call.status != "ongoing":
            return

        if not video_call.start_time:
            return

        end_time = datetime.now(
            timezone.utc
        )

        start_time = video_call.start_time

        if start_time.tzinfo is None:
            start_time = start_time.replace(
                tzinfo=timezone.utc
            )

        duration_seconds = (
            end_time - start_time
        ).total_seconds()

        if duration_seconds < 0:
            duration_seconds = 0

        if duration_seconds > FREE_CALL_DURATION_SECONDS:
            duration_seconds = FREE_CALL_DURATION_SECONDS

        duration_hours = round(
            duration_seconds / 3600,
            2
        )

        video_call.end_time = end_time

        video_call.duration = Decimal(
            str(duration_hours)
        )

        video_call.coins = 0

        video_call.revenue = Decimal(
            "0.00"
        )

        video_call.status = "completed"

        db.commit()

    except Exception:

        db.rollback()

    finally:

        db.close()


# ==========================================================
# INITIATE VIDEO CALL
# ==========================================================

@router.post(
    "/initiate",
    response_model=VideoCallResponse,
    status_code=201
)
def initiate_video_call(
    request: VideoCallInitiate,
    db: Session = Depends(get_db)
):

    if request.caller_id == request.receiver_id:
        raise HTTPException(
            status_code=400,
            detail="Caller and receiver cannot be the same user"
        )

    caller = db.query(User).filter(
        User.id == request.caller_id
    ).first()

    if not caller:
        raise HTTPException(
            status_code=404,
            detail="Caller not found"
        )

    receiver = db.query(User).filter(
        User.id == request.receiver_id
    ).first()

    if not receiver:
        raise HTTPException(
            status_code=404,
            detail="Receiver not found"
        )

    if caller.role not in [
        "customer",
        "creator"
    ]:
        raise HTTPException(
            status_code=400,
            detail="Caller must be a customer or creator"
        )

    if receiver.role not in [
        "customer",
        "creator"
    ]:
        raise HTTPException(
            status_code=400,
            detail="Receiver must be a customer or creator"
        )

    if caller.role == receiver.role:
        raise HTTPException(
            status_code=400,
            detail="Video call is allowed only between customer and creator"
        )

    # ------------------------------------------------------
    # CUSTOMER / CREATOR MAPPING
    # ------------------------------------------------------

    if caller.role == "customer":

        customer_id = caller.id
        creator_id = receiver.id

    else:

        customer_id = receiver.id
        creator_id = caller.id

    # ------------------------------------------------------
    # CHECK ACTIVE CALL
    # ------------------------------------------------------

    active_call = db.query(VideoCall).filter(
        VideoCall.status.in_(
            ["ringing", "ongoing"]
        ),
        or_(
            (
                VideoCall.caller_id == request.caller_id
            ) & (
                VideoCall.receiver_id == request.receiver_id
            ),
            (
                VideoCall.caller_id == request.receiver_id
            ) & (
                VideoCall.receiver_id == request.caller_id
            )
        )
    ).first()

    if active_call:
        raise HTTPException(
            status_code=400,
            detail="An active video call already exists between these users"
        )

    # ------------------------------------------------------
    # ONLINE STATUS IS INFORMATIONAL ONLY
    # OFFLINE USER WILL NOT BLOCK CALL
    # ------------------------------------------------------

    caller_status = db.query(UserStatus).filter(
        UserStatus.user_id == request.caller_id
    ).first()

    receiver_status = db.query(UserStatus).filter(
        UserStatus.user_id == request.receiver_id
    ).first()

    # ------------------------------------------------------
    # FIRST FREE CALL
    # ------------------------------------------------------

    free_call = is_first_free_call(
        db=db,
        customer_id=customer_id
    )

    # ------------------------------------------------------
    # PAID CALL - CHECK WALLET ONLY
    # ACTUAL DEDUCTION WILL HAPPEN AT ACCEPT
    # ------------------------------------------------------

    if not free_call:

        check_wallet_balance(
            db=db,
            caller_id=request.caller_id
        )

    # ------------------------------------------------------
    # CREATE VIDEO CALL
    # ------------------------------------------------------

    video_call = VideoCall(
        video_call_id=generate_video_call_id(db),

        customer_id=customer_id,
        creator_id=creator_id,

        caller_id=request.caller_id,
        receiver_id=request.receiver_id,

        start_time=None,
        end_time=None,

        duration=Decimal("0.00"),

        coins=0,

        revenue=Decimal("0.00"),

        status="ringing",

        is_free_call=free_call
    )

    db.add(video_call)

    db.commit()

    db.refresh(video_call)

    return video_call


# ==========================================================
# MANUAL CREATE VIDEO CALL
# ==========================================================

@router.post(
    "/",
    response_model=VideoCallResponse,
    status_code=201
)
def create_video_call(
    request: VideoCallCreate,
    db: Session = Depends(get_db)
):

    if request.caller_id == request.receiver_id:
        raise HTTPException(
            status_code=400,
            detail="Caller and receiver cannot be the same user"
        )

    validate_customer_creator(
        db=db,
        customer_id=request.customer_id,
        creator_id=request.creator_id,
        caller_id=request.caller_id,
        receiver_id=request.receiver_id
    )

    active_call = db.query(VideoCall).filter(
        VideoCall.status.in_(
            ["ringing", "ongoing"]
        ),
        or_(
            (
                VideoCall.caller_id == request.caller_id
            ) & (
                VideoCall.receiver_id == request.receiver_id
            ),
            (
                VideoCall.caller_id == request.receiver_id
            ) & (
                VideoCall.receiver_id == request.caller_id
            )
        )
    ).first()

    if active_call:
        raise HTTPException(
            status_code=400,
            detail="An active video call already exists between these users"
        )

    # ------------------------------------------------------
    # FIRST FREE CALL
    # ------------------------------------------------------

    free_call = is_first_free_call(
        db=db,
        customer_id=request.customer_id
    )

    # ------------------------------------------------------
    # PAID CALL WALLET CHECK
    # ------------------------------------------------------

    if not free_call:

        check_wallet_balance(
            db=db,
            caller_id=request.caller_id
        )

    # ------------------------------------------------------
    # CREATE
    # ------------------------------------------------------

    video_call = VideoCall(
        video_call_id=generate_video_call_id(db),

        customer_id=request.customer_id,
        creator_id=request.creator_id,

        caller_id=request.caller_id,
        receiver_id=request.receiver_id,

        start_time=None,
        end_time=None,

        duration=Decimal("0.00"),

        coins=0,

        revenue=Decimal("0.00"),

        status="ringing",

        is_free_call=free_call
    )

    db.add(video_call)

    db.commit()

    db.refresh(video_call)

    return video_call


# ==========================================================
# GET ALL VIDEO CALLS
# ==========================================================

@router.get(
    "/",
    response_model=list[VideoCallResponse]
)
def get_all_video_calls(
    call_date: date | None = Query(
        default=None
    ),

    start_date: date | None = Query(
        default=None
    ),

    end_date: date | None = Query(
        default=None
    ),

    customer_id: int | None = Query(
        default=None
    ),

    creator_id: int | None = Query(
        default=None
    ),

    caller_id: int | None = Query(
        default=None
    ),

    receiver_id: int | None = Query(
        default=None
    ),

    status: str | None = Query(
        default=None
    ),

    db: Session = Depends(get_db)
):

    query = db.query(VideoCall)

    if call_date:

        query = query.filter(
            func.date(VideoCall.created_at)
            == call_date
        )

    if start_date:

        query = query.filter(
            func.date(VideoCall.created_at)
            >= start_date
        )

    if end_date:

        query = query.filter(
            func.date(VideoCall.created_at)
            <= end_date
        )

    if customer_id:

        query = query.filter(
            VideoCall.customer_id
            == customer_id
        )

    if creator_id:

        query = query.filter(
            VideoCall.creator_id
            == creator_id
        )

    if caller_id:

        query = query.filter(
            VideoCall.caller_id
            == caller_id
        )

    if receiver_id:

        query = query.filter(
            VideoCall.receiver_id
            == receiver_id
        )

    if status:

        query = query.filter(
            VideoCall.status
            == status
        )

    video_calls = query.order_by(
        VideoCall.id.desc()
    ).all()

    if not video_calls:

        raise HTTPException(
            status_code=404,
            detail="No video calls found"
        )

    return video_calls


# ==========================================================
# ACCEPT VIDEO CALL
# ==========================================================

@router.post(
    "/{video_call_id}/accept",
    response_model=VideoCallResponse
)
def accept_video_call(
    video_call_id: str,
    db: Session = Depends(get_db)
):

    video_call = db.query(VideoCall).filter(
        VideoCall.video_call_id
        == video_call_id
    ).first()

    if not video_call:

        raise HTTPException(
            status_code=404,
            detail="Video call not found"
        )

    if video_call.status != "ringing":

        raise HTTPException(
            status_code=400,
            detail="Only ringing video calls can be accepted"
        )

    # ======================================================
    # PAID CALL - DEDUCT 200 COINS
    # ======================================================

    if not video_call.is_free_call:

        wallet = (
            db.query(Wallet)
            .filter(
                Wallet.user_id
                == video_call.caller_id
            )
            .with_for_update()
            .first()
        )

        if not wallet:

            raise HTTPException(
                status_code=404,
                detail="Wallet not found"
            )

        if wallet.coins < PAID_CALL_COINS:

            raise HTTPException(
                status_code=400,
                detail=f"Insufficient coins. {PAID_CALL_COINS} coins required"
            )

        wallet.coins -= PAID_CALL_COINS

        wallet.spending = (
            wallet.spending or Decimal("0.00")
        ) + Decimal(
            str(PAID_CALL_COINS)
        )

        wallet.last_transaction = datetime.now(
            timezone.utc
        )

        video_call.coins = PAID_CALL_COINS

        video_call.revenue = Decimal(
            str(PAID_CALL_COINS)
        )

    else:

        video_call.coins = 0

        video_call.revenue = Decimal(
            "0.00"
        )

    # ======================================================
    # START CALL
    # ======================================================

    video_call.status = "ongoing"

    video_call.start_time = datetime.now(
        timezone.utc
    )

    db.commit()

    db.refresh(video_call)

    # ======================================================
    # FREE CALL AUTO END AFTER 2 SECONDS
    # ======================================================

    if video_call.is_free_call:

        thread = threading.Thread(
            target=auto_end_free_video_call,
            args=(video_call.video_call_id,),
            daemon=True
        )

        thread.start()

    return video_call


# ==========================================================
# REJECT VIDEO CALL
# ==========================================================

@router.post(
    "/{video_call_id}/reject",
    response_model=VideoCallResponse
)
def reject_video_call(
    video_call_id: str,
    db: Session = Depends(get_db)
):

    video_call = db.query(VideoCall).filter(
        VideoCall.video_call_id
        == video_call_id
    ).first()

    if not video_call:

        raise HTTPException(
            status_code=404,
            detail="Video call not found"
        )

    if video_call.status != "ringing":

        raise HTTPException(
            status_code=400,
            detail="Only ringing video calls can be rejected"
        )

    video_call.status = "rejected"

    video_call.end_time = datetime.now(
        timezone.utc
    )

    video_call.duration = Decimal(
        "0.00"
    )

    video_call.coins = 0

    video_call.revenue = Decimal(
        "0.00"
    )

    db.commit()

    db.refresh(video_call)

    return video_call


# ==========================================================
# END VIDEO CALL
# ==========================================================

@router.post(
    "/{video_call_id}/end",
    response_model=VideoCallResponse
)
def end_video_call(
    video_call_id: str,
    db: Session = Depends(get_db)
):

    video_call = db.query(VideoCall).filter(
        VideoCall.video_call_id
        == video_call_id
    ).first()

    if not video_call:

        raise HTTPException(
            status_code=404,
            detail="Video call not found"
        )

    if video_call.status != "ongoing":

        raise HTTPException(
            status_code=400,
            detail="Only ongoing video calls can be ended"
        )

    if video_call.start_time is None:

        raise HTTPException(
            status_code=400,
            detail="Video call start time is missing"
        )

    end_time = datetime.now(
        timezone.utc
    )

    start_time = video_call.start_time

    if start_time.tzinfo is None:

        start_time = start_time.replace(
            tzinfo=timezone.utc
        )

    duration_seconds = (
        end_time - start_time
    ).total_seconds()

    if duration_seconds < 0:

        duration_seconds = 0

    # ------------------------------------------------------
    # FREE CALL MAX 2 SECONDS
    # ------------------------------------------------------

    if video_call.is_free_call:

        duration_seconds = min(
            duration_seconds,
            FREE_CALL_DURATION_SECONDS
        )

    duration_hours = round(
        duration_seconds / 3600,
        2
    )

    video_call.end_time = end_time

    video_call.duration = Decimal(
        str(duration_hours)
    )

    video_call.status = "completed"

    # Free call should never have coins/revenue
    if video_call.is_free_call:

        video_call.coins = 0

        video_call.revenue = Decimal(
            "0.00"
        )

    db.commit()

    db.refresh(video_call)

    return video_call


# ==========================================================
# GET SINGLE VIDEO CALL
# ==========================================================

@router.get(
    "/{video_call_id}",
    response_model=VideoCallResponse
)
def get_video_call(
    video_call_id: str,
    db: Session = Depends(get_db)
):

    video_call = db.query(VideoCall).filter(
        VideoCall.video_call_id
        == video_call_id
    ).first()

    if not video_call:

        raise HTTPException(
            status_code=404,
            detail="Video call not found"
        )

    return video_call


# ==========================================================
# UPDATE VIDEO CALL
# ==========================================================

@router.put(
    "/{video_call_id}",
    response_model=VideoCallResponse
)
def update_video_call(
    video_call_id: str,
    request: VideoCallUpdate,
    db: Session = Depends(get_db)
):

    video_call = db.query(VideoCall).filter(
        VideoCall.video_call_id
        == video_call_id
    ).first()

    if not video_call:

        raise HTTPException(
            status_code=404,
            detail="Video call not found"
        )

    update_data = request.model_dump(
        exclude_unset=True
    )

    for key, value in update_data.items():

        setattr(
            video_call,
            key,
            value
        )

    db.commit()

    db.refresh(video_call)

    return video_call


# ==========================================================
# DELETE VIDEO CALL
# ==========================================================

@router.delete(
    "/{video_call_id}"
)
def delete_video_call(
    video_call_id: str,
    db: Session = Depends(get_db)
):

    video_call = db.query(VideoCall).filter(
        VideoCall.video_call_id
        == video_call_id
    ).first()

    if not video_call:

        raise HTTPException(
            status_code=404,
            detail="Video call not found"
        )

    db.delete(video_call)

    db.commit()

    return {
        "status": True,
        "message": "Video call deleted successfully"
    }