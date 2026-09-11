# ==========================================================
# VOICE CALL ROUTES
# ==========================================================

import uuid
from datetime import datetime, date, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, func
from sqlalchemy.orm import Session

from database import get_db

from models.users import User
from models.voice_call import VoiceCall
from models.user_status import UserStatus

from schemas.voice_call import (
    VoiceCallInitiate,
    VoiceCallCreate,
    VoiceCallUpdate,
    VoiceCallResponse
)


router = APIRouter(
    prefix="/voice-calls",
    tags=["Voice Calls"]
)


# ==========================================================
# GENERATE CALL ID
# ==========================================================

def generate_call_id():

    return "CALL-" + uuid.uuid4().hex[:12].upper()


# ==========================================================
# INITIATE VOICE CALL
# ==========================================================

@router.post(
    "/initiate",
    response_model=VoiceCallResponse,
    status_code=200
)
def initiate_voice_call(
    data: VoiceCallInitiate,
    db: Session = Depends(get_db)
):

    # ------------------------------------------------------
    # CHECK SAME USER
    # ------------------------------------------------------

    if data.caller_id == data.receiver_id:

        raise HTTPException(
            status_code=400,
            detail="Caller and receiver cannot be the same"
        )

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
            status_code=404,
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
            status_code=404,
            detail="Receiver not found"
        )

    # ------------------------------------------------------
    # CUSTOMER / CREATOR CHECK
    # ------------------------------------------------------

    if caller.role == "customer" and receiver.role == "creator":

        customer_id = caller.id
        creator_id = receiver.id

    elif caller.role == "creator" and receiver.role == "customer":

        customer_id = receiver.id
        creator_id = caller.id

    else:

        raise HTTPException(
            status_code=400,
            detail="Only customer and creator can make voice calls"
        )

    # ------------------------------------------------------
    # CHECK ACTIVE CALL
    # ------------------------------------------------------

    existing_call = (
        db.query(VoiceCall)
        .filter(
            or_(
                VoiceCall.caller_id == data.caller_id,
                VoiceCall.receiver_id == data.caller_id,
                VoiceCall.caller_id == data.receiver_id,
                VoiceCall.receiver_id == data.receiver_id
            ),
            VoiceCall.status.in_(
                ["ringing", "ongoing"]
            )
        )
        .first()
    )

    if existing_call:

        raise HTTPException(
            status_code=400,
            detail="User is already in another call"
        )

    # ------------------------------------------------------
    # CHECK USER STATUS
    #
    # ONLINE / OFFLINE DOES NOT BLOCK CALL
    # ------------------------------------------------------

    caller_status = (
        db.query(UserStatus)
        .filter(
            UserStatus.user_id == data.caller_id
        )
        .first()
    )

    receiver_status = (
        db.query(UserStatus)
        .filter(
            UserStatus.user_id == data.receiver_id
        )
        .first()
    )

    # Status is only read.
    # Offline users can still receive a call record.

    caller_online = (
        caller_status.is_online
        if caller_status
        else False
    )

    receiver_online = (
        receiver_status.is_online
        if receiver_status
        else False
    )

    # ------------------------------------------------------
    # GENERATE CALL ID AUTOMATICALLY
    # ------------------------------------------------------

    call_id = generate_call_id()

    # ------------------------------------------------------
    # CREATE CALL
    # ------------------------------------------------------

    voice_call = VoiceCall(

        call_id=call_id,

        customer_id=customer_id,
        creator_id=creator_id,

        caller_id=data.caller_id,
        receiver_id=data.receiver_id,

        start_time=None,
        end_time=None,

        duration=0,
        coins=0,
        revenue=Decimal("0.00"),

        status="ringing"
    )

    db.add(voice_call)

    db.commit()

    db.refresh(voice_call)

    return voice_call


# ==========================================================
# CREATE VOICE CALL
# ==========================================================

