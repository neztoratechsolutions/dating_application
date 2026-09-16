import uuid

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
# GENERATE VIDEO CALL ID
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
        last_number = int(
            last_call.video_call_id.split("-")[-1]
        )

        next_number = last_number + 1

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

    if caller.role not in ["customer", "creator"]:
        raise HTTPException(
            status_code=400,
            detail="Caller must be a customer or creator"
        )

    if receiver.role not in ["customer", "creator"]:
        raise HTTPException(
            status_code=400,
            detail="Receiver must be a customer or creator"
        )

    if caller.role == receiver.role:
        raise HTTPException(
            status_code=400,
            detail="Video call is allowed only between customer and creator"
        )

    if caller.role == "customer":
        customer_id = caller.id
        creator_id = receiver.id
    else:
        customer_id = receiver.id
        creator_id = caller.id

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

    # Online status is informational only.
    # Offline users are not blocked.
    caller_status = db.query(UserStatus).filter(
        UserStatus.user_id == request.caller_id
    ).first()

    receiver_status = db.query(UserStatus).filter(
        UserStatus.user_id == request.receiver_id
    ).first()

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

        status="ringing"
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

        status="ringing"
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
            func.date(VideoCall.created_at) == call_date
        )

    if start_date:
        query = query.filter(
            func.date(VideoCall.created_at) >= start_date
        )

    if end_date:
        query = query.filter(
            func.date(VideoCall.created_at) <= end_date
        )

    if customer_id:
        query = query.filter(
            VideoCall.customer_id == customer_id
        )

    if creator_id:
        query = query.filter(
            VideoCall.creator_id == creator_id
        )

    if caller_id:
        query = query.filter(
            VideoCall.caller_id == caller_id
        )

    if receiver_id:
        query = query.filter(
            VideoCall.receiver_id == receiver_id
        )

    if status:
        query = query.filter(
            VideoCall.status == status
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
        VideoCall.video_call_id == video_call_id
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

    video_call.status = "ongoing"

    video_call.start_time = datetime.now(
        timezone.utc
    )

    db.commit()
    db.refresh(video_call)

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
        VideoCall.video_call_id == video_call_id
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

    video_call.duration = Decimal("0.00")

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
        VideoCall.video_call_id == video_call_id
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

    duration_hours = round(
        duration_seconds / 3600,
        2
    )

    video_call.end_time = end_time

    video_call.duration = Decimal(
        str(duration_hours)
    )

    video_call.status = "completed"

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
        VideoCall.video_call_id == video_call_id
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
        VideoCall.video_call_id == video_call_id
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
        setattr(video_call, key, value)

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
        VideoCall.video_call_id == video_call_id
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


# # ==========================================================
# # DASHBOARD SUMMARY
# # ==========================================================

# @router.get(
#     "/dashboard/summary"
# )
# def video_call_dashboard_summary(
#     db: Session = Depends(get_db)
# ):

#     total_calls = db.query(VideoCall).count()

#     completed_calls = db.query(VideoCall).filter(
#         VideoCall.status == "completed"
#     ).count()

#     ongoing_calls = db.query(VideoCall).filter(
#         VideoCall.status == "ongoing"
#     ).count()

#     ringing_calls = db.query(VideoCall).filter(
#         VideoCall.status == "ringing"
#     ).count()

#     rejected_calls = db.query(VideoCall).filter(
#         VideoCall.status == "rejected"
#     ).count()

#     total_duration = db.query(
#         func.coalesce(
#             func.sum(VideoCall.duration),
#             0
#         )
#     ).scalar()

#     total_coins = db.query(
#         func.coalesce(
#             func.sum(VideoCall.coins),
#             0
#         )
#     ).scalar()

#     total_revenue = db.query(
#         func.coalesce(
#             func.sum(VideoCall.revenue),
#             0
#         )
#     ).scalar()

#     return {
#         "status": True,
#         "message": "Video call dashboard summary fetched successfully",
#         "data": {
#             "total_calls": total_calls,
#             "completed_calls": completed_calls,
#             "ongoing_calls": ongoing_calls,
#             "ringing_calls": ringing_calls,
#             "rejected_calls": rejected_calls,
#             "total_duration": total_duration,
#             "total_coins": total_coins,
#             "total_revenue": total_revenue
#         }
#     }


# # ==========================================================
# # DAILY VIDEO CALL VOLUME
# # ==========================================================

# @router.get(
#     "/dashboard/daily-volume"
# )
# def daily_video_call_volume(
#     start_date: date | None = None,
#     end_date: date | None = None,
#     db: Session = Depends(get_db)
# ):

#     query = db.query(
#         func.date(
#             VideoCall.created_at
#         ).label("call_date"),

#         func.count(
#             VideoCall.id
#         ).label("total_calls")
#     )

#     if start_date:
#         query = query.filter(
#             func.date(VideoCall.created_at) >= start_date
#         )

#     if end_date:
#         query = query.filter(
#             func.date(VideoCall.created_at) <= end_date
#         )

#     result = query.group_by(
#         func.date(VideoCall.created_at)
#     ).order_by(
#         func.date(VideoCall.created_at)
#     ).all()

#     if not result:
#         raise HTTPException(
#             status_code=404,
#             detail="No daily video call data found"
#         )

#     return {
#         "status": True,
#         "message": "Daily video call volume fetched successfully",
#         "data": [
#             {
#                 "date": row.call_date,
#                 "total_calls": row.total_calls
#             }
#             for row in result
#         ]
#     }


# # ==========================================================
# # VIDEO CALL REVENUE
# # ==========================================================

# @router.get(
#     "/dashboard/revenue"
# )
# def video_call_revenue(
#     start_date: date | None = None,
#     end_date: date | None = None,
#     db: Session = Depends(get_db)
# ):

#     query = db.query(
#         func.date(
#             VideoCall.created_at
#         ).label("call_date"),

#         func.coalesce(
#             func.sum(VideoCall.revenue),
#             0
#         ).label("total_revenue")
#     )

#     if start_date:
#         query = query.filter(
#             func.date(VideoCall.created_at) >= start_date
#         )

#     if end_date:
#         query = query.filter(
#             func.date(VideoCall.created_at) <= end_date
#         )

#     result = query.group_by(
#         func.date(VideoCall.created_at)
#     ).order_by(
#         func.date(VideoCall.created_at)
#     ).all()

#     if not result:
#         raise HTTPException(
#             status_code=404,
#             detail="No video call revenue data found"
#         )

#     return {
#         "status": True,
#         "message": "Video call revenue fetched successfully",
#         "data": [
#             {
#                 "date": row.call_date,
#                 "total_revenue": row.total_revenue
#             }
#             for row in result
#         ]
#     }


# # ==========================================================
# # AVERAGE VIDEO CALL DURATION
# # ==========================================================

# @router.get(
#     "/dashboard/average-duration"
# )
# def average_video_call_duration(
#     start_date: date | None = None,
#     end_date: date | None = None,
#     db: Session = Depends(get_db)
# ):

#     query = db.query(
#         func.date(
#             VideoCall.created_at
#         ).label("call_date"),

#         func.coalesce(
#             func.avg(VideoCall.duration),
#             0
#         ).label("average_duration")
#     ).filter(
#         VideoCall.status == "completed"
#     )

#     if start_date:
#         query = query.filter(
#             func.date(VideoCall.created_at) >= start_date
#         )

#     if end_date:
#         query = query.filter(
#             func.date(VideoCall.created_at) <= end_date
#         )

#     result = query.group_by(
#         func.date(VideoCall.created_at)
#     ).order_by(
#         func.date(VideoCall.created_at)
#     ).all()

#     if not result:
#         raise HTTPException(
#             status_code=404,
#             detail="No average video call duration data found"
#         )

#     return {
#         "status": True,
#         "message": "Average video call duration fetched successfully",
#         "data": [
#             {
#                 "date": row.call_date,
#                 "average_duration": round(
#                     float(row.average_duration),
#                     2
#                 )
#             }
#             for row in result
#         ]
#     }