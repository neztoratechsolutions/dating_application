# from datetime import datetime, timezone, date
# from decimal import Decimal
# from typing import Optional

# from sqlalchemy import func, or_
# from fastapi import (
#     APIRouter,
#     Depends,
#     HTTPException,
#     BackgroundTasks,
#     status,
# )
# from sqlalchemy.orm import Session

# from database import get_db, SessionLocal

# from models.voice_call import VoiceCall
# from models.users import User
# from models.user_status import UserStatus
# from models.wallet import Wallet
# from models.chat_history import Chat
# from routes.websocket_routes import manager


# from schemas.voice_call import (
#      VoiceCallInitiate,
#      VoiceCallCreate,
#      VoiceCallUpdate,
#     VoiceCallResponse,
# )
# router = APIRouter(
#     prefix="/voice-calls",
#     tags=["Voice Calls"]
# )


# # ==========================================================
# # CONSTANTS
# # ==========================================================

# FREE_CALL_DURATION_SECONDS = 2
# PAID_CALL_COINS = 200


# # ==========================================================
# # REAL-TIME CALL DELIVERY
# #
# # Voice-call lifecycle events (ringing / ongoing / rejected /
# # ended) are pushed over the chat WebSocket so the other
# # party is notified instantly. We reuse the chat connection
# # manager because both participants of a call are already
# # connected to the same chat room.
# # ==========================================================

# def get_chat_id_for_users(
#     db: Session,
#     user_a: int,
#     user_b: int,
# ):
#     chat = (
#         db.query(Chat)
#         .filter(
#             or_(
#                 (Chat.user_one_id == user_a)
#                 & (Chat.user_two_id == user_b),
#                 (Chat.user_one_id == user_b)
#                 & (Chat.user_two_id == user_a),
#             )
#         )
#         .first()
#     )

#     return chat.id if chat else None


# async def broadcast_call_event(
#     db: Session,
#     call: VoiceCall,
#     status_override: Optional[str] = None,
# ):
#     chat_id = get_chat_id_for_users(
#         db,
#         call.customer_id,
#         call.creator_id,
#     )

#     if chat_id is None:
#         return

#     await manager.broadcast(
#         chat_id,
#         {
#             "type": "voice_call",
#             "call_id": call.call_id,
#             "caller_id": call.caller_id,
#             "receiver_id": call.receiver_id,
#             "customer_id": call.customer_id,
#             "creator_id": call.creator_id,
#             "status": status_override or call.status,
#             "is_free_call": call.is_free_call,
#             "coins": call.coins,
#             "start_time": (
#                 call.start_time.isoformat()
#                 if call.start_time
#                 else None
#             ),
#         },
#     )


# # ==========================================================
# # GENERATE VOICE CALL ID
# #
# # Example:
# # VOICE-2026-09-16-01
# # VOICE-2026-09-16-02
# # ==========================================================

# def generate_call_id(db: Session):

#     today = datetime.now(timezone.utc).date()

#     date_part = today.strftime("%Y-%m-%d")

#     prefix = f"VOICE-{date_part}-"

#     last_call = (
#         db.query(VoiceCall)
#         .filter(
#             VoiceCall.call_id.like(f"{prefix}%")
#         )
#         .order_by(
#             VoiceCall.id.desc()
#         )
#         .first()
#     )

#     if last_call:

#         try:
#             last_number = int(
#                 last_call.call_id.split("-")[-1]
#             )

#             next_number = last_number + 1

#         except (ValueError, AttributeError):

#             next_number = 1

#     else:

#         next_number = 1

#     return f"{prefix}{next_number:02d}"


# # ==========================================================
# # CHECK USER / CALLER / RECEIVER
# # ==========================================================

# def validate_customer_creator(
#     db: Session,
#     customer_id: int,
#     creator_id: int,
#     caller_id: int,
#     receiver_id: int,
# ):

#     customer = (
#         db.query(User)
#         .filter(
#             User.id == customer_id
#         )
#         .first()
#     )

#     if not customer:

#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Customer not found"
#         )

#     creator = (
#         db.query(User)
#         .filter(
#             User.id == creator_id
#         )
#         .first()
#     )

#     if not creator:

#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Creator not found"
#         )

#     caller = (
#         db.query(User)
#         .filter(
#             User.id == caller_id
#         )
#         .first()
#     )

#     if not caller:

#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Caller not found"
#         )

#     receiver = (
#         db.query(User)
#         .filter(
#             User.id == receiver_id
#         )
#         .first()
#     )

#     if not receiver:

#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Receiver not found"
#         )

#     if customer.role != "customer":

#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Customer ID must belong to a customer"
#         )

#     if creator.role != "creator":

#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Creator ID must belong to a creator"
#         )

#     if caller_id != customer_id:

#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Caller must be the customer"
#         )

#     if receiver_id != creator_id:

#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Receiver must be the creator"
#         )

#     return customer, creator, caller, receiver


# # ==========================================================
# # CHECK WHETHER CUSTOMER ALREADY USED FREE CALL
# # ==========================================================

# def has_used_free_call(
#     db: Session,
#     customer_id: int
# ):

#     free_call = (
#         db.query(VoiceCall)
#         .filter(
#             VoiceCall.customer_id == customer_id,
#             VoiceCall.is_free_call.is_(True)
#         )
#         .first()
#     )

#     return free_call is not None


# # ==========================================================
# # GET CUSTOMER WALLET
# # ==========================================================

# def get_customer_wallet(
#     db: Session,
#     customer_id: int
# ):

