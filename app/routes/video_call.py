from datetime import datetime, timedelta, time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session,aliased

from database import get_db

from models.video_call import VideoCall
from models.users import User

from schemas.video_call import (
    VideoCallCreate,
    VideoCallUpdate,
    VideoCallResponse
)


router = APIRouter(
    prefix="/video-calls",
    tags=["Video Calls"]
)


# ==========================================================
# CREATE VIDEO CALL
# ==========================================================

@router.post("/", response_model=VideoCallResponse)
def create_video_call(
    data: VideoCallCreate,
    db: Session = Depends(get_db)
):

    # --------------------------------
    # Check Customer
    # --------------------------------

    customer = (
        db.query(User)
        .filter(User.id == data.customer_id)
        .first()
    )

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    # --------------------------------
    # Check Creator
    # --------------------------------

    creator = (
        db.query(User)
        .filter(User.id == data.creator_id)
        .first()
    )

    if not creator:
        raise HTTPException(
            status_code=404,
            detail="Creator not found"
        )

    # --------------------------------
    # Generate Video Call ID
    # --------------------------------

    last_call = (
        db.query(VideoCall)
        .order_by(VideoCall.id.desc())
        .first()
    )

    if last_call:
        next_number = last_call.id + 20000
    else:
        next_number = 20000

    video_call_id = f"VID-{next_number}"

    # --------------------------------
    # Create Video Call
    # --------------------------------

    video_call = VideoCall(
        video_call_id=video_call_id,
        customer_id=data.customer_id,
        creator_id=data.creator_id,
        start_time=data.start_time,
        end_time=data.end_time,
        duration=data.duration,
        coins=data.coins,
        revenue=data.revenue,
        status=data.status
    )

    db.add(video_call)
    db.commit()
    db.refresh(video_call)

    return video_call


# ==========================================================
# GET ALL VIDEO CALLS
# ==========================================================

@router.get("/", response_model=list[VideoCallResponse])
def get_all_video_calls(
    state_id: int | None = None,
    creator_id: int | None = None,
    status: str | None = None,
    db: Session = Depends(get_db)
):

    # --------------------------------
    # Create User Aliases
    # --------------------------------

    customer_user = aliased(User)
    creator_user = aliased(User)

    # --------------------------------
    # Base Query
    # --------------------------------

    query = (
        db.query(VideoCall)
        .join(
            customer_user,
            customer_user.id == VideoCall.customer_id
        )
        .join(
            creator_user,
            creator_user.id == VideoCall.creator_id
        )
    )

    # --------------------------------
    # State Filter
    # --------------------------------
    # Customer OR Creator state

    if state_id is not None:

        query = query.filter(
            or_(
                customer_user.state_id == state_id,
                creator_user.state_id == state_id
            )
        )

    # --------------------------------
    # Creator Filter
    # --------------------------------

    if creator_id is not None:

        query = query.filter(
            VideoCall.creator_id == creator_id
        )

    # --------------------------------
    # Status Filter
    # --------------------------------

    if status is not None:

        query = query.filter(
            VideoCall.status == status
        )

    # --------------------------------
    # Get Result
    # --------------------------------

    calls = (
        query
        .order_by(VideoCall.id.desc())
        .all()
    )

    return calls


# ==========================================================
# DASHBOARD SUMMARY
# ==========================================================

@router.get("/dashboard/summary")
def get_video_call_dashboard_summary(
    db: Session = Depends(get_db)
):

    # Today's start time

    today_start = datetime.combine(
        datetime.now().date(),
        time.min
    )

    # --------------------------------
    # Total Video Calls Today
    # --------------------------------

    total_calls_today = (
        db.query(func.count(VideoCall.id))
        .filter(
            VideoCall.start_time >= today_start
        )
        .scalar()
    )

    # --------------------------------
    # Active Now
    # --------------------------------

    active_now = (
        db.query(func.count(VideoCall.id))
        .filter(
            VideoCall.status == "ongoing"
        )
        .scalar()
    )

    # --------------------------------
    # Total Minutes
    # --------------------------------

    total_seconds = (
        db.query(
            func.coalesce(
                func.sum(VideoCall.duration),
                0
            )
        )
        .filter(
            VideoCall.start_time >= today_start
        )
        .scalar()
    )

    total_minutes = round(
        float(total_seconds) / 60,
        2
    )

    # --------------------------------
    # Average Duration
    # --------------------------------

    avg_duration_seconds = (
        db.query(
            func.coalesce(
                func.avg(VideoCall.duration),
                0
            )
        )
        .filter(
            VideoCall.start_time >= today_start
        )
        .scalar()
    )

    avg_duration_seconds = round(
        float(avg_duration_seconds),
        2
    )

    avg_minutes = int(
        avg_duration_seconds // 60
    )

    avg_seconds = int(
        avg_duration_seconds % 60
    )

    avg_duration = (
        f"{avg_minutes}m {avg_seconds}s"
    )

    # --------------------------------
    # Revenue
    # --------------------------------

    revenue = (
        db.query(
            func.coalesce(
                func.sum(VideoCall.revenue),
                0
            )
        )
        .filter(
            VideoCall.start_time >= today_start
        )
        .scalar()
    )

    # --------------------------------
    # Failed Calls
    # --------------------------------

    failed_calls = (
        db.query(func.count(VideoCall.id))
        .filter(
            VideoCall.start_time >= today_start,
            VideoCall.status.in_([
                "missed",
                "cancelled",
                "failed"
            ])
        )
        .scalar()
    )

    return {
        "total_calls_today": total_calls_today,
        "active_now": active_now,
        "total_minutes": total_minutes,
        "avg_duration": avg_duration,
        "revenue": float(revenue),
        "failed_calls": failed_calls
    }