@router.post(
    "/",
    response_model=VoiceCallResponse,
    status_code=200
)
def create_voice_call(
    data: VoiceCallCreate,
    db: Session = Depends(get_db)
):

    # ------------------------------------------------------
    # CHECK SAME USER
    # ------------------------------------------------------

    if data.caller_id == data.receiver_id:

        raise HTTPException(
            status_code=400,
            detail="Caller and receiver cannot be the same"
        )

    # ------------------------------------------------------
    # CHECK CUSTOMER
    # ------------------------------------------------------

    customer = (
        db.query(User)
        .filter(
            User.id == data.customer_id,
            User.role == "customer"
        )
        .first()
    )

    if not customer:

        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    # ------------------------------------------------------
    # CHECK CREATOR
    # ------------------------------------------------------

    creator = (
        db.query(User)
        .filter(
            User.id == data.creator_id,
            User.role == "creator"
        )
        .first()
    )

    if not creator:

        raise HTTPException(
            status_code=404,
            detail="Creator not found"
        )

    # ------------------------------------------------------
    # CHECK CALLER
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
            status_code=404,
            detail="Caller not found"
        )

    # ------------------------------------------------------
    # CHECK RECEIVER
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
            status_code=404,
            detail="Receiver not found"
        )

    # ------------------------------------------------------
    # VALIDATE CUSTOMER / CREATOR
    # ------------------------------------------------------

    if caller.role == "customer" and receiver.role == "creator":

        if (
            caller.id != customer.id
            or receiver.id != creator.id
        ):

            raise HTTPException(
                status_code=400,
                detail="Customer and creator do not match caller and receiver"
            )

    elif caller.role == "creator" and receiver.role == "customer":

        if (
            receiver.id != customer.id
            or caller.id != creator.id
        ):

            raise HTTPException(
                status_code=400,
                detail="Customer and creator do not match caller and receiver"
            )

    else:

        raise HTTPException(
            status_code=400,
            detail="Only customer and creator can make voice calls"
        )

    # ------------------------------------------------------
    # CHECK ACTIVE CALL
    # ------------------------------------------------------

    existing_call = (
        db.query(VoiceCall)
        .filter(
            or_(
                VoiceCall.caller_id == data.caller_id,
                VoiceCall.receiver_id == data.caller_id,
                VoiceCall.caller_id == data.receiver_id,
                VoiceCall.receiver_id == data.receiver_id
            ),
            VoiceCall.status.in_(
                ["ringing", "ongoing"]
            )
        )
        .first()
    )

    if existing_call:

        raise HTTPException(
            status_code=400,
            detail="User is already in another call"
        )

    # ------------------------------------------------------
    # GENERATE CALL ID AUTOMATICALLY
    # ------------------------------------------------------

    call_id = generate_call_id()

    # ------------------------------------------------------
    # CREATE CALL
    # ------------------------------------------------------

    voice_call = VoiceCall(

        call_id=call_id,

        customer_id=data.customer_id,
        creator_id=data.creator_id,

        caller_id=data.caller_id,
        receiver_id=data.receiver_id,

        start_time=None,
        end_time=None,

        duration=0,
        coins=0,
        revenue=Decimal("0.00"),

        status="ringing"
    )

    db.add(voice_call)

    db.commit()

    db.refresh(voice_call)

    return voice_call


# ==========================================================
# ACCEPT VOICE CALL
# ==========================================================

@router.post(
    "/{call_id}/accept",
    response_model=VoiceCallResponse,
    status_code=200
)
def accept_voice_call(
    call_id: str,
    db: Session = Depends(get_db)
):

    voice_call = (
        db.query(VoiceCall)
        .filter(
            VoiceCall.call_id == call_id
        )
        .first()
    )

    if not voice_call:

        raise HTTPException(
            status_code=404,
            detail="Call not found"
        )

    # ------------------------------------------------------
    # CHECK STATUS
    # ------------------------------------------------------

    if voice_call.status != "ringing":

        raise HTTPException(
            status_code=400,
            detail="Call cannot be accepted"
        )

    # ------------------------------------------------------
    # ACCEPT CALL
    # ------------------------------------------------------

    voice_call.status = "ongoing"

    # IMPORTANT:
    # Use timezone-aware datetime

    voice_call.start_time = datetime.now(
        timezone.utc
    )

    db.commit()

    db.refresh(voice_call)

    return voice_call


# ==========================================================
# REJECT VOICE CALL
# ==========================================================

@router.post(
    "/{call_id}/reject",
    response_model=VoiceCallResponse,
    status_code=200
)
def reject_voice_call(
    call_id: str,
    db: Session = Depends(get_db)
):

    voice_call = (
        db.query(VoiceCall)
        .filter(
            VoiceCall.call_id == call_id
        )
        .first()
    )

    if not voice_call:

        raise HTTPException(
            status_code=404,
            detail="Call not found"
        )

    # ------------------------------------------------------
    # CHECK STATUS
    # ------------------------------------------------------

    if voice_call.status != "ringing":

        raise HTTPException(
            status_code=400,
            detail="Call cannot be rejected"
        )

    # ------------------------------------------------------
    # REJECT CALL
    # ------------------------------------------------------

    voice_call.status = "rejected"

    voice_call.end_time = datetime.now(
        timezone.utc
    )

    db.commit()

    db.refresh(voice_call)

    return voice_call