#     wallet = (
#         db.query(Wallet)
#         .filter(
#             Wallet.user_id == customer_id
#         )
#         .with_for_update()
#         .first()
#     )

#     if not wallet:

#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Customer wallet not found"
#         )

#     return wallet


# # ==========================================================
# # AUTO END FIRST FREE CALL AFTER 2 SECONDS
# # ==========================================================

# async def auto_end_free_call(call_id: str):

#     import asyncio

#     await asyncio.sleep(
#         FREE_CALL_DURATION_SECONDS
#     )

#     db = SessionLocal()

#     try:

#         call = (
#             db.query(VoiceCall)
#             .filter(
#                 VoiceCall.call_id == call_id
#             )
#             .first()
#         )

#         if not call:
#             return

#         # Only end if call is still ongoing
#         if call.status != "ongoing":
#             return

#         if not call.start_time:
#             return

#         end_time = datetime.now(
#             timezone.utc
#         )

#         start_time = call.start_time

#         if start_time.tzinfo is None:

#             start_time = start_time.replace(
#                 tzinfo=timezone.utc
#             )

#         duration_seconds = (
#             end_time - start_time
#         ).total_seconds()

#         # Maximum free call = 2 seconds
#         duration_seconds = min(
#             duration_seconds,
#             FREE_CALL_DURATION_SECONDS
#         )

#         duration_hours = round(
#             duration_seconds / 3600,
#             2
#         )

#         call.end_time = end_time

#         call.duration = Decimal(
#             str(duration_hours)
#         )

#         call.status = "ended"

#         db.commit()

#         db.refresh(call)

#         # Notify both parties that the free call ended.
#         await broadcast_call_event(
#             db,
#             call,
#             status_override="ended"
#         )

#     except Exception:

#         db.rollback()

#     finally:

#         db.close()


# # ==========================================================
# # INITIATE VOICE CALL
# #
# # Either participant may initiate: a customer calling a
# # creator, or a creator calling a customer. The customer is
# # always the payer (free first call, then 200 coins).
# # ==========================================================

# @router.post(
#     "/initiate",
#     response_model=VoiceCallResponse,
#     status_code=status.HTTP_201_CREATED
# )
# async def initiate_voice_call(
#     data: VoiceCallInitiate,
#     background_tasks: BackgroundTasks,
#     db: Session = Depends(get_db)
# ):

#     # ------------------------------------------------------
#     # GET CALLER
#     # ------------------------------------------------------

#     caller = (
#         db.query(User)
#         .filter(
#             User.id == data.caller_id
#         )
#         .first()
#     )

#     if not caller:

#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Caller not found"
#         )

#     # ------------------------------------------------------
#     # GET RECEIVER
#     # ------------------------------------------------------

#     receiver = (
#         db.query(User)
#         .filter(
#             User.id == data.receiver_id
#         )
#         .first()
#     )

#     if not receiver:

#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Receiver not found"
#         )

#     # ------------------------------------------------------
#     # CALLER AND RECEIVER MUST BE ONE CUSTOMER + ONE CREATOR
#     # (either may initiate the call).
#     # ------------------------------------------------------

#     if caller.role == "customer" and receiver.role == "creator":
#         customer_id = caller.id
#         creator_id = receiver.id
#     elif caller.role == "creator" and receiver.role == "customer":
#         customer_id = receiver.id
#         creator_id = caller.id
#     else:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Voice call must be between a customer and a creator"
#         )

#     # ------------------------------------------------------
#     # CHECK ACTIVE CALL
#     # ------------------------------------------------------

#     active_call = (
#         db.query(VoiceCall)
#         .filter(
#             VoiceCall.status.in_(
#                 ["ringing", "ongoing"]
#             )
#         )
#         .filter(
#             (
#                 (VoiceCall.caller_id == data.caller_id)
#                 &
#                 (VoiceCall.receiver_id == data.receiver_id)
#             )
#             |
#             (
#                 (VoiceCall.caller_id == data.receiver_id)
#                 &
#                 (VoiceCall.receiver_id == data.caller_id)
#             )
#         )
#         .first()
#     )

#     if active_call:

#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="An active call already exists between these users"
#         )

#     # ------------------------------------------------------
#     # CHECK FIRST FREE CALL
#     #
#     # Free-call eligibility is tracked against the customer,
#     # regardless of who initiates the call.
#     # ------------------------------------------------------

#     free_call_already_used = has_used_free_call(
#         db,
#         customer_id
#     )

#     is_free_call = not free_call_already_used

#     # ------------------------------------------------------
#     # FOR PAID CALL
#     #
#     # We only CHECK wallet here.
#     # Actual deduction happens when accepted.
#     # ------------------------------------------------------

#     if not is_free_call:

#         wallet = (
#             db.query(Wallet)
#             .filter(
#                 Wallet.user_id == customer_id
#             )
#             .first()
#         )

#         if not wallet:

#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Customer wallet not found"
#             )

#         if wallet.coins < PAID_CALL_COINS:

#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="You need at least 200 coins to make a call"
#             )

#     # ------------------------------------------------------
#     # GENERATE CALL ID
#     # ------------------------------------------------------

#     call_id = generate_call_id(db)

#     # ------------------------------------------------------
#     # CREATE CALL
#     # ------------------------------------------------------

#     new_call = VoiceCall(

#         call_id=call_id,

#         customer_id=customer_id,

#         creator_id=creator_id,

#         caller_id=data.caller_id,

#         receiver_id=data.receiver_id,

#         start_time=None,

