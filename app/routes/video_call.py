import logging
import uuid

from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import or_

from database import SessionLocal

from models.users import User
from models.wallet import Wallet
from models.video_call import VideoCall
from models.pricing_details import PricingDetail
from models.chat_history import Chat

from schemas.video_call import VideoCallInitiateRequest

# IMPORTANT:
# Use the same WebSocket manager as voice_call.py.
# This must be the manager used by /ws/chat/{chat_id}.
from routes.websocket_routes import manager


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/video-calls",
    tags=["Video Calls"],
)


# =====================================================
# CONFIGURATION
# =====================================================

FREE_CALL_DURATION_SECONDS = 2

COINS_PER_RUPEE = Decimal("1")

PRICE_PER_MINUTE = True


# =====================================================
# DATABASE
# =====================================================

def get_db():
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


# =====================================================
# HELPERS
# =====================================================

def generate_call_id():

    return f"VC-{uuid.uuid4().hex[:20].upper()}"


def get_creator_pricing(
    db: Session,
    creator_id: int,
):

    pricing = (
        db.query(PricingDetail)
        .filter(
            PricingDetail.user_id == creator_id
        )
        .first()
    )

    if not pricing:

        raise HTTPException(
            status_code=404,
            detail="Creator pricing details not found",
        )

    return pricing


def get_wallet(
    db: Session,
    user_id: int,
    lock: bool = False,
):

    query = (
        db.query(Wallet)
        .filter(
            Wallet.user_id == user_id
        )
    )

    if lock:

        query = query.with_for_update()

    wallet = query.first()

    if not wallet:

        raise HTTPException(
            status_code=404,
            detail="Wallet not found",
        )

    return wallet


def get_video_call(
    db: Session,
    call_id: str,
    lock: bool = False,
):

    query = (
        db.query(VideoCall)
        .filter(
            VideoCall.video_call_id == call_id
        )
    )

    if lock:

        query = query.with_for_update()

    call = query.first()

    if not call:

        raise HTTPException(
            status_code=404,
            detail="Video call not found",
        )

    return call


# =====================================================
# CALCULATE CALL CHARGE
# =====================================================

def calculate_call_charge(
    price_per_minute: Decimal,
    duration_seconds: int,
):

    if duration_seconds <= 0:

        return Decimal("0.00"), 0

    if PRICE_PER_MINUTE:

        amount = (
            price_per_minute
            * Decimal(duration_seconds)
            / Decimal("60")
        )

    else:

        amount = price_per_minute

    amount = amount.quantize(
        Decimal("0.01")
    )

    coins = int(
        (
            amount
            * COINS_PER_RUPEE
        ).quantize(
            Decimal("1"),
            rounding=ROUND_CEILING,
        )
    )

    return amount, coins


# =====================================================
# SERIALIZE VIDEO CALL
# =====================================================

def serialize_call(
    call: VideoCall,
):

    return {

        "call_id": call.video_call_id,

        "video_call_id": call.video_call_id,

        "customer_id": call.customer_id,

        "creator_id": call.creator_id,

        "caller_id": call.caller_id,

        "receiver_id": call.receiver_id,

        "start_time": (
            call.start_time.isoformat()
            if call.start_time
            else None
        ),

        "end_time": (
            call.end_time.isoformat()
            if call.end_time
            else None
        ),

        "duration": float(
            call.duration or 0
        ),

        "coins": int(
            call.coins or 0
        ),

        "revenue": float(
            call.revenue or 0
        ),

        "status": call.status,

        "is_free_call": bool(
            call.is_free_call
        ),

        "created_at": (
            call.created_at.isoformat()
            if call.created_at
            else None
        ),

        "updated_at": (
            call.updated_at.isoformat()
            if call.updated_at
            else None
        ),
    }


# =====================================================
# CHAT LOOKUP
# =====================================================

def get_call_chat(
    db: Session,
    customer_id: int,
    creator_id: int,
):
    """
    Find the existing chat between customer and creator.

    This matches the voice call chat lookup.

    It does not require Chat.status=True because
    the voice call implementation does not use
    that condition.
    """

    chat = (
        db.query(Chat)
        .filter(
            or_(
                (
                    Chat.user_one_id == customer_id
                )
                &
                (
                    Chat.user_two_id == creator_id
                ),

                (
                    Chat.user_one_id == creator_id
                )
                &
                (
                    Chat.user_two_id == customer_id
                ),
            )
        )
        .first()
    )

    return chat