# ==========================================================
# END VOICE CALL
# ==========================================================

@router.post(
    "/{call_id}/end",
    response_model=VoiceCallResponse,
    status_code=200
)
def end_voice_call(
    call_id: str,
    db: Session = Depends(get_db)
):

    voice_call = (
        db.query(VoiceCall)
        .filter(
            VoiceCall.call_id == call_id
        )
        .first()
    )

    if not voice_call:

        raise HTTPException(
            status_code=404,
            detail="Call not found"
        )

    # ------------------------------------------------------
    # CHECK STATUS
    # ------------------------------------------------------

    if voice_call.status != "ongoing":

        raise HTTPException(
            status_code=400,
            detail="Only ongoing calls can be ended"
        )

    # ------------------------------------------------------
    # END TIME
    # ------------------------------------------------------

    end_time = datetime.now(
        timezone.utc
    )

    voice_call.end_time = end_time

    # ------------------------------------------------------
    # CALCULATE DURATION
    # ------------------------------------------------------

    if voice_call.start_time:

        start_time = voice_call.start_time

        # If DB returns naive datetime,
        # convert it to UTC-aware datetime

        if start_time.tzinfo is None:

            start_time = start_time.replace(
                tzinfo=timezone.utc
            )

        duration = (
            end_time - start_time
        ).total_seconds()

        voice_call.duration = max(
            0,
            int(duration)
        )

    else:

        voice_call.duration = 0

    # ------------------------------------------------------
    # STATUS
    # ------------------------------------------------------

    voice_call.status = "completed"

    db.commit()

    db.refresh(voice_call)

    return voice_call


# ==========================================================
# GET ALL VOICE CALLS
# ==========================================================

@router.get(
    "/",
    response_model=list[VoiceCallResponse],
    status_code=200
)
def get_all_voice_calls(
    call_date: date | None = None,
    state_id: int | None = None,
    creator_id: int | None = None,
    status: str | None = None,
    db: Session = Depends(get_db)
):

    query = db.query(VoiceCall)

    # ------------------------------------------------------
    # DATE FILTER
    # ------------------------------------------------------

    if call_date:

        query = query.filter(
            func.date(
                VoiceCall.created_at
            ) == call_date
        )

    # ------------------------------------------------------
    # CREATOR FILTER
    # ------------------------------------------------------

    if creator_id:

        query = query.filter(
            VoiceCall.creator_id == creator_id
        )

    # ------------------------------------------------------
    # STATUS FILTER
    # ------------------------------------------------------

    if status:

        query = query.filter(
            VoiceCall.status == status
        )

    # ------------------------------------------------------
    # STATE FILTER
    # ------------------------------------------------------

    if state_id:

        query = (
            query
            .join(
                User,
                User.id == VoiceCall.creator_id
            )
            .filter(
                User.state_id == state_id
            )
        )

    # ------------------------------------------------------
    # GET CALLS
    # ------------------------------------------------------

    calls = (
        query
        .order_by(
            VoiceCall.id.desc()
        )
        .all()
    )

    return calls


# ==========================================================
# GET SINGLE VOICE CALL
# ==========================================================

@router.get(
    "/{call_id}",
    response_model=VoiceCallResponse,
    status_code=200
)
def get_voice_call(
    call_id: str,
    db: Session = Depends(get_db)
):

    voice_call = (
        db.query(VoiceCall)
        .filter(
            VoiceCall.call_id == call_id
        )
        .first()
    )

    if not voice_call:

        raise HTTPException(
            status_code=404,
            detail="Call not found"
        )

    return voice_call


# ==========================================================
# DELETE VOICE CALL
# ==========================================================

@router.delete(
    "/{call_id}",
    status_code=200
)
def delete_voice_call(
    call_id: str,
    db: Session = Depends(get_db)
):

    voice_call = (
        db.query(VoiceCall)
        .filter(
            VoiceCall.call_id == call_id
        )
        .first()
    )

    if not voice_call:

        raise HTTPException(
            status_code=404,
            detail="Call not found"
        )

    db.delete(voice_call)

    db.commit()

    return {
        "message": "Voice call deleted successfully"
    }


# # ==========================================================
# # DASHBOARD - VOICE CALL SUMMARY
# # ==========================================================