#         end_time=None,

#         duration=Decimal("0.00"),

#         coins=0,

#         revenue=Decimal("0.00"),

#         status="ringing",

#         is_free_call=is_free_call
#     )

#     db.add(new_call)

#     db.commit()

#     db.refresh(new_call)

#     # ------------------------------------------------------
#     # NOTIFY THE OTHER PARTY IN REAL TIME
#     # ------------------------------------------------------

#     await broadcast_call_event(
#         db,
#         new_call,
#         status_override="ringing"
#     )

#     return new_call


# # ==========================================================
# # CREATE VOICE CALL
# # ==========================================================

# @router.post(
#     "/",
#     response_model=VoiceCallResponse,
#     status_code=status.HTTP_201_CREATED
# )
# def create_voice_call(
#     data: VoiceCallCreate,
#     db: Session = Depends(get_db)
# ):

#     customer, creator, caller, receiver = (
#         validate_customer_creator(
#             db=db,
#             customer_id=data.customer_id,
#             creator_id=data.creator_id,
#             caller_id=data.caller_id,
#             receiver_id=data.receiver_id
#         )
#     )

#     # ------------------------------------------------------
#     # CHECK PREVIOUS FREE CALL
#     # ------------------------------------------------------

#     free_call_already_used = has_used_free_call(
#         db,
#         data.customer_id
#     )

#     is_free_call = not free_call_already_used

#     # ------------------------------------------------------
#     # PAID CALL WALLET CHECK
#     # ------------------------------------------------------

#     if not is_free_call:

#         wallet = (
#             db.query(Wallet)
#             .filter(
#                 Wallet.user_id == data.customer_id
#             )
#             .first()
#         )

#         if not wallet:

#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Customer wallet not found"
#             )

#         if wallet.coins < PAID_CALL_COINS:

#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="You need at least 200 coins to make a call"
#             )

#     # ------------------------------------------------------
#     # CREATE
#     # ------------------------------------------------------

#     new_call = VoiceCall(

#         call_id=generate_call_id(db),

#         customer_id=data.customer_id,

#         creator_id=data.creator_id,

#         caller_id=data.caller_id,

#         receiver_id=data.receiver_id,

#         start_time=data.start_time,

#         end_time=data.end_time,

#         duration=data.duration,

#         coins=0,

#         revenue=data.revenue,

#         status=data.status,

#         is_free_call=is_free_call
#     )

#     db.add(new_call)

#     db.commit()

#     db.refresh(new_call)

#     return new_call


# # ==========================================================
# # GET ALL VOICE CALLS
# # ==========================================================

# @router.get(
#     "/",
#     response_model=list[VoiceCallResponse]
# )
# def get_all_voice_calls(

#     call_date: Optional[date] = None,

#     start_date: Optional[date] = None,

#     end_date: Optional[date] = None,

#     customer_id: Optional[int] = None,

#     creator_id: Optional[int] = None,

#     caller_id: Optional[int] = None,

#     receiver_id: Optional[int] = None,

#     call_status: Optional[str] = None,

#     db: Session = Depends(get_db)
# ):

#     query = db.query(VoiceCall)

#     # ------------------------------------------------------
#     # CALL DATE
#     # ------------------------------------------------------

#     if call_date:

#         query = query.filter(
#             func.date(
#                 VoiceCall.created_at
#             ) == call_date
#         )

#     # ------------------------------------------------------
#     # START DATE
#     # ------------------------------------------------------

#     if start_date:

#         query = query.filter(
#             func.date(
#                 VoiceCall.created_at
#             ) >= start_date
#         )

#     # ------------------------------------------------------
#     # END DATE
#     # ------------------------------------------------------

#     if end_date:

#         query = query.filter(
#             func.date(
#                 VoiceCall.created_at
#             ) <= end_date
#         )

#     # ------------------------------------------------------
#     # CUSTOMER
#     # ------------------------------------------------------

#     if customer_id:

#         query = query.filter(
#             VoiceCall.customer_id == customer_id
#         )

#     # ------------------------------------------------------
#     # CREATOR
#     # ------------------------------------------------------

#     if creator_id:

#         query = query.filter(
#             VoiceCall.creator_id == creator_id
#         )

#     # ------------------------------------------------------
#     # CALLER
#     # ------------------------------------------------------

#     if caller_id:

#         query = query.filter(
#             VoiceCall.caller_id == caller_id
#         )

#     # ------------------------------------------------------
#     # RECEIVER
#     # ------------------------------------------------------

#     if receiver_id:

#         query = query.filter(
#             VoiceCall.receiver_id == receiver_id
#         )

#     # ------------------------------------------------------
#     # STATUS
#     # ------------------------------------------------------

#     if call_status:

#         query = query.filter(
#             VoiceCall.status == call_status
#         )

#     calls = (
#         query
#         .order_by(
#             VoiceCall.id.desc()
#         )
#         .all()
#     )

#     if not calls:

#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="No voice calls found"
#         )

#     return calls


# # ==========================================================
# # ACCEPT VOICE CALL
# # ==========================================================

# @router.post(
#     "/{call_id}/accept",
#     response_model=VoiceCallResponse
# )
# async def accept_voice_call(
#     call_id: str,
#     background_tasks: BackgroundTasks,
#     db: Session = Depends(get_db)
# ):

#     # ------------------------------------------------------
#     # GET CALL
#     # ------------------------------------------------------

#     call = (
#         db.query(VoiceCall)
#         .filter(
#             VoiceCall.call_id == call_id
#         )
#         .first()
#     )