# =====================================================
# WEBSOCKET NOTIFICATION
# =====================================================

async def notify_call_participants(
    db: Session,
    call: VideoCall,
    event_type: str,
):
    """
    Send video call lifecycle events to the existing chat room.

    Uses the same manager import as voice_call.py.

    Events:
        video_call
        video_call_accepted
        video_call_rejected
        video_call_ended
    """

    chat = get_call_chat(
        db,
        call.customer_id,
        call.creator_id,
    )

    if not chat:

        logger.error(
            "VIDEO CALL CHAT NOT FOUND "
            "customer_id=%s creator_id=%s call_id=%s",
            call.customer_id,
            call.creator_id,
            call.video_call_id,
        )

        return False

    payload = {

        "type": event_type,

        "call_id": call.video_call_id,

        "video_call_id": call.video_call_id,

        "chat_id": chat.id,

        "customer_id": call.customer_id,

        "creator_id": call.creator_id,

        "caller_id": call.caller_id,

        "receiver_id": call.receiver_id,

        "status": call.status,

        "is_free_call": bool(
            call.is_free_call
        ),
    }

    try:

        await manager.broadcast(
            chat.id,
            payload,
        )

        logger.info(
            "VIDEO CALL EVENT BROADCAST "
            "type=%s chat_id=%s call_id=%s "
            "caller_id=%s receiver_id=%s status=%s",
            event_type,
            chat.id,
            call.video_call_id,
            call.caller_id,
            call.receiver_id,
            call.status,
        )

        return True

    except Exception:

        logger.exception(
            "VIDEO CALL WEBSOCKET BROADCAST FAILED "
            "chat_id=%s call_id=%s",
            chat.id,
            call.video_call_id,
        )

        return False


# =====================================================
# INITIATE VIDEO CALL
# POST /video-calls/initiate
# =====================================================

