from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from database import get_db
from models.users import User
from models.user_status import UserStatus
from models.voice_call import VoiceCall

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
# GENERATE VOICE CALL ID
# Format: VOICE-2026-09-15-01
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
# VALIDATE CUSTOMER / CREATOR / CALLER / RECEIVER
# ==========================================================

def validate_customer_creator(
    db: Session,
    customer_id: int,
    creator_id: int,
    caller_id: int,
    receiver_id: int
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

    if caller_id == receiver_id:
        raise HTTPException(
            status_code=400,
            detail="Caller and receiver cannot be the same"
        )

    if caller.role == "customer" and receiver.role == "creator":

        if (
            caller_id != customer_id
            or receiver_id != creator_id
        ):
            raise HTTPException(
                status_code=400,
                detail="Caller and receiver do not match customer and creator"
            )

    elif caller.role == "creator" and receiver.role == "customer":

        if (
            caller_id != creator_id
            or receiver_id != customer_id
        ):
            raise HTTPException(
                status_code=400,
                detail="Caller and receiver do not match customer and creator"
            )

    else:
        raise HTTPException(
            status_code=400,
            detail="Voice call is allowed only between customer and creator"
        )

    return customer, creator, caller, receiver


# ==========================================================
# INITIATE VOICE CALL
# ==========================================================

@router.post(
    "/initiate",
    response_model=VoiceCallResponse,
    status_code=201
)
def initiate_voice_call(
    data: VoiceCallInitiate,
    db: Session = Depends(get_db)
):

    caller = (
        db.query(User)
        .filter(User.id == data.caller_id)
        .first()
    )

    if not caller:
        raise HTTPException(
            status_code=404,
            detail="Caller not found"
        )

    receiver = (
        db.query(User)
        .filter(User.id == data.receiver_id)
        .first()
    )

    if not receiver:
        raise HTTPException(
            status_code=404,
            detail="Receiver not found"
        )

    if caller.id == receiver.id:
        raise HTTPException(
            status_code=400,
            detail="Caller and receiver cannot be the same"
        )

    # ------------------------------------------------------
    # Only customer <-> creator calls are allowed
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
            detail="Voice call is allowed only between customer and creator"
        )

    # ------------------------------------------------------
    # Check existing ringing / ongoing call
    # ------------------------------------------------------

    existing_call = (
        db.query(VoiceCall)
        .filter(
            VoiceCall.status.in_(
                ["ringing", "ongoing"]
            ),
            or_(
                (
                    (VoiceCall.caller_id == caller.id)
                    &
                    (VoiceCall.receiver_id == receiver.id)
                ),
                (
                    (VoiceCall.caller_id == receiver.id)
                    &
                    (VoiceCall.receiver_id == caller.id)
                )
            )
        )
        .first()
    )

    if existing_call:

        raise HTTPException(
            status_code=400,
            detail="An active voice call already exists between these users"
        )

    # ------------------------------------------------------
    # User online status
    # ------------------------------------------------------
    # Offline users are also allowed to receive a call.
    # This check is only informational.

    receiver_status = (
        db.query(UserStatus)
        .filter(
            UserStatus.user_id == receiver.id
        )
        .first()
    )

    # ------------------------------------------------------
    # Generate Call ID
    # ------------------------------------------------------

    call_id = generate_call_id(db)

    # ------------------------------------------------------
    # Create Call
    # ------------------------------------------------------

    new_call = VoiceCall(

        call_id=call_id,

        customer_id=customer_id,
        creator_id=creator_id,

        caller_id=caller.id,
        receiver_id=receiver.id,

        start_time=None,
        end_time=None,

        duration=Decimal("0.00"),

        coins=0,
        revenue=Decimal("0.00"),

        status="ringing"
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
    status_code=201
)
def create_voice_call(
    data: VoiceCallCreate,
    db: Session = Depends(get_db)
):

    validate_customer_creator(
        db=db,
        customer_id=data.customer_id,
        creator_id=data.creator_id,
        caller_id=data.caller_id,
        receiver_id=data.receiver_id
    )

    # ------------------------------------------------------
    # Check existing active call
    # ------------------------------------------------------

    existing_call = (
        db.query(VoiceCall)
        .filter(
            VoiceCall.status.in_(
                ["ringing", "ongoing"]
            ),
            or_(
                (
                    (VoiceCall.caller_id == data.caller_id)
                    &
                    (VoiceCall.receiver_id == data.receiver_id)
                ),
                (
                    (VoiceCall.caller_id == data.receiver_id)
                    &
                    (VoiceCall.receiver_id == data.caller_id)
                )
            )
        )
        .first()
    )

    if existing_call:

        raise HTTPException(
            status_code=400,
            detail="An active voice call already exists between these users"
        )

    # ------------------------------------------------------
    # Generate Call ID
    # ------------------------------------------------------

    call_id = generate_call_id(db)

    new_call = VoiceCall(

        call_id=call_id,

        customer_id=data.customer_id,
        creator_id=data.creator_id,

        caller_id=data.caller_id,
        receiver_id=data.receiver_id,

        start_time=data.start_time,
        end_time=data.end_time,

        duration=data.duration,

        coins=data.coins,
        revenue=data.revenue,

        status=data.status
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

    call_date: str | None = Query(
        default=None,
        description="YYYY-MM-DD"
    ),

    start_date: str | None = Query(
        default=None,
        description="YYYY-MM-DD"
    ),

    end_date: str | None = Query(
        default=None,
        description="YYYY-MM-DD"
    ),

    customer_id: int | None = None,
    creator_id: int | None = None,
    caller_id: int | None = None,
    receiver_id: int | None = None,
    status: str | None = None,

    db: Session = Depends(get_db)
):

    query = db.query(VoiceCall)

    # ------------------------------------------------------
    # Single date filter
    # ------------------------------------------------------

    if call_date:

        try:
            parsed_date = datetime.strptime(
                call_date,
                "%Y-%m-%d"
            ).date()

        except ValueError:

            raise HTTPException(
                status_code=400,
                detail="Invalid call_date format. Use YYYY-MM-DD"
            )

        query = query.filter(
            func.date(
                VoiceCall.created_at
            ) == parsed_date
        )

    # ------------------------------------------------------
    # Start date
    # ------------------------------------------------------

    if start_date:

        try:
            parsed_start_date = datetime.strptime(
                start_date,
                "%Y-%m-%d"
            ).date()

        except ValueError:

            raise HTTPException(
                status_code=400,
                detail="Invalid start_date format. Use YYYY-MM-DD"
            )

        query = query.filter(
            func.date(
                VoiceCall.created_at
            ) >= parsed_start_date
        )

    # ------------------------------------------------------
    # End date
    # ------------------------------------------------------

    if end_date:

        try:
            parsed_end_date = datetime.strptime(
                end_date,
                "%Y-%m-%d"
            ).date()

        except ValueError:

            raise HTTPException(
                status_code=400,
                detail="Invalid end_date format. Use YYYY-MM-DD"
            )

        query = query.filter(
            func.date(
                VoiceCall.created_at
            ) <= parsed_end_date
        )

    if customer_id is not None:

        query = query.filter(
            VoiceCall.customer_id == customer_id
        )

    if creator_id is not None:

        query = query.filter(
            VoiceCall.creator_id == creator_id
        )

    if caller_id is not None:

        query = query.filter(
            VoiceCall.caller_id == caller_id
        )

    if receiver_id is not None:

        query = query.filter(
            VoiceCall.receiver_id == receiver_id
        )

    if status:

        query = query.filter(
            VoiceCall.status == status
        )

    calls = (
        query
        .order_by(VoiceCall.id.desc())
        .all()
    )

    if not calls:

        raise HTTPException(
            status_code=404,
            detail="No voice calls found"
        )

    return calls