#     if not call:

#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Voice call not found"
#         )

#     # ------------------------------------------------------
#     # CALL MUST BE RINGING
#     # ------------------------------------------------------

#     if call.status != "ringing":

#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Only ringing calls can be accepted"
#         )

#     # ======================================================
#     # FREE CALL
#     # ======================================================

#     if call.is_free_call:

#         # First free call
#         call.coins = 0

#     # ======================================================
#     # PAID CALL
#     # ======================================================

#     else:

#         # --------------------------------------------------
#         # GET WALLET
#         # --------------------------------------------------

#         wallet = (
#             db.query(Wallet)
#             .filter(
#                 Wallet.user_id == call.customer_id
#             )
#             .with_for_update()
#             .first()
#         )

#         if not wallet:

#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Customer wallet not found"
#             )

#         # --------------------------------------------------
#         # CHECK COINS
#         # --------------------------------------------------

#         if wallet.coins < PAID_CALL_COINS:

#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="You need at least 200 coins to make a call"
#             )

#         # --------------------------------------------------
#         # DEDUCT 200 COINS
#         # --------------------------------------------------

#         wallet.coins = (
#             wallet.coins - PAID_CALL_COINS
#         )

#         # --------------------------------------------------
#         # UPDATE WALLET TRANSACTION INFO
#         # --------------------------------------------------

#         wallet.spending = (
#             wallet.spending or Decimal("0.00")
#         )

#         wallet.last_transaction = (
#             datetime.now(timezone.utc)
#         )

#         # --------------------------------------------------
#         # STORE CHARGED COINS IN VOICE CALL
#         # --------------------------------------------------

#         call.coins = PAID_CALL_COINS

#     # ======================================================
#     # START CALL
#     # ======================================================

#     start_time = datetime.now(
#         timezone.utc
#     )

#     call.start_time = start_time

#     call.status = "ongoing"

#     db.commit()

#     db.refresh(call)

#     # ======================================================
#     # FREE CALL AUTO CUT
#     # ======================================================

#     if call.is_free_call:

#         background_tasks.add_task(
#             auto_end_free_call,
#             call.call_id
#         )

#     # ======================================================
#     # NOTIFY CALLER THAT THE CALL WAS ACCEPTED
#     # ======================================================

#     await broadcast_call_event(
#         db,
#         call,
#         status_override="ongoing"
#     )

#     return call


# # ==========================================================
# # REJECT VOICE CALL
# # ==========================================================

# @router.post(
#     "/{call_id}/reject",
#     response_model=VoiceCallResponse
# )
# async def reject_voice_call(
#     call_id: str,
#     db: Session = Depends(get_db)
# ):

#     call = (
#         db.query(VoiceCall)
#         .filter(
#             VoiceCall.call_id == call_id
#         )
#         .first()
#     )

#     if not call:

#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Voice call not found"
#         )

#     if call.status != "ringing":

#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Only ringing calls can be rejected"
#         )

#     call.status = "rejected"

#     call.end_time = datetime.now(
#         timezone.utc
#     )

#     call.duration = Decimal("0.00")

#     db.commit()

#     db.refresh(call)

#     # Notify the caller that the call was declined.
#     await broadcast_call_event(
#         db,
#         call,
#         status_override="rejected"
#     )

#     return call


# # ==========================================================
# # END VOICE CALL
# # ==========================================================

# @router.post(
#     "/{call_id}/end",
#     response_model=VoiceCallResponse
# )
# async def end_voice_call(
#     call_id: str,
#     db: Session = Depends(get_db)
# ):

#     call = (
#         db.query(VoiceCall)
#         .filter(
#             VoiceCall.call_id == call_id
#         )
#         .first()
#     )

#     if not call:

#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Voice call not found"
#         )

#     if call.status != "ongoing":

#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Only ongoing calls can be ended"
#         )

#     if not call.start_time:

#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Call start time not found"
#         )

#     end_time = datetime.now(
#         timezone.utc
#     )

#     start_time = call.start_time

#     if start_time.tzinfo is None:

#         start_time = start_time.replace(
#             tzinfo=timezone.utc
#         )

#     duration_seconds = (
#         end_time - start_time
#     ).total_seconds()

#     # ------------------------------------------------------
#     # FREE CALL MAXIMUM = 2 SECONDS
#     # ------------------------------------------------------

#     if call.is_free_call:

#         duration_seconds = min(
#             duration_seconds,
#             FREE_CALL_DURATION_SECONDS
#         )

#     duration_hours = round(
#         duration_seconds / 3600,
#         2
#     )

#     call.end_time = end_time

#     call.duration = Decimal(
#         str(duration_hours)
#     )

#     call.status = "ended"

#     db.commit()

#     db.refresh(call)

#     # Notify both parties that the call ended.
#     await broadcast_call_event(
#         db,
#         call,
#         status_override="ended"
#     )

#     return call


# # ==========================================================
# # GET SINGLE VOICE CALL
# # ==========================================================

# @router.get(
#     "/{call_id}",
#     response_model=VoiceCallResponse
# )
# def get_voice_call(
#     call_id: str,
#     db: Session = Depends(get_db)
# ):

#     call = (
#         db.query(VoiceCall)
#         .filter(
#             VoiceCall.call_id == call_id
#         )
#         .first()
#     )

#     if not call:

#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Voice call not found"
#         )

#     return call


# # ==========================================================
# # UPDATE VOICE CALL
# # ==========================================================