@router.post(
    "/initiate",
    status_code=status.HTTP_201_CREATED,
)
async def initiate_video_call(
    data: VideoCallInitiateRequest,
    db: Session = Depends(get_db),
):

    try:

        caller_id = data.caller_id

        receiver_id = data.receiver_id

        # =============================================
        # GET CALLER
        # =============================================

        caller = (
            db.query(User)
            .filter(
                User.id == caller_id
            )
            .first()
        )

        if not caller:

            raise HTTPException(
                status_code=404,
                detail="Caller not found",
            )

        # =============================================
        # GET RECEIVER
        # =============================================

        receiver = (
            db.query(User)
            .filter(
                User.id == receiver_id
            )
            .first()
        )

        if not receiver:

            raise HTTPException(
                status_code=404,
                detail="Receiver not found",
            )

        # =============================================
        # VALIDATE CALLER / RECEIVER
        # =============================================

        if caller_id == receiver_id:

            raise HTTPException(
                status_code=400,
                detail="You cannot call yourself",
            )

        # =============================================
        # CUSTOMER / CREATOR MAPPING
        # =============================================

        if (
            caller.role == "customer"
            and receiver.role == "creator"
        ):

            customer_id = caller.id

            creator_id = receiver.id

        elif (
            caller.role == "creator"
            and receiver.role == "customer"
        ):

            customer_id = receiver.id

            creator_id = caller.id

        else:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Video call must be between "
                    "a customer and a creator"
                ),
            )

        # =============================================
        # FIND CHAT
        # =============================================

        chat = get_call_chat(
            db,
            customer_id,
            creator_id,
        )

        if not chat:

            raise HTTPException(
                status_code=404,
                detail=(
                    "Chat not found between "
                    "customer and creator"
                ),
            )

        # =============================================
        # CHECK CREATOR PRICING
        # =============================================

        pricing = get_creator_pricing(
            db,
            creator_id,
        )

        video_price = Decimal(
            str(
                pricing.video_call_amount or 0
            )
        )

        if video_price <= 0:

            raise HTTPException(
                status_code=400,
                detail="Creator video call price is invalid",
            )

        # =============================================
        # CHECK EXISTING FREE CALL
        # =============================================

        previous_free_call = (
            db.query(VideoCall)
            .filter(
                VideoCall.customer_id == customer_id,

                VideoCall.creator_id == creator_id,

                VideoCall.is_free_call.is_(True),

                VideoCall.status == "completed",
            )
            .first()
        )

        is_free_call = (
            previous_free_call is None
        )

        # =============================================
        # CHECK CUSTOMER WALLET
        # =============================================

        wallet = get_wallet(
            db,
            customer_id,
        )

        if not is_free_call:

            _, minimum_coins = calculate_call_charge(
                video_price,
                60,
            )

            if wallet.coins < minimum_coins:

                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": "Insufficient wallet balance",

                        "required_coins": minimum_coins,

                        "available_coins": wallet.coins,
                    },
                )

        # =============================================
        # CHECK EXISTING ACTIVE CALL
        # =============================================

        existing_call = (
            db.query(VideoCall)
            .filter(
                VideoCall.customer_id == customer_id,

                VideoCall.creator_id == creator_id,

                VideoCall.status.in_([
                    "ringing",
                    "ongoing",
                ]),
            )
            .first()
        )

        if existing_call:

            raise HTTPException(
                status_code=400,
                detail={
                    "message": (
                        "An active video call "
                        "already exists"
                    ),

                    "call_id": (
                        existing_call.video_call_id
                    ),

                    "status": existing_call.status,
                },
            )

        # =============================================
        # CREATE VIDEO CALL
        # =============================================

        call = VideoCall(

            video_call_id=generate_call_id(),

            customer_id=customer_id,

            creator_id=creator_id,

            caller_id=caller_id,

            receiver_id=receiver_id,

            start_time=None,

            end_time=None,

            duration=Decimal("0.00"),

            coins=0,

            revenue=Decimal("0.00"),

            status="ringing",

            is_free_call=is_free_call,
        )

        db.add(call)

        db.commit()

        db.refresh(call)

        # =============================================
        # BROADCAST INCOMING CALL
        # =============================================

        notification_sent = (
            await notify_call_participants(
                db=db,
                call=call,
                event_type="video_call",
            )
        )

        # =============================================
        # RESPONSE
        # =============================================

        return {

            "message": (
                "Video call initiated successfully"
                if notification_sent
                else (
                    "Video call created, "
                    "but notification could not be sent"
                )
            ),

            "notification_sent": notification_sent,

            "call": serialize_call(call),

            "call_id": call.video_call_id,

            "video_call_id": call.video_call_id,

            "is_free_call": call.is_free_call,
        }

    except HTTPException:

        db.rollback()

        raise

    except SQLAlchemyError:

        db.rollback()

        logger.exception(
            "VIDEO CALL INITIATION DATABASE ERROR"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Database error while "
                "initiating video call"
            ),
        )

    except Exception:

        db.rollback()

        logger.exception(
            "VIDEO CALL INITIATION FAILED"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to initiate video call",
        )


# =====================================================
# ACCEPT VIDEO CALL
# POST /video-calls/{call_id}/accept
# =====================================================