# # ==========================================================
# # DASHBOARD SUMMARY
# # ==========================================================

# @router.get(
#     "/dashboard/summary"
# )
# def voice_call_dashboard_summary(
#     db: Session = Depends(get_db)
# ):

#     total_calls = (
#         db.query(VoiceCall)
#         .count()
#     )

#     completed_calls = (
#         db.query(VoiceCall)
#         .filter(
#             VoiceCall.status == "completed"
#         )
#         .count()
#     )

#     ongoing_calls = (
#         db.query(VoiceCall)
#         .filter(
#             VoiceCall.status == "ongoing"
#         )
#         .count()
#     )

#     ringing_calls = (
#         db.query(VoiceCall)
#         .filter(
#             VoiceCall.status == "ringing"
#         )
#         .count()
#     )

#     rejected_calls = (
#         db.query(VoiceCall)
#         .filter(
#             VoiceCall.status == "rejected"
#         )
#         .count()
#     )

#     total_coins = (
#         db.query(
#             func.coalesce(
#                 func.sum(VoiceCall.coins),
#                 0
#             )
#         )
#         .scalar()
#     )

#     total_revenue = (
#         db.query(
#             func.coalesce(
#                 func.sum(VoiceCall.revenue),
#                 0
#             )
#         )
#         .scalar()
#     )

#     return {
#         "status": True,
#         "message": "Voice call dashboard summary fetched successfully",
#         "data": {
#             "total_calls": total_calls,
#             "completed_calls": completed_calls,
#             "ongoing_calls": ongoing_calls,
#             "ringing_calls": ringing_calls,
#             "rejected_calls": rejected_calls,
#             "total_coins": total_coins,
#             "total_revenue": total_revenue
#         }
#     }


# # ==========================================================
# # DAILY CALL VOLUME
# # ==========================================================

# @router.get(
#     "/dashboard/daily-volume"
# )
# def daily_call_volume(
#     db: Session = Depends(get_db)
# ):

#     results = (
#         db.query(
#             func.date(
#                 VoiceCall.created_at
#             ).label("date"),

#             func.count(
#                 VoiceCall.id
#             ).label("total_calls")
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

#     if not results:

#         raise HTTPException(
#             status_code=404,
#             detail="No voice call volume data found"
#         )

#     return {
#         "status": True,
#         "message": "Daily voice call volume fetched successfully",
#         "data": [
#             {
#                 "date": row.date,
#                 "total_calls": row.total_calls
#             }
#             for row in results
#         ]
#     }


# # ==========================================================
# # REVENUE BY CALLS
# # ==========================================================

# @router.get(
#     "/dashboard/revenue"
# )
# def voice_call_revenue(
#     db: Session = Depends(get_db)
# ):

#     result = (
#         db.query(
#             func.coalesce(
#                 func.sum(VoiceCall.revenue),
#                 0
#             ).label("total_revenue"),

#             func.coalesce(
#                 func.sum(VoiceCall.coins),
#                 0
#             ).label("total_coins")
#         )
#         .first()
#     )

#     return {
#         "status": True,
#         "message": "Voice call revenue fetched successfully",
#         "data": {
#             "total_revenue": result.total_revenue,
#             "total_coins": result.total_coins
#         }
#     }


# # ==========================================================
# # AVERAGE CALL DURATION
# # Duration is stored in HOURS
# # ==========================================================

# @router.get(
#     "/dashboard/average-duration"
# )
# def average_call_duration(
#     db: Session = Depends(get_db)
# ):

#     result = (
#         db.query(
#             func.coalesce(
#                 func.avg(VoiceCall.duration),
#                 0
#             )
#         )
#         .filter(
#             VoiceCall.status == "completed"
#         )
#         .scalar()
#     )

#     return {
#         "status": True,
#         "message": "Average voice call duration fetched successfully",
#         "data": {
#             "average_duration_hours": round(
#                 float(result),
#                 2
#             )
#         }
#     }


# ==========================================================
# ACCEPT VOICE CALL
# ==========================================================

@router.post(
    "/{call_id}/accept",
    response_model=VoiceCallResponse
)
def accept_voice_call(
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

    if call.status != "ringing":

        raise HTTPException(
            status_code=400,
            detail="Only ringing calls can be accepted"
        )

    call.status = "ongoing"

    call.start_time = datetime.now(
        timezone.utc
    )

    db.commit()
    db.refresh(call)

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
            status_code=404,
            detail="Voice call not found"
        )

    if call.status != "ringing":

        raise HTTPException(
            status_code=400,
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
# Duration calculated in HOURS
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
            status_code=404,
            detail="Voice call not found"
        )

    if call.status != "ongoing":

        raise HTTPException(
            status_code=400,
            detail="Only ongoing calls can be ended"
        )

    if not call.start_time:

        raise HTTPException(
            status_code=400,
            detail="Call start time is missing"
        )

    end_time = datetime.now(
        timezone.utc
    )

    start_time = call.start_time

    # ------------------------------------------------------
    # Handle naive datetime
    # ------------------------------------------------------

    if start_time.tzinfo is None:

        start_time = start_time.replace(
            tzinfo=timezone.utc
        )

    # ------------------------------------------------------
    # Calculate duration
    # Seconds -> Hours
    # ------------------------------------------------------

    duration_seconds = (
        end_time - start_time
    ).total_seconds()

    duration_hours = round(
        duration_seconds / 3600,
        2
    )

    call.end_time = end_time

    call.duration = Decimal(
        str(duration_hours)
    )

    call.status = "completed"

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

    if data.start_time is not None:

        call.start_time = data.start_time

    if data.end_time is not None:

        call.end_time = data.end_time

    if data.duration is not None:

        call.duration = data.duration

    if data.coins is not None:

        call.coins = data.coins

    if data.revenue is not None:

        call.revenue = data.revenue

    if data.status is not None:

        call.status = data.status

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
        "status": True,
        "message": "Voice call deleted successfully"
    }