# @router.put(
#     "/{call_id}",
#     response_model=VoiceCallResponse
# )
# def update_voice_call(
#     call_id: str,
#     data: VoiceCallUpdate,
#     db: Session = Depends(get_db)
# ):

#     call = (
#         db.query(VoiceCall)
#         .filter(
#             VoiceCall.call_id == call_id
#         )
#         .first()
#     )

#     if not call:

#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Voice call not found"
#         )

#     update_data = data.model_dump(
#         exclude_unset=True
#     )

#     for key, value in update_data.items():

#         setattr(
#             call,
#             key,
#             value
#         )

#     db.commit()

#     db.refresh(call)

#     return call


# # ==========================================================
# # DELETE VOICE CALL
# # ==========================================================

# @router.delete(
#     "/{call_id}"
# )
# def delete_voice_call(
#     call_id: str,
#     db: Session = Depends(get_db)
# ):

#     call = (
#         db.query(VoiceCall)
#         .filter(
#             VoiceCall.call_id == call_id
#         )
#         .first()
#     )

#     if not call:

#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Voice call not found"
#         )

#     db.delete(call)

#     db.commit()

#     return {
#         "status": 200,
#         "message": "Voice call deleted successfully"
#     }
# Updated `routes/voice_call.py`

from datetime import datetime, timezone, date
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from typing import Optional
import uuid
import asyncio
import logging

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    BackgroundTasks,
    status,
)

from database import get_db, SessionLocal

from models.voice_call import VoiceCall
from models.users import User
from models.wallet import Wallet
from models.wallet_transaction import WalletTransaction
from models.earnings import Earning
from models.pricing_details import PricingDetail
from models.chat_history import Chat

from routes.websocket_routes import manager

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

logger = logging.getLogger(__name__)


# ==========================================================
# CONSTANTS
# ==========================================================

FREE_CALL_DURATION_SECONDS = 2

# Assumption: 1 rupee = 1 coin
COINS_PER_RUPEE = Decimal("1")

# ==========================================================
# HELPERS
# ==========================================================


def utc_now():
    return datetime.now(timezone.utc)


def generate_transaction_id():
    return f"VTX-{uuid.uuid4().hex[:20].upper()}"


def generate_call_id(db: Session):

    today = utc_now().date()

    prefix = f"VOICE-{today.strftime('%Y-%m-%d')}-"

    last_call = (
        db.query(VoiceCall)
        .filter(
            VoiceCall.call_id.like(f"{prefix}%")
        )
        .order_by(VoiceCall.id.desc())
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
# GET CUSTOMER / CREATOR
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
        .filter(User.id == customer_id)
        .first()
    )

    if not customer:

        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    creator = (
        db.query(User)
        .filter(User.id == creator_id)
        .first()
    )

    if not creator:

        raise HTTPException(
            status_code=404,
            detail="Creator not found"
        )

    caller = (
        db.query(User)
        .filter(User.id == caller_id)
        .first()
    )

    if not caller:

        raise HTTPException(
            status_code=404,
            detail="Caller not found"
        )

    receiver = (
        db.query(User)
        .filter(User.id == receiver_id)
        .first()
    )

    if not receiver:

        raise HTTPException(
            status_code=404,
            detail="Receiver not found"
        )

    if customer.role != "customer":

        raise HTTPException(
            status_code=400,
            detail="Customer ID must belong to a customer"
        )

    if creator.role != "creator":

        raise HTTPException(
            status_code=400,
            detail="Creator ID must belong to a creator"
        )

    if caller_id != customer_id:

        raise HTTPException(
            status_code=400,
            detail="Caller must be the customer"
        )

    if receiver_id != creator_id:

        raise HTTPException(
            status_code=400,
            detail="Receiver must be the creator"
        )

    return customer, creator, caller, receiver


# ==========================================================
# GET CREATOR VOICE PRICE
# ==========================================================


def get_creator_voice_price(
    db: Session,
    creator_id: int
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
            detail="Creator pricing details not found"
        )

    if pricing.voice_call_amount is None:

        raise HTTPException(
            status_code=400,
            detail="Creator voice call price not configured"
        )

    price = Decimal(
        str(pricing.voice_call_amount)
    )

    if price <= 0:

        raise HTTPException(
            status_code=400,
            detail="Creator voice call price must be greater than zero"
        )

    return price


# ==========================================================
# CALCULATE CALL CHARGE
#
# Example:
# Creator price = 30 rupees/minute
# Duration = 60 seconds
# Amount = 30 rupees
# Coins = 30
#
# Partial minutes are charged proportionally.
# ==========================================================


def calculate_voice_call_charge(
    price_per_minute: Decimal,
    duration_seconds: float
):

    price_per_minute = Decimal(
        str(price_per_minute)
    )

    duration_seconds = Decimal(
        str(max(duration_seconds, 0))
    )

    amount = (
        price_per_minute
        * duration_seconds
        / Decimal("60")
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    coins = int(
        (
            amount * COINS_PER_RUPEE
        ).to_integral_value(
            rounding=ROUND_CEILING
        )
    )

    return amount, coins


# ==========================================================
# CHECK FREE CALL
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
    customer_id: int,
    lock: bool = False
):

    query = (
        db.query(Wallet)
        .filter(
            Wallet.user_id == customer_id
        )
    )

    if lock:

        query = query.with_for_update()

    wallet = query.first()

    if not wallet:

        raise HTTPException(
            status_code=404,
            detail="Customer wallet not found"
        )

    if wallet.status != "active":

        raise HTTPException(
            status_code=400,
            detail="Customer wallet is not active"
        )

    return wallet


# ==========================================================
# GET CREATOR EARNING
# ==========================================================


def get_creator_earning(
    db: Session,
    creator_id: int
):

    earning = (
        db.query(Earning)
        .filter(
            Earning.user_id == creator_id
        )
        .with_for_update()
        .first()
    )

    if not earning:

        earning = Earning(
            user_id=creator_id,
            total_earned=Decimal("0.00"),
            withdrawal_amount=Decimal("0.00"),
            balance=Decimal("0.00")
        )

        db.add(earning)

        db.flush()

    return earning


# ==========================================================
# GET CHAT ID
# ==========================================================


def get_chat_id_for_users(
    db: Session,
    user_a: int,
    user_b: int
):

    chat = (
        db.query(Chat)
        .filter(
            or_(
                (
                    Chat.user_one_id == user_a
                )
                &
                (
                    Chat.user_two_id == user_b
                ),
                (
                    Chat.user_one_id == user_b
                )
                &
                (
                    Chat.user_two_id == user_a
                )
            )
        )
        .first()
    )

    return chat.id if chat else None


# ==========================================================
# BROADCAST CALL EVENT
# ==========================================================


async def broadcast_call_event(
    db: Session,
    call: VoiceCall,
    status_override: Optional[str] = None
):

    chat_id = get_chat_id_for_users(
        db,
        call.customer_id,
        call.creator_id
    )

    if chat_id is None:

        logger.warning(
            "No chat found for voice call %s",
            call.call_id
        )

        return

    payload = {

        "type": "voice_call",

        "call_id": call.call_id,

        "caller_id": call.caller_id,

        "receiver_id": call.receiver_id,

        "customer_id": call.customer_id,

        "creator_id": call.creator_id,

        "status": status_override or call.status,

        "is_free_call": call.is_free_call,

        "coins": call.coins,

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

        "duration": (
            float(call.duration)
            if call.duration is not None
            else 0
        ),
    }

    await manager.broadcast(
        chat_id,
        payload
    )


# ==========================================================
# GET CALL DURATION
# ==========================================================


def get_call_duration_seconds(
    call: VoiceCall,
    end_time: datetime
):

    if not call.start_time:

        raise HTTPException(
            status_code=400,
            detail="Call start time not found"
        )

    start_time = call.start_time

    if start_time.tzinfo is None:

        start_time = start_time.replace(
            tzinfo=timezone.utc
        )

    if end_time.tzinfo is None:

        end_time = end_time.replace(
            tzinfo=timezone.utc
        )

    duration_seconds = (
        end_time - start_time
    ).total_seconds()

    duration_seconds = max(
        duration_seconds,
        0
    )

    if call.is_free_call:

        duration_seconds = min(
            duration_seconds,
            FREE_CALL_DURATION_SECONDS
        )

    return duration_seconds


# ==========================================================
# FREE CALL AUTO END
# ==========================================================


async def auto_end_free_call(
    call_id: str
):

    await asyncio.sleep(
        FREE_CALL_DURATION_SECONDS
    )

    db = SessionLocal()

    try:

        call = (
            db.query(VoiceCall)
            .filter(
                VoiceCall.call_id == call_id
            )
            .with_for_update()
            .first()
        )

        if not call:

            return

        if call.status != "ongoing":

            return

        end_time = utc_now()

        duration_seconds = get_call_duration_seconds(
            call,
            end_time
        )

        duration_hours = (
            Decimal(str(duration_seconds))
            / Decimal("3600")
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        call.end_time = end_time

        call.duration = duration_hours

        call.coins = 0

        call.revenue = Decimal("0.00")

        call.status = "ended"

        db.commit()

        db.refresh(call)

        await broadcast_call_event(
            db,
            call,
            status_override="ended"
        )

    except Exception:

        logger.exception(
            "Failed to auto-end free voice call %s",
            call_id
        )

        db.rollback()

    finally:

        db.close()


# ==========================================================
# INITIATE VOICE CALL
#
# Customer or Creator can initiate.
# Customer is always the payer.
# ==========================================================


@router.post(
    "/initiate",
    response_model=VoiceCallResponse,
    status_code=status.HTTP_201_CREATED
)
async def initiate_voice_call(
    data: VoiceCallInitiate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):

    caller = (
        db.query(User)
        .filter(
            User.id == data.caller_id
        )
        .first()
    )

    if not caller:

        raise HTTPException(
            status_code=404,
            detail="Caller not found"
        )

    receiver = (
        db.query(User)
        .filter(
            User.id == data.receiver_id
        )
        .first()
    )

    if not receiver:

        raise HTTPException(
            status_code=404,
            detail="Receiver not found"
        )

    # Customer calling Creator
    if (
        caller.role == "customer"
        and receiver.role == "creator"
    ):

        customer_id = caller.id

        creator_id = receiver.id

    # Creator calling Customer
    elif (
        caller.role == "creator"
        and receiver.role == "customer"
    ):

        customer_id = receiver.id

        creator_id = caller.id

    else:

        raise HTTPException(
            status_code=400,
            detail="Voice call must be between a customer and a creator"
        )

    # ------------------------------------------------------
    # CHECK ACTIVE CALL BETWEEN THESE USERS
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
                (
                    VoiceCall.customer_id
                    == customer_id
                )
                &
                (
                    VoiceCall.creator_id
                    == creator_id
                )
            )
        )
        .first()
    )

    if active_call:

        raise HTTPException(
            status_code=400,
            detail="An active call already exists between these users"
        )

    # ------------------------------------------------------
    # FREE CALL CHECK
    # ------------------------------------------------------

    is_free_call = not has_used_free_call(
        db,
        customer_id
    )

    # ------------------------------------------------------
    # GET CREATOR PRICE
    # ------------------------------------------------------

    creator_price = get_creator_voice_price(
        db,
        creator_id
    )

    # ------------------------------------------------------
    # CHECK WALLET FOR PAID CALL
    #
    # No deduction at initiation.
    # Actual deduction happens when the call ends.
    # ------------------------------------------------------

    if not is_free_call:

        wallet = get_customer_wallet(
            db,
            customer_id
        )

        amount, coins = calculate_voice_call_charge(
            creator_price,
            60
        )

        if wallet.coins < coins:

            raise HTTPException(
                status_code=400,
                detail=(
                    f"You need at least {coins} coins "
                    "for one minute of this creator's voice call"
                )
            )

    # ------------------------------------------------------
    # CREATE CALL
    # ------------------------------------------------------

    new_call = VoiceCall(

        call_id=generate_call_id(db),

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

    # ------------------------------------------------------
    # NOTIFY BOTH PARTIES
    # ------------------------------------------------------

    await broadcast_call_event(
        db,
        new_call,
        status_override="ringing"
    )

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

    (
        customer,
        creator,
        caller,
        receiver
    ) = validate_customer_creator(
        db=db,
        customer_id=data.customer_id,
        creator_id=data.creator_id,
        caller_id=data.caller_id,
        receiver_id=data.receiver_id
    )

    is_free_call = not has_used_free_call(
        db,
        data.customer_id
    )

    creator_price = get_creator_voice_price(
        db,
        data.creator_id
    )

    if not is_free_call:

        wallet = get_customer_wallet(
            db,
            data.customer_id
        )

        amount, coins = calculate_voice_call_charge(
            creator_price,
            60
        )

        if wallet.coins < coins:

            raise HTTPException(
                status_code=400,
                detail=(
                    f"You need at least {coins} coins "
                    "for one minute of this creator's voice call"
                )
            )

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

        revenue=Decimal("0.00"),

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

    if call_date:

        query = query.filter(
            func.date(
                VoiceCall.created_at
            ) == call_date
        )

    if start_date:

        query = query.filter(
            func.date(
                VoiceCall.created_at
            ) >= start_date
        )

    if end_date:

        query = query.filter(
            func.date(
                VoiceCall.created_at
            ) <= end_date
        )

    if customer_id:

        query = query.filter(
            VoiceCall.customer_id == customer_id
        )

    if creator_id:

        query = query.filter(
            VoiceCall.creator_id == creator_id
        )

    if caller_id:

        query = query.filter(
            VoiceCall.caller_id == caller_id
        )

    if receiver_id:

        query = query.filter(
            VoiceCall.receiver_id == receiver_id
        )

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
            status_code=404,
            detail="No voice calls found"
        )

    return calls


# ==========================================================
# ACCEPT VOICE CALL
#
# No wallet deduction here.
# Charge is based on actual duration at call end.
# ==========================================================


@router.post(
    "/{call_id}/accept",
    response_model=VoiceCallResponse
)
async def accept_voice_call(
    call_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):

    call = (
        db.query(VoiceCall)
        .filter(
            VoiceCall.call_id == call_id
        )
        .with_for_update()
        .first()
    )

    if not call:

        raise HTTPException(
            status_code=404,
            detail="Voice call not found"
        )

    if call.status != "ringing":

        raise HTTPException(
            status_code=400,
            detail="Only ringing calls can be accepted"
        )

    # ------------------------------------------------------
    # CHECK CUSTOMER WALLET FOR PAID CALL
    # ------------------------------------------------------

    if not call.is_free_call:

        creator_price = get_creator_voice_price(
            db,
            call.creator_id
        )

        wallet = get_customer_wallet(
            db,
            call.customer_id
        )

        amount, coins = calculate_voice_call_charge(
            creator_price,
            60
        )

        if wallet.coins < coins:

            call.status = "rejected"

            call.end_time = utc_now()

            db.commit()

            db.refresh(call)

            await broadcast_call_event(
                db,
                call,
                status_override="rejected"
            )

            raise HTTPException(
                status_code=400,
                detail=(
                    f"You need at least {coins} coins "
                    "for one minute of this creator's voice call"
                )
            )

    # ------------------------------------------------------
    # START CALL
    # ------------------------------------------------------

    call.start_time = utc_now()

    call.end_time = None

    call.status = "ongoing"

    call.coins = 0

    call.revenue = Decimal("0.00")

    db.commit()

    db.refresh(call)

    # ------------------------------------------------------
    # FREE CALL AUTO END
    # ------------------------------------------------------

    if call.is_free_call:

        background_tasks.add_task(
            auto_end_free_call,
            call.call_id
        )

    # ------------------------------------------------------
    # NOTIFY BOTH PARTIES
    # ------------------------------------------------------

    await broadcast_call_event(
        db,
        call,
        status_override="ongoing"
    )

    return call


# ==========================================================
# REJECT VOICE CALL
# ==========================================================


@router.post(
    "/{call_id}/reject",
    response_model=VoiceCallResponse
)
async def reject_voice_call(
    call_id: str,
    db: Session = Depends(get_db)
):

    call = (
        db.query(VoiceCall)
        .filter(
            VoiceCall.call_id == call_id
        )
        .with_for_update()
        .first()
    )

    if not call:

        raise HTTPException(
            status_code=404,
            detail="Voice call not found"
        )

    if call.status != "ringing":

        raise HTTPException(
            status_code=400,
            detail="Only ringing calls can be rejected"
        )

    call.status = "rejected"

    call.end_time = utc_now()

    call.duration = Decimal("0.00")

    call.coins = 0

    call.revenue = Decimal("0.00")

    db.commit()

    db.refresh(call)

    await broadcast_call_event(
        db,
        call,
        status_override="rejected"
    )

    return call


# ==========================================================
# END VOICE CALL
#
# PAID:
#   1. Calculate duration.
#   2. Fetch Creator price.
#   3. Calculate amount and coins.
#   4. Deduct customer wallet.
#   5. Create wallet transaction.
#   6. Update Creator earnings.
#   7. Update call record.
#
# FREE:
#   No wallet transaction.
#   No Creator earnings.
# ==========================================================


@router.post(
    "/{call_id}/end",
    response_model=VoiceCallResponse
)
async def end_voice_call(
    call_id: str,
    db: Session = Depends(get_db)
):

    try:

        # --------------------------------------------------
        # LOCK CALL
        # --------------------------------------------------

        call = (
            db.query(VoiceCall)
            .filter(
                VoiceCall.call_id == call_id
            )
            .with_for_update()
            .first()
        )

        if not call:

            raise HTTPException(
                status_code=404,
                detail="Voice call not found"
            )

        if call.status != "ongoing":

            raise HTTPException(
                status_code=400,
                detail="Only ongoing calls can be ended"
            )

        end_time = utc_now()

        duration_seconds = get_call_duration_seconds(
            call,
            end_time
        )

        # --------------------------------------------------
        # DURATION IN HOURS
        #
        # VoiceCall.duration is stored as decimal hours
        # in the existing model.
        # --------------------------------------------------

        duration_hours = (
            Decimal(str(duration_seconds))
            / Decimal("3600")
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        call.end_time = end_time

        call.duration = duration_hours

        # --------------------------------------------------
        # FREE CALL
        # --------------------------------------------------

        if call.is_free_call:

            call.coins = 0

            call.revenue = Decimal("0.00")

            call.status = "ended"

            db.commit()

            db.refresh(call)

            await broadcast_call_event(
                db,
                call,
                status_override="ended"
            )

            return call

        # --------------------------------------------------
        # GET CREATOR PRICE
        # --------------------------------------------------

        creator_price = get_creator_voice_price(
            db,
            call.creator_id
        )

        # --------------------------------------------------
        # CALCULATE ACTUAL CALL AMOUNT
        # --------------------------------------------------

        amount, coins_to_deduct = (
            calculate_voice_call_charge(
                creator_price,
                duration_seconds
            )
        )

        # --------------------------------------------------
        # LOCK CUSTOMER WALLET
        # --------------------------------------------------

        wallet = get_customer_wallet(
            db,
            call.customer_id,
            lock=True
        )

        # --------------------------------------------------
        # CHECK CUSTOMER BALANCE
        # --------------------------------------------------

        if wallet.coins < coins_to_deduct:

            raise HTTPException(
                status_code=400,
                detail=(
                    f"Insufficient wallet coins. "
                    f"Required: {coins_to_deduct}, "
                    f"Available: {wallet.coins}"
                )
            )

        # --------------------------------------------------
        # UPDATE CUSTOMER WALLET
        # --------------------------------------------------

        wallet.coins = (
            wallet.coins - coins_to_deduct
        )

        wallet.spending = (
            Decimal(str(wallet.spending or 0))
            + amount
        )

        wallet.balance = (
            Decimal(str(wallet.balance or 0))
            - amount
        )

        wallet.last_transaction = end_time

        # --------------------------------------------------
        # CREATE WALLET TRANSACTION
        # --------------------------------------------------

        wallet_transaction = WalletTransaction(

            transaction_id=generate_transaction_id(),

            user_id=call.customer_id,

            wallet_id=wallet.id,

            type="voice_call",

            amount=amount,

            coins=coins_to_deduct,

            method="wallet",

            status="completed"
        )

        db.add(wallet_transaction)

        # --------------------------------------------------
        # UPDATE CREATOR EARNING
        # --------------------------------------------------

        creator_earning = get_creator_earning(
            db,
            call.creator_id
        )

        creator_earning.total_earned = (
            Decimal(
                str(
                    creator_earning.total_earned or 0
                )
            )
            + amount
        )

        creator_earning.balance = (
            Decimal(
                str(
                    creator_earning.balance or 0
                )
            )
            + amount
        )

        # --------------------------------------------------
        # UPDATE VOICE CALL
        # --------------------------------------------------

        call.coins = coins_to_deduct

        call.revenue = amount

        call.status = "ended"

        # --------------------------------------------------
        # COMMIT ALL BILLING CHANGES TOGETHER
        # --------------------------------------------------

        db.commit()

        db.refresh(call)

        # --------------------------------------------------
        # NOTIFY BOTH USERS
        # --------------------------------------------------

        await broadcast_call_event(
            db,
            call,
            status_override="ended"
        )

        return call

    except HTTPException:

        db.rollback()

        raise

    except Exception:

        db.rollback()

        logger.exception(
            "Failed to end and bill voice call %s",
            call_id
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to complete voice call billing"
        )


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
            status_code=404,
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
            status_code=404,
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
            status_code=404,
            detail="Voice call not found"
        )

    db.delete(call)

    db.commit()

    return {
        "status": 200,
        "message": "Voice call deleted successfully"
    }