@router.post(
    "/{call_id}/accept",
)
async def accept_video_call(
    call_id: str,
    db: Session = Depends(get_db),
):

    try:

        # =============================================
        # GET CALL
        # =============================================

        call = get_video_call(
            db,
            call_id,
            lock=True,
        )

        if call.status != "ringing":

            raise HTTPException(
                status_code=400,
                detail="Call cannot be accepted",
            )

        # =============================================
        # GET CREATOR
        # =============================================

        creator = (
            db.query(User)
            .filter(
                User.id == call.creator_id
            )
            .first()
        )

        if not creator:

            raise HTTPException(
                status_code=404,
                detail="Creator not found",
            )

        # =============================================
        # GET PRICING
        # =============================================

        pricing = get_creator_pricing(
            db,
            call.creator_id,
        )

        video_price = Decimal(
            str(
                pricing.video_call_amount or 0
            )
        )

        # =============================================
        # CHECK WALLET
        # =============================================

        if not call.is_free_call:

            wallet = get_wallet(
                db,
                call.customer_id,
                lock=True,
            )

            _, minimum_coins = calculate_call_charge(
                video_price,
                60,
            )

            if wallet.coins < minimum_coins:

                call.status = "rejected"

                call.end_time = datetime.now(
                    timezone.utc
                )

                db.commit()

                db.refresh(call)

                await notify_call_participants(
                    db,
                    call,
                    "video_call_rejected",
                )

                raise HTTPException(
                    status_code=400,
                    detail="Insufficient wallet balance",
                )

        # =============================================
        # ACCEPT CALL
        # =============================================

        call.start_time = datetime.now(
            timezone.utc
        )

        call.status = "ongoing"

        db.commit()

        db.refresh(call)

        # =============================================
        # NOTIFY BOTH PARTICIPANTS
        # =============================================

        await notify_call_participants(
            db,
            call,
            "video_call_accepted",
        )

        # =============================================
        # RESPONSE
        # =============================================

        return {

            "message": "Video call accepted",

            "call": serialize_call(call),

            "pricing": {

                "video_call_amount": float(
                    video_price
                ),

                "price_type": "per_minute",
            },
        }

    except HTTPException:

        db.rollback()

        raise

    except SQLAlchemyError:

        db.rollback()

        logger.exception(
            "VIDEO CALL ACCEPT DATABASE ERROR"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Database error while "
                "accepting video call"
            ),
        )

    except Exception:

        db.rollback()

        logger.exception(
            "VIDEO CALL ACCEPT FAILED"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to accept video call",
        )


# =====================================================
# REJECT VIDEO CALL
# POST /video-calls/{call_id}/reject
# =====================================================

@router.post(
    "/{call_id}/reject",
)
async def reject_video_call(
    call_id: str,
    db: Session = Depends(get_db),
):

    try:

        call = get_video_call(
            db,
            call_id,
            lock=True,
        )

        if call.status != "ringing":

            raise HTTPException(
                status_code=400,
                detail=(
                    "Only ringing calls "
                    "can be rejected"
                ),
            )

        # =============================================
        # REJECT
        # =============================================

        call.status = "rejected"

        call.end_time = datetime.now(
            timezone.utc
        )

        call.duration = Decimal("0.00")

        db.commit()

        db.refresh(call)

        # =============================================
        # NOTIFY BOTH PARTICIPANTS
        # =============================================

        await notify_call_participants(
            db,
            call,
            "video_call_rejected",
        )

        return {

            "message": "Video call rejected",

            "call": serialize_call(call),
        }

    except HTTPException:

        db.rollback()

        raise

    except SQLAlchemyError:

        db.rollback()

        logger.exception(
            "VIDEO CALL REJECT DATABASE ERROR"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Database error while "
                "rejecting video call"
            ),
        )

    except Exception:

        db.rollback()

        logger.exception(
            "VIDEO CALL REJECT FAILED"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to reject video call",
        )


# =====================================================
# END VIDEO CALL
# POST /video-calls/{call_id}/end
# =====================================================

@router.post(
    "/{call_id}/end",
)
async def end_video_call(
    call_id: str,
    db: Session = Depends(get_db),
):

    try:

        # =============================================
        # GET CALL
        # =============================================

        call = get_video_call(
            db,
            call_id,
            lock=True,
        )

        if call.status != "ongoing":

            raise HTTPException(
                status_code=400,
                detail="Call is not ongoing",
            )

        # =============================================
        # CHECK START TIME
        # =============================================

        if not call.start_time:

            raise HTTPException(
                status_code=400,
                detail="Call start time not found",
            )

        now = datetime.now(
            timezone.utc
        )

        start_time = call.start_time

        if start_time.tzinfo is None:

            start_time = start_time.replace(
                tzinfo=timezone.utc
            )

        duration_seconds = max(
            0,
            int(
                (
                    now - start_time
                ).total_seconds()
            ),
        )

        # =============================================
        # FREE CALL
        # =============================================

        if call.is_free_call:

            duration_seconds = min(
                duration_seconds,
                FREE_CALL_DURATION_SECONDS,
            )

            call.coins = 0

            call.revenue = Decimal("0.00")

        # =============================================
        # PAID CALL
        # =============================================

        else:

            pricing = get_creator_pricing(
                db,
                call.creator_id,
            )

            video_price = Decimal(
                str(
                    pricing.video_call_amount or 0
                )
            )

            amount, coins_to_deduct = (
                calculate_call_charge(
                    video_price,
                duration_seconds,
                )
            )

            wallet = get_wallet(
                db,
                call.customer_id,
                lock=True,
            )

            if wallet.coins < coins_to_deduct:

                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": (
                            "Insufficient balance "
                            "to complete call"
                        ),

                        "required_coins": (
                            coins_to_deduct
                        ),

                        "available_coins": (
                            wallet.coins
                        ),
                    },
                )

            # =========================================
            # DEDUCT CUSTOMER WALLET
            # =========================================

            wallet.coins = (
                wallet.coins
                - coins_to_deduct
            )

            wallet.total_spending = (
                Decimal(
                    str(
                        wallet.total_spending or 0
                    )
                )
                + amount
            )

            wallet.last_transaction = now

            # =========================================
            # STORE CALL BILLING
            # =========================================

            call.coins = coins_to_deduct

            call.revenue = amount

        # =============================================
        # SAVE CALL
        # =============================================

        call.duration = (
            Decimal(duration_seconds)
            / Decimal("3600")
        ).quantize(
            Decimal("0.01")
        )

        call.end_time = now

        call.status = "completed"

        db.commit()

        db.refresh(call)

        # =============================================
        # NOTIFY BOTH PARTICIPANTS
        # =============================================

        await notify_call_participants(
            db,
            call,
            "video_call_ended",
        )

        # =============================================
        # RESPONSE
        # =============================================

        return {

            "message": (
                "Video call ended successfully"
            ),

            "call": serialize_call(call),

            "billing": {

                "duration_seconds": (
                    duration_seconds
                ),

                "duration_minutes": round(
                    duration_seconds / 60,
                    2,
                ),

                "coins_deducted": int(
                    call.coins or 0
                ),

                "creator_revenue": float(
                    call.revenue or 0
                ),
            },
        }

    except HTTPException:

        db.rollback()

        raise

    except SQLAlchemyError:

        db.rollback()

        logger.exception(
            "VIDEO CALL END DATABASE ERROR"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Database error while "
                "ending video call"
            ),
        )

    except Exception:

        db.rollback()

        logger.exception(
            "VIDEO CALL END FAILED"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to end video call",
        )


# =====================================================
# CUSTOMER VIDEO CALL HISTORY
# GET /video-calls/customer/{customer_id}
# =====================================================

@router.get(
    "/customer/{customer_id}",
)
def get_customer_video_calls(
    customer_id: int,
    db: Session = Depends(get_db),
):

    calls = (
        db.query(VideoCall)
        .filter(
            VideoCall.customer_id == customer_id
        )
        .order_by(
            VideoCall.created_at.desc()
        )
        .all()
    )

    return {

        "total": len(calls),

        "calls": [
            serialize_call(call)
            for call in calls
        ],
    }


# =====================================================
# CREATOR VIDEO CALL HISTORY
# GET /video-calls/creator/{creator_id}
# =====================================================

@router.get(
    "/creator/{creator_id}",
)
def get_creator_video_calls(
    creator_id: int,
    db: Session = Depends(get_db),
):

    calls = (
        db.query(VideoCall)
        .filter(
            VideoCall.creator_id == creator_id
        )
        .order_by(
            VideoCall.created_at.desc()
        )
        .all()
    )

    return {

        "total": len(calls),

        "calls": [
            serialize_call(call)
            for call in calls
        ],
    }


# =====================================================
# GET VIDEO CALL DETAILS
# GET /video-calls/{call_id}
# =====================================================

@router.get(
    "/{call_id}",
)
def get_video_call_details(
    call_id: str,
    db: Session = Depends(get_db),
):

    call = get_video_call(
        db,
        call_id,
    )

    return {

        "message": "Video call details",

        "call": serialize_call(call),
    }