# ==========================================================
# DAILY VIDEO CALL VOLUME
# ==========================================================

@router.get("/dashboard/daily-call-volume")
def get_daily_video_call_volume(
    db: Session = Depends(get_db)
):

    today = datetime.now().date()

    start_date = today - timedelta(days=6)

    start_datetime = datetime.combine(
        start_date,
        time.min
    )

    result = (
        db.query(
            func.date(
                VideoCall.start_time
            ).label("call_date"),

            func.count(
                VideoCall.id
            ).label("total_calls")
        )
        .filter(
            VideoCall.start_time >= start_datetime
        )
        .group_by(
            func.date(
                VideoCall.start_time
            )
        )
        .order_by(
            func.date(
                VideoCall.start_time
            )
        )
        .all()
    )

    call_data = {
        row.call_date: row.total_calls
        for row in result
    }

    response = []

    for i in range(7):

        current_date = (
            start_date +
            timedelta(days=i)
        )

        response.append({
            "date": current_date.strftime(
                "%Y-%m-%d"
            ),

            "day": current_date.strftime(
                "%a"
            ),

            "calls": call_data.get(
                current_date,
                0
            )
        })

    return {
        "data": response
    }


# ==========================================================
# REVENUE BY VIDEO CALLS
# ==========================================================

@router.get("/dashboard/revenue-by-calls")
def get_video_call_revenue_by_calls(
    db: Session = Depends(get_db)
):

    today = datetime.now().date()

    start_date = today - timedelta(days=6)

    start_datetime = datetime.combine(
        start_date,
        time.min
    )

    result = (
        db.query(
            func.date(
                VideoCall.start_time
            ).label("call_date"),

            func.coalesce(
                func.sum(VideoCall.revenue),
                0
            ).label("total_revenue")
        )
        .filter(
            VideoCall.start_time >= start_datetime,
            VideoCall.status.in_([
                "completed",
                "ongoing"
            ])
        )
        .group_by(
            func.date(
                VideoCall.start_time
            )
        )
        .order_by(
            func.date(
                VideoCall.start_time
            )
        )
        .all()
    )

    revenue_data = {
        row.call_date: float(
            row.total_revenue
        )
        for row in result
    }

    response = []

    for i in range(7):

        current_date = (
            start_date +
            timedelta(days=i)
        )

        response.append({
            "date": current_date.strftime(
                "%Y-%m-%d"
            ),

            "day": current_date.strftime(
                "%a"
            ),

            "revenue": revenue_data.get(
                current_date,
                0
            )
        })

    return {
        "data": response
    }


# ==========================================================
# AVERAGE DURATION TREND
# ==========================================================

@router.get("/dashboard/avg-duration-trend")
def get_video_call_avg_duration_trend(
    db: Session = Depends(get_db)
):

    today = datetime.now().date()

    start_date = today - timedelta(days=6)

    start_datetime = datetime.combine(
        start_date,
        time.min
    )

    result = (
        db.query(
            func.date(
                VideoCall.start_time
            ).label("call_date"),

            func.avg(
                VideoCall.duration
            ).label("avg_duration")
        )
        .filter(
            VideoCall.start_time >= start_datetime,
            VideoCall.status.in_([
                "completed",
                "ongoing"
            ])
        )
        .group_by(
            func.date(
                VideoCall.start_time
            )
        )
        .order_by(
            func.date(
                VideoCall.start_time
            )
        )
        .all()
    )

    duration_data = {
        row.call_date: round(
            float(row.avg_duration),
            2
        )
        for row in result
    }

    response = []

    for i in range(7):

        current_date = (
            start_date +
            timedelta(days=i)
        )

        response.append({
            "date": current_date.strftime(
                "%Y-%m-%d"
            ),

            "day": current_date.strftime(
                "%a"
            ),

            "avg_duration": duration_data.get(
                current_date,
                0
            )
        })

    return {
        "data": response
    }


# ==========================================================
# GET VIDEO CALL BY ID
# ==========================================================

@router.get("/{id}", response_model=VideoCallResponse)
def get_video_call(
    id: int,
    db: Session = Depends(get_db)
):

    call = (
        db.query(VideoCall)
        .filter(
            VideoCall.id == id
        )
        .first()
    )

    if not call:
        raise HTTPException(
            status_code=404,
            detail="Video call not found"
        )

    return call


# ==========================================================
# UPDATE VIDEO CALL
# ==========================================================

@router.put("/{id}", response_model=VideoCallResponse)
def update_video_call(
    id: int,
    data: VideoCallUpdate,
    db: Session = Depends(get_db)
):

    call = (
        db.query(VideoCall)
        .filter(
            VideoCall.id == id
        )
        .first()
    )

    if not call:
        raise HTTPException(
            status_code=404,
            detail="Video call not found"
        )

    update_data = data.model_dump(
        exclude_unset=True
    )

    for field, value in update_data.items():
        setattr(
            call,
            field,
            value
        )

    db.commit()
    db.refresh(call)

    return call


# ==========================================================
# DELETE VIDEO CALL
# ==========================================================

@router.delete("/{video_call_id}")
def delete_video_call(
    video_call_id: str,
    db: Session = Depends(get_db)
):

    call = (
        db.query(VideoCall)
        .filter(
            VideoCall.video_call_id == video_call_id
        )
        .first()
    )

    if not call:
        raise HTTPException(
            status_code=404,
            detail="Video call not found"
        )

    db.delete(call)
    db.commit()

    return {
        "message": "Video call deleted successfully"
    }