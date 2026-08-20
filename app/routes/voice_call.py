from datetime import datetime, timedelta, time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session,aliased

from database import get_db
from models.voice_call import VoiceCall
from models.state import State
from models.users import User

from schemas.voice_call import (
    VoiceCallCreate,
    VoiceCallUpdate,
    VoiceCallResponse
)


router = APIRouter(
    prefix="/voice-calls",
    tags=["Voice Calls"]
)



@router.post("/", response_model=VoiceCallResponse)
def create_voice_call(
    data: VoiceCallCreate,
    db: Session = Depends(get_db)
):
    existing_call = (
        db.query(VoiceCall)
        .filter(VoiceCall.call_id == data.call_id)
        .first()
    )

    if existing_call:
        raise HTTPException(
            status_code=400,
            detail="Call ID already exists"
        )

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

    voice_call = VoiceCall(
        call_id=data.call_id,
        customer_id=data.customer_id,
        creator_id=data.creator_id,
        start_time=data.start_time,
        end_time=data.end_time,
        duration=data.duration,
        coins=data.coins,
        revenue=data.revenue,
        status=data.status
    )

    db.add(voice_call)
    db.commit()
    db.refresh(voice_call)

    return voice_call



@router.get("/", response_model=list[VoiceCallResponse])
def get_all_voice_calls(
    db: Session = Depends(get_db)
):
    calls = (
        db.query(VoiceCall)
        .order_by(VoiceCall.id.desc())
        .all()
    )

    return calls



@router.get("/{id}", response_model=VoiceCallResponse)
def get_voice_call(
    id: int,
    db: Session = Depends(get_db)
):
    call = (
        db.query(VoiceCall)
        .filter(VoiceCall.id == id)
        .first()
    )

    if not call:
        raise HTTPException(
            status_code=404,
            detail="Voice call not found"
        )

    return call




@router.delete("/{call_id}")
def delete_voice_call(
    call_id: str,
    db: Session = Depends(get_db)
):
    call = (
        db.query(VoiceCall)
        .filter(VoiceCall.call_id == call_id)
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
        "message": "Voice call deleted successfully"
    }



@router.get("/dashboard/summary")
def get_voice_call_dashboard_summary(
    db: Session = Depends(get_db)
):
    # Today's start time
    today_start = datetime.combine(
        datetime.now().date(),
        time.min
    )

    # --------------------------------
    # Total Calls Today
    # --------------------------------

    total_calls_today = (
        db.query(func.count(VoiceCall.id))
        .filter(
            VoiceCall.start_time >= today_start
        )
        .scalar()
    )

    # --------------------------------
    # Active Now
    # --------------------------------

    active_now = (
        db.query(func.count(VoiceCall.id))
        .filter(
            VoiceCall.status == "ongoing"
        )
        .scalar()
    )

    # --------------------------------
    # Total Minutes
    # --------------------------------

    total_seconds = (
        db.query(
            func.coalesce(
                func.sum(VoiceCall.duration),
                0
            )
        )
        .filter(
            VoiceCall.start_time >= today_start
        )
        .scalar()
    )

    total_minutes = round(
        total_seconds / 60,
        2
    )

    # --------------------------------
    # Average Duration
    # --------------------------------

    avg_duration_seconds = (
        db.query(
            func.coalesce(
                func.avg(VoiceCall.duration),
                0
            )
        )
        .filter(
            VoiceCall.start_time >= today_start
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

    avg_duration = f"{avg_minutes}m {avg_seconds}s"

    # --------------------------------
    # Revenue
    # --------------------------------

    revenue = (
        db.query(
            func.coalesce(
                func.sum(VoiceCall.revenue),
                0
            )
        )
        .filter(
            VoiceCall.start_time >= today_start
        )
        .scalar()
    )

    # --------------------------------
    # Failed Calls
    # --------------------------------

    failed_calls = (
        db.query(func.count(VoiceCall.id))
        .filter(
            VoiceCall.start_time >= today_start,
            VoiceCall.status.in_([
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





@router.get("/dashboard/daily-call-volume")
def get_daily_call_volume(
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
            func.date(VoiceCall.start_time).label("call_date"),
            func.count(VoiceCall.id).label("total_calls")
        )
        .filter(
            VoiceCall.start_time >= start_datetime
        )
        .group_by(
            func.date(VoiceCall.start_time)
        )
        .order_by(
            func.date(VoiceCall.start_time)
        )
        .all()
    )

    call_data = {
        row.call_date: row.total_calls
        for row in result
    }

    response = []

    for i in range(7):

        current_date = start_date + timedelta(days=i)

        response.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "day": current_date.strftime("%a"),
            "calls": call_data.get(
                current_date,
                0
            )
        })

    return {
        "data": response
    }




@router.get("/dashboard/revenue-by-calls")
def get_revenue_by_calls(
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
            func.date(VoiceCall.start_time).label("call_date"),
            func.coalesce(
                func.sum(VoiceCall.revenue),
                0
            ).label("total_revenue")
        )
        .filter(
            VoiceCall.start_time >= start_datetime,
            VoiceCall.status.in_(["completed", "ongoing"])
        )
        .group_by(
            func.date(VoiceCall.start_time)
        )
        .order_by(
            func.date(VoiceCall.start_time)
        )
        .all()
    )

    revenue_data = {
        row.call_date: float(row.total_revenue)
        for row in result
    }

    response = []

    for i in range(7):

        current_date = start_date + timedelta(days=i)

        response.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "day": current_date.strftime("%a"),
            "revenue": revenue_data.get(
                current_date,
                0
            )
        })

    return {
        "data": response
    }



@router.get("/dashboard/avg-duration-trend")
def get_avg_duration_trend(
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
            func.date(VoiceCall.start_time).label("call_date"),
            func.avg(VoiceCall.duration).label("avg_duration")
        )
        .filter(
            VoiceCall.start_time >= start_datetime,
            VoiceCall.status.in_(["completed", "ongoing"])
        )
        .group_by(
            func.date(VoiceCall.start_time)
        )
        .order_by(
            func.date(VoiceCall.start_time)
        )
        .all()
    )

    duration_data = {
        row.call_date: round(float(row.avg_duration), 2)
        for row in result
    }

    response = []

    for i in range(7):

        current_date = start_date + timedelta(days=i)

        response.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "day": current_date.strftime("%a"),
            "avg_duration": duration_data.get(
                current_date,
                0
            )
        })

    return {
        "data": response
    }



# @router.get("/voice-calls")
# def filter(
#     date_filter: str = Query(
#         "all",
#         description="today, last_7_days, last_30_days, all"
#     ),
#     state_id: int | None = Query(
#         None,
#         description="Filter by state ID"
#     ),
#     creator_id: int | None = Query(
#         None,
#         description="Filter by creator ID"
#     ),
#     status: str | None = Query(
#         None,
#         description="completed, missed, cancelled, ongoing"
#     ),
#     db: Session = Depends(get_db)
# ):

#     Customer = aliased(User)
#     Creator = aliased(User)

#     query = (
#         db.query(
#             VoiceCall,
#             Customer.display_name.label("customer_name"),
#             Creator.display_name.label("creator_name"),
#             State.state_name.label("state_name")
#         )
#         .join(
#             Customer,
#             VoiceCall.customer_id == Customer.id
#         )
#         .join(
#             Creator,
#             VoiceCall.creator_id == Creator.id
#         )
#         .outerjoin(
#             State,
#             Creator.state_id == State.id
#         )
#     )

#     # -------------------------
#     # DATE FILTER
#     # -------------------------

#     today = datetime.now().date()

#     if date_filter == "today":

#         start_datetime = datetime.combine(
#             today,
#             time.min
#         )

#         query = query.filter(
#             VoiceCall.start_time >= start_datetime
#         )

#     elif date_filter == "last_7_days":

#         start_date = today - timedelta(days=6)

#         start_datetime = datetime.combine(
#             start_date,
#             time.min
#         )

#         query = query.filter(
#             VoiceCall.start_time >= start_datetime
#         )

#     elif date_filter == "last_30_days":

#         start_date = today - timedelta(days=29)

#         start_datetime = datetime.combine(
#             start_date,
#             time.min
#         )

#         query = query.filter(
#             VoiceCall.start_time >= start_datetime
#         )

#     elif date_filter != "all":

#         return {
#             "error": "Invalid date_filter. Use today, last_7_days, last_30_days or all"
#         }

#     # -------------------------
#     # STATE FILTER
#     # -------------------------

#     if state_id is not None:

#         query = query.filter(
#             Creator.state_id == state_id
#         )

#     # -------------------------
#     # CREATOR FILTER
#     # -------------------------

#     if creator_id is not None:

#         query = query.filter(
#             VoiceCall.creator_id == creator_id
#         )

#     # -------------------------
#     # STATUS FILTER
#     # -------------------------

#     if status is not None:

#         query = query.filter(
#             VoiceCall.status == status
#         )

#     # -------------------------
#     # ORDER
#     # -------------------------

#     query = query.order_by(
#         VoiceCall.start_time.desc()
#     )

#     results = query.all()

#     response = []

#     for voice_call, customer_name, creator_name, state_name in results:

#         response.append({
#             "id": voice_call.id,
#             "call_id": voice_call.call_id,
#             "customer": customer_name,
#             "creator": creator_name,
#             "state": state_name,
#             "start_time": voice_call.start_time,
#             "end_time": voice_call.end_time,
#             "duration": voice_call.duration,
#             "coins": voice_call.coins,
#             "revenue": float(voice_call.revenue or 0),
#             "status": voice_call.status
#         })

#     return {
#         "count": len(response),
#         "data": response
#     }