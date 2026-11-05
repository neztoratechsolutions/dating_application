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
from models.earnings import Earning
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

# =====================================================
# UPDATE CREATOR EARNING
# =====================================================

def update_creator_earning(
    db: Session,
    creator_id: int,
    amount: Decimal,
):
    """
    Add video call revenue to creator earnings.

    First earning:
        Create Earning record.

    Existing earning:
        Update total_earned and balance.

    amount:
        Creator earning for this video call.
    """

    amount = Decimal(
        str(amount or 0)
    ).quantize(
        Decimal("0.01")
    )

    # =============================================
    # FREE CALL
    # =============================================

    if amount <= 0:

        return None

    # =============================================
    # GET CREATOR EARNING
    # =============================================

    earning = (
        db.query(Earning)
        .filter(
            Earning.user_id == creator_id
        )
        .with_for_update()
        .first()
    )

    # =============================================
    # CREATE EARNING RECORD
    # =============================================

    if not earning:

        earning = Earning(

            user_id=creator_id,

            total_earned=amount,

            withdrawal_amount=Decimal(
                "0.00"
            ),

            balance=amount,
        )

        db.add(earning)

    # =============================================
    # UPDATE EXISTING EARNING
    # =============================================

    else:

        earning.total_earned = (
            Decimal(
                str(
                    earning.total_earned or 0
                )
            )
            + amount
        )

        earning.balance = (
            Decimal(
                str(
                    earning.balance or 0
                )
            )
            + amount
        )

    return earning


from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP


def calculate_call_charge(
    price_per_minute: Decimal,
    duration_seconds: int,
):
    price_per_minute = Decimal(
        str(price_per_minute)
    )

    duration_seconds = Decimal(
        str(max(duration_seconds, 0))
    )

    if duration_seconds <= 0:
        return Decimal("0.00"), 0

    amount = (
        price_per_minute
        * duration_seconds
        / Decimal("60")
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )

    coins = int(
        (
            amount * COINS_PER_RUPEE
        ).to_integral_value(
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



# =====================================================
# WEBSOCKET NOTIFICATION
# =====================================================

async def notify_call_participants(
    db: Session,
    call: VideoCall,
    event_type: str,
):
    """
    Notify customer and creator about video call events.

    Events:
        video_call
        video_call_accepted
        video_call_ongoing
        video_call_rejected
        video_call_ended

    Uses the existing chat WebSocket room.
    """

    try:

        # =============================================
        # GET CUSTOMER / CREATOR CHAT
        # =============================================

        chat = get_call_chat(
            db=db,
            customer_id=call.customer_id,
            creator_id=call.creator_id,
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

        # =============================================
        # NORMALIZE EVENT TYPE
        # =============================================

        if event_type in [
            "video_call",
            "video_call_initiated",
        ]:

            event_name = "video_call"

            call_status = "ringing"

        elif event_type in [
            "video_call_accepted",
            "video_call_ongoing",
        ]:

            event_name = "video_call_accepted"

            call_status = "ongoing"

        elif event_type == "video_call_rejected":

            event_name = "video_call_rejected"

            call_status = "rejected"

        elif event_type == "video_call_ended":

            event_name = "video_call_ended"

            call_status = "ended"

        else:

            event_name = event_type

            call_status = call.status

        # =============================================
        # GET CALL DURATION
        # =============================================

        duration = float(
            call.duration or 0
        )

        # =============================================
        # GET CALL COINS
        # =============================================

        coins = int(
            call.coins or 0
        )

        # =============================================
        # GET CALL REVENUE
        # =============================================

        revenue = float(
            call.revenue or 0
        )

        # =============================================
        # GET START TIME
        # =============================================

        start_time = None

        if call.start_time:

            start_time = (
                call.start_time.isoformat()
            )

        # =============================================
        # GET END TIME
        # =============================================

        end_time = None

        if call.end_time:

            end_time = (
                call.end_time.isoformat()
            )

        # =============================================
        # CREATE WEBSOCKET PAYLOAD
        # =============================================

        payload = {

            # Event type used by frontend
            "type": "video_call",

            # Actual lifecycle event
            "event": event_name,

            # Call identifiers
            "call_id": call.video_call_id,

            "video_call_id": call.video_call_id,

            # Chat identifier
            "chat_id": chat.id,

            # Participants
            "customer_id": call.customer_id,

            "creator_id": call.creator_id,

            "caller_id": call.caller_id,

            "receiver_id": call.receiver_id,

            # Call status
            "status": call_status,

            # Free call
            "is_free_call": bool(
                call.is_free_call
            ),

            # Billing
            "coins": coins,

            "revenue": revenue,

            # Duration
            "duration": duration,

            # Timestamps
            "start_time": start_time,

            "end_time": end_time,

        }

        # =============================================
        # BROADCAST TO CHAT WEBSOCKET
        # =============================================

        await manager.broadcast(
            chat.id,
            payload,
        )

        # =============================================
        # LOG SUCCESS
        # =============================================

        logger.info(
            "VIDEO CALL WEBSOCKET EVENT SENT "
            "event=%s "
            "status=%s "
            "chat_id=%s "
            "call_id=%s "
            "customer_id=%s "
            "creator_id=%s",
            event_name,
            call_status,
            chat.id,
            call.video_call_id,
            call.customer_id,
            call.creator_id,
        )

        return True

    except Exception:

        # =============================================
        # LOG FAILURE
        # =============================================

        logger.exception(
            "VIDEO CALL WEBSOCKET NOTIFICATION FAILED "
            "call_id=%s "
            "event=%s",
            call.video_call_id,
            event_type,
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
        # =============================================
        # GET CALLER AND RECEIVER
        # =============================================

        caller_id = data.caller_id
        receiver_id = data.receiver_id

        caller = (
            db.query(User)
            .filter(User.id == caller_id)
            .first()
        )

        if not caller:
            raise HTTPException(
                status_code=404,
                detail="Caller not found",
            )

        receiver = (
            db.query(User)
            .filter(User.id == receiver_id)
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
            str(pricing.video_call_amount or 0)
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
                VideoCall.is_free_call.is_(True),
                VideoCall.status.in_([
                    "ended",
                    "completed",
                ]),
            )
            .first()
        )

        # First completed video call is free
        is_free_call = previous_free_call is None

        # =============================================
        # CHECK CUSTOMER WALLET
        # =============================================

        wallet = get_wallet(
            db,
            customer_id,
        )

        if not wallet:
            raise HTTPException(
                status_code=404,
                detail="Customer wallet not found",
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
                    "call_id": existing_call.video_call_id,
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
        # BROADCAST INCOMING VIDEO CALL
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


# =====================================================
# END VIDEO CALL
# POST /video-calls/{call_id}/end
# =====================================================


@router.post("/{call_id}/end")
async def end_video_call(
    call_id: str,
    db: Session = Depends(get_db),
):

    try:

        # =============================================
        # GET VIDEO CALL WITH LOCK
        # =============================================

        call = get_video_call(
            db,
            call_id,
            lock=True,
        )

        # =============================================
        # CHECK CALL STATUS
        # =============================================

        if call.status not in ["ongoing"]:

            # Already ended: return existing result
            # without deducting wallet or adding earnings again.

            if call.status in ["ended", "completed"]:

                return {
                    "message": "Video call already ended",

                    "call": serialize_call(call),

                    "billing": {
                        "coins_deducted": int(
                            call.coins or 0
                        ),

                        "creator_revenue": float(
                            call.revenue or 0
                        ),
                    },
                }

            raise HTTPException(
                status_code=400,
                detail="Video call is not ongoing",
            )

        # =============================================
        # CHECK START TIME
        # =============================================

        if not call.start_time:

            raise HTTPException(
                status_code=400,
                detail="Call start time not found",
            )

        # =============================================
        # CURRENT TIME
        # =============================================

        now = datetime.now(
            timezone.utc
        )

        start_time = call.start_time

        # Handle timezone-naive database datetime

        if start_time.tzinfo is None:

            start_time = start_time.replace(
                tzinfo=timezone.utc
            )

        # =============================================
        # CALCULATE DURATION
        # =============================================

        duration_seconds = max(
            0,
            int(
                (
                    now - start_time
                ).total_seconds()
            ),
        )

        # =============================================
        # INITIAL BILLING
        # =============================================

        amount = Decimal("0.00")

        coins_to_deduct = 0

        creator_earning_amount = Decimal("0.00")

        # =============================================
        # FREE CALL
        # =============================================

        if call.is_free_call:

            duration_seconds = min(
                duration_seconds,
                FREE_CALL_DURATION_SECONDS,
            )

            amount = Decimal("0.00")

            coins_to_deduct = 0

            creator_earning_amount = Decimal("0.00")

        # =============================================
        # PAID CALL
        # =============================================

        else:

            # =========================================
            # GET CREATOR PRICING
            # =========================================

            pricing = get_creator_pricing(
                db,
                call.creator_id,
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

            # =========================================
            # CALCULATE CALL CHARGE
            # =========================================

            amount, coins_to_deduct = (
                calculate_call_charge(
                    video_price,
                    duration_seconds,
                )
            )

            # =========================================
            # GET CUSTOMER WALLET WITH LOCK
            # =========================================

            wallet = get_wallet(
                db,
                call.customer_id,
                lock=True,
            )

            # =========================================
            # CHECK CUSTOMER BALANCE
            # =========================================

            available_coins = int(
                wallet.coins or 0
            )

            if available_coins < coins_to_deduct:

                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": (
                            "Insufficient balance "
                            "to complete video call"
                        ),

                        "required_coins": (
                            coins_to_deduct
                        ),

                        "available_coins": (
                            available_coins
                        ),
                    },
                )

            # =========================================
            # DEDUCT CUSTOMER WALLET
            # =========================================

            wallet.coins = (
                available_coins
                - coins_to_deduct
            )

            # =========================================
            # UPDATE WALLET LAST TRANSACTION
            # =========================================

            if hasattr(
                wallet,
                "last_transaction",
            ):

                wallet.last_transaction = now

            # =========================================
            # CREATOR EARNING AMOUNT
            # =========================================

            creator_earning_amount = amount

            # =========================================
            # GET CREATOR EARNING RECORD
            # =========================================

            earning = (
                db.query(Earning)
                .filter(
                    Earning.user_id == call.creator_id
                )
                .with_for_update()
                .first()
            )

            # =========================================
            # CREATE EARNING RECORD IF NOT EXISTS
            # =========================================

            if not earning:

                earning = Earning(
                    user_id=call.creator_id,

                    total_earned=Decimal("0.00"),

                    withdrawal_amount=Decimal("0.00"),

                    balance=Decimal("0.00"),
                )

                db.add(earning)

                # Flush so the new record is available
                # before updating its earning values.

                db.flush()

            # =========================================
            # UPDATE CREATOR TOTAL EARNING
            # =========================================

            current_total_earned = Decimal(
                str(
                    earning.total_earned or 0
                )
            )

            earning.total_earned = (
                current_total_earned
                + creator_earning_amount
            )

            # =========================================
            # UPDATE CREATOR AVAILABLE BALANCE
            # =========================================

            current_balance = Decimal(
                str(
                    earning.balance or 0
                )
            )

            earning.balance = (
                current_balance
                + creator_earning_amount
            )

            # =========================================
            # DO NOT MODIFY WITHDRAWAL AMOUNT
            # =========================================

            # earning.withdrawal_amount remains unchanged.

        # =============================================
        # UPDATE VIDEO CALL BILLING
        # =============================================

        call.coins = coins_to_deduct

        call.revenue = amount

        # =============================================
        # SAVE CALL DURATION
        # =============================================

        call.duration = (
            Decimal(
                str(duration_seconds)
            )
            / Decimal("3600")
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        # =============================================
        # SAVE END TIME
        # =============================================

        call.end_time = now

        # =============================================
        # UPDATE CALL STATUS
        # =============================================

        call.status = "completed"

        # =============================================
        # COMMIT ALL DATABASE CHANGES
        # =============================================

        # Wallet deduction, creator earning and call
        # completion are committed together.

        db.commit()

        # =============================================
        # REFRESH VIDEO CALL
        # =============================================

        db.refresh(call)

        # =============================================
        # NOTIFY BOTH PARTICIPANTS
        # =============================================

        notification_sent = False

        try:

            notification_sent = (
                await notify_call_participants(
                    db=db,
                    call=call,
                    event_type="video_call_ended",
                )
            )

        except Exception:

            logger.exception(
                "VIDEO CALL END NOTIFICATION FAILED"
            )

            # The call is already completed and saved.
            # Notification failure should not undo billing.

            notification_sent = False

        # =============================================
        # RESPONSE
        # =============================================

        return {

            "success": True,

            "message": (
                "Video call ended successfully"
            ),

            "notification_sent": (
                notification_sent
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

                "coins_deducted": (
                    coins_to_deduct
                ),

                "creator_revenue": float(
                    amount
                ),

                "creator_earning": float(
                    creator_earning_amount
                ),

                "is_free_call": bool(
                    call.is_free_call
                ),
            },
        }

    # =============================================
    # HTTP ERROR
    # =============================================

    except HTTPException:

        db.rollback()

        raise

    # =============================================
    # DATABASE ERROR
    # =============================================

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

    # =============================================
    # OTHER ERROR
    # =============================================

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