# @router.get(
#     "/dashboard/summary"
# )
# def voice_call_summary(
#     db: Session = Depends(get_db)
# ):

#     total_calls = (
#         db.query(
#             func.count(VoiceCall.id)
#         )
#         .scalar()
#     )

#     completed_calls = (
#         db.query(
#             func.count(VoiceCall.id)
#         )
#         .filter(
#             VoiceCall.status == "completed"
#         )
#         .scalar()
#     )

#     ongoing_calls = (
#         db.query(
#             func.count(VoiceCall.id)
#         )
#         .filter(
#             VoiceCall.status == "ongoing"
#         )
#         .scalar()
#     )

#     ringing_calls = (
#         db.query(
#             func.count(VoiceCall.id)
#         )
#         .filter(
#             VoiceCall.status == "ringing"
#         )
#         .scalar()
#     )

#     rejected_calls = (
#         db.query(
#             func.count(VoiceCall.id)
#         )
#         .filter(
#             VoiceCall.status == "rejected"
#         )
#         .scalar()
#     )

#     total_revenue = (
#         db.query(
#             func.coalesce(
#                 func.sum(
#                     VoiceCall.revenue
#                 ),
#                 0
#             )
#         )
#         .scalar()
#     )

#     total_duration = (
#         db.query(
#             func.coalesce(
#                 func.sum(
#                     VoiceCall.duration
#                 ),
#                 0
#             )
#         )
#         .scalar()
#     )

#     return {
#         "total_calls": total_calls or 0,
#         "completed_calls": completed_calls or 0,
#         "ongoing_calls": ongoing_calls or 0,
#         "ringing_calls": ringing_calls or 0,
#         "rejected_calls": rejected_calls or 0,
#         "total_revenue": str(
#             total_revenue or 0
#         ),
#         "total_duration": total_duration or 0
#     }


# # ==========================================================
# # DAILY CALL VOLUME
# # ==========================================================

# @router.get(
#     "/dashboard/daily-call-volume"
# )
# def daily_call_volume(
#     db: Session = Depends(get_db)
# ):

#     result = (
#         db.query(
#             func.date(
#                 VoiceCall.created_at
#             ).label("date"),

#             func.count(
#                 VoiceCall.id
#             ).label("call_count")
#         )
#         .group_by(
#             func.date(
#                 VoiceCall.created_at
#             )
#         )
#         .order_by(
#             func.date(
#                 VoiceCall.created_at
#             )
#         )
#         .all()
#     )

#     return [
#         {
#             "date": row.date,
#             "call_count": row.call_count
#         }
#         for row in result
#     ]


# # ==========================================================
# # REVENUE BY CALLS
# # ==========================================================

# @router.get(
#     "/dashboard/revenue-by-calls"
# )
# def revenue_by_calls(
#     db: Session = Depends(get_db)
# ):

#     result = (
#         db.query(
#             func.date(
#                 VoiceCall.created_at
#             ).label("date"),

#             func.count(
#                 VoiceCall.id
#             ).label("call_count"),

#             func.coalesce(
#                 func.sum(
#                     VoiceCall.revenue
#                 ),
#                 0
#             ).label("revenue")
#         )
#         .group_by(
#             func.date(
#                 VoiceCall.created_at
#             )
#         )
#         .order_by(
#             func.date(
#                 VoiceCall.created_at
#             )
#         )
#         .all()
#     )

#     return [
#         {
#             "date": row.date,
#             "call_count": row.call_count,
#             "revenue": str(
#                 row.revenue
#             )
#         }
#         for row in result
#     ]


# # ==========================================================
# # AVERAGE CALL DURATION
# # ==========================================================

# @router.get(
#     "/dashboard/average-duration"
# )
# def average_call_duration(
#     db: Session = Depends(get_db)
# ):

#     result = (
#         db.query(
#             func.date(
#                 VoiceCall.created_at
#             ).label("date"),

#             func.avg(
#                 VoiceCall.duration
#             ).label("average_duration")
#         )
#         .filter(
#             VoiceCall.status == "completed"
#         )
#         .group_by(
#             func.date(
#                 VoiceCall.created_at
#             )
#         )
#         .order_by(
#             func.date(
#                 VoiceCall.created_at
#             )
#         )
#         .all()
#     )

#     return [
#         {
#             "date": row.date,
#             "average_duration": round(
#                 float(
#                     row.average_duration or 0
#                 ),
#                 2
#             )
#         }
#         for row in result
#     ]