
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query
)

from fastapi.responses import StreamingResponse

from sqlalchemy.orm import Session

from sqlalchemy import func, or_

from datetime import (
    date,
    datetime,
    time,
    timedelta
)

from typing import Optional

from decimal import Decimal

from zoneinfo import ZoneInfo

import csv
import io


from database import SessionLocal

from models.users import User

from models.voice_call import VoiceCall


# =========================================================
# EXISTING VOICE CALL ROUTER
# Keep your existing voice call endpoints.
# Add these admin APIs to the same router.
# =========================================================

router = APIRouter(
    prefix="/voice-calls",
    tags=["Voice Calls"],
)


# =========================================================
# DATABASE
# =========================================================

def get_db():

    db = SessionLocal()

    try:

        yield db

    finally:

        db.close()


# =========================================================
# TIMEZONE
# =========================================================

IST = ZoneInfo("Asia/Kolkata")


def get_today():

    return datetime.now(IST).date()


def get_utc_datetime(date_value, time_value):

    return datetime.combine(
        date_value,
        time_value,
        tzinfo=IST
    ).astimezone(
        ZoneInfo("UTC")
    )


# =========================================================
# HELPERS
# =========================================================

def user_name(user):

    if not user:

        return "Unknown User"

    for field in (
        "display_name",
        "full_name",
        "name",
        "username",
        "email",
    ):

        value = getattr(
            user,
            field,
            None
        )

        if value:

            return str(value)

    return f"User {user.id}"


# =========================================================
# GET USER
# =========================================================

def get_user(
    db: Session,
    user_id: Optional[int]
):

    if not user_id:

        return None

    return db.query(
        User
    ).filter(
        User.id == user_id
    ).first()


# =========================================================
# DURATION SECONDS
# =========================================================

def duration_seconds(
    call: VoiceCall
):

    # Calculate using start and end time
    # when both are available.

    if call.start_time and call.end_time:

        return max(
            0,
            int(
                (
                    call.end_time
                    - call.start_time
                ).total_seconds()
            )
        )

    # Your existing VoiceCall.duration
    # is assumed to be stored in HOURS.

    return max(
        0,
        int(
            float(
                call.duration or 0
            ) * 3600
        )
    )


# =========================================================
# DURATION MINUTES
# =========================================================

def duration_minutes(
    call: VoiceCall
):

    return round(
        float(
            call.duration or 0
        ) * 60,
        2
    )


# =========================================================
# FORMAT DURATION
# =========================================================

def format_duration(
    seconds: int
):

    seconds = max(
        0,
        int(seconds or 0)
    )

    hours, remainder = divmod(
        seconds,
        3600
    )

    minutes, seconds = divmod(
        remainder,
        60
    )

    if hours:

        return (
            f"{hours}h "
            f"{minutes}m"
        )

    if minutes:

        return (
            f"{minutes}m "
            f"{seconds}s"
        )

    return f"{seconds}s"


# =========================================================
# SERIALIZE VOICE CALL
# =========================================================

def serialize_voice_call(
    db: Session,
    call: VoiceCall
):

    customer = get_user(
        db,
        call.customer_id
    )

    creator = get_user(
        db,
        call.creator_id
    )

    seconds = duration_seconds(
        call
    )

    return {

        "id": call.id,

        "call_id": call.call_id,

        "customer_id": call.customer_id,

        "customer": user_name(
            customer
        ),

        "creator_id": call.creator_id,

        "creator": user_name(
            creator
        ),

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

        "duration": duration_minutes(
            call
        ),

        "duration_seconds": seconds,

        "duration_formatted": format_duration(
            seconds
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

        )

    }


# =========================================================
# SEARCH USERS
# =========================================================

def search_user_ids(
    db: Session,
    search: str
):

    conditions = []

    for field in (
        "email",
        "username",
        "display_name",
        "full_name",
        "name",
    ):

        column = getattr(
            User,
            field,
            None
        )

        if column is not None:

            try:

                conditions.append(
                    column.ilike(
                        f"%{search}%"
                    )
                )

            except AttributeError:

                pass

    if not conditions:

        return []

    rows = db.query(
        User.id
    ).filter(
        or_(*conditions)
    ).all()

    return [
        row[0]
        for row in rows
    ]


# =========================================================
# COMMON FILTERS
# =========================================================

def apply_voice_call_filters(

    db: Session,

    query,

    search: Optional[str] = None,

    status: Optional[str] = "all",

    customer_id: Optional[int] = None,

    creator_id: Optional[int] = None,

    start_date: Optional[date] = None,

    end_date: Optional[date] = None,

):

    # =====================================================
    # SEARCH CALL ID / CUSTOMER / CREATOR
    # =====================================================

    if search and search.strip():

        value = search.strip()

        matching_ids = search_user_ids(
            db,
            value
        )

        conditions = [

            VoiceCall.call_id.ilike(
                f"%{value}%"
            )

        ]

        if matching_ids:

            conditions.extend([

                VoiceCall.customer_id.in_(
                    matching_ids
                ),

                VoiceCall.creator_id.in_(
                    matching_ids
                )

            ])

        query = query.filter(
            or_(*conditions)
        )


    # =====================================================
    # STATUS FILTER
    # =====================================================

    if status and status.lower() != "all":

        query = query.filter(

            func.lower(
                VoiceCall.status
            ) == status.lower()

        )


    # =====================================================
    # CUSTOMER FILTER
    # =====================================================

    if customer_id is not None:

        query = query.filter(

            VoiceCall.customer_id
            == customer_id

        )


    # =====================================================
    # CREATOR FILTER
    # =====================================================

    if creator_id is not None:

        query = query.filter(

            VoiceCall.creator_id
            == creator_id

        )


    # =====================================================
    # START DATE FILTER
    # =====================================================

    if start_date:

        start_datetime = get_utc_datetime(
            start_date,
            time.min
        )

        query = query.filter(

            VoiceCall.created_at
            >= start_datetime

        )


    # =====================================================
    # END DATE FILTER
    # Inclusive end date
    # =====================================================

    if end_date:

        end_datetime = get_utc_datetime(

            end_date + timedelta(days=1),

            time.min

        )

        query = query.filter(

            VoiceCall.created_at
            < end_datetime

        )


    return query


# =========================================================
# CURRENT MONTH DATE HELPER
# Returns every date from the 1st of this month through today.
# =========================================================

def get_current_month_dates():

    today = get_today()

    first_day = today.replace(day=1)

    dates = []

    current_day = first_day

    while current_day <= today:

        dates.append(current_day)

        current_day += timedelta(days=1)

    return dates


# =========================================================
# 1. ADMIN DASHBOARD
# =========================================================

@router.get("/admin/dashboard")
def admin_voice_call_dashboard(

    db: Session = Depends(get_db),

):

    try:

        # =================================================
        # TODAY DATE
        # =================================================

        today = get_today()

        today_start = get_utc_datetime(
            today,
            time.min
        )

        tomorrow_start = get_utc_datetime(

            today + timedelta(days=1),

            time.min

        )

        # =================================================
        # CURRENT MONTH DATE RANGE (IST converted to UTC)
        # =================================================

        month_start_date = today.replace(day=1)

        month_start = get_utc_datetime(
            month_start_date,
            time.min
        )

        month_end = tomorrow_start

        # =================================================
        # TOTAL CALLS THIS MONTH
        # =================================================

        total_calls_this_month = db.query(
            func.count(VoiceCall.id)
        ).filter(
            VoiceCall.created_at >= month_start,
            VoiceCall.created_at < month_end
        ).scalar() or 0

        # =================================================
        # REVENUE THIS MONTH
        # =================================================

        revenue_this_month = db.query(
            func.coalesce(
                func.sum(VoiceCall.revenue),
                0
            )
        ).filter(
            VoiceCall.created_at >= month_start,
            VoiceCall.created_at < month_end
        ).scalar() or 0

        # =================================================
        # DURATION THIS MONTH
        # VoiceCall.duration is assumed to be stored in HOURS.
        # =================================================

        duration_this_month = db.query(
            func.coalesce(
                func.sum(VoiceCall.duration),
                0
            )
        ).filter(
            VoiceCall.created_at >= month_start,
            VoiceCall.created_at < month_end
        ).scalar() or 0

        total_minutes_this_month = (
            float(duration_this_month) * 60
        )

        # =================================================
        # FAILED CALLS THIS MONTH
        # =================================================

        failed_calls_this_month = db.query(
            func.count(VoiceCall.id)
        ).filter(
            VoiceCall.created_at >= month_start,
            VoiceCall.created_at < month_end,
            func.lower(VoiceCall.status).in_([
                "failed",
                "missed",
                "cancelled",
                "canceled",
                "rejected"
            ])
        ).scalar() or 0


        # =================================================
        # TOTAL CALLS TODAY
        # =================================================

        total_calls_today = db.query(

            func.count(
                VoiceCall.id
            )

        ).filter(

            VoiceCall.created_at >= today_start,

            VoiceCall.created_at < tomorrow_start

        ).scalar() or 0


        # =================================================
        # ACTIVE CALLS
        # =================================================

        active_calls = db.query(

            func.count(
                VoiceCall.id
            )

        ).filter(

            func.lower(
                VoiceCall.status
            ).in_([

                "ringing",

                "ongoing",

                "active",

                "connected"

            ])

        ).scalar() or 0


        # =================================================
        # TOTAL DURATION TODAY
        # =================================================

        total_duration = db.query(

            func.coalesce(

                func.sum(
                    VoiceCall.duration
                ),

                0

            )

        ).filter(

            VoiceCall.created_at >= today_start,

            VoiceCall.created_at < tomorrow_start

        ).scalar() or 0


        total_minutes = (

            float(
                total_duration
            ) * 60

        )


        # =================================================
        # REVENUE TODAY
        # =================================================

        revenue_today = db.query(

            func.coalesce(

                func.sum(
                    VoiceCall.revenue
                ),

                0

            )

        ).filter(

            VoiceCall.created_at >= today_start,

            VoiceCall.created_at < tomorrow_start

        ).scalar() or 0


        # =================================================
        # FAILED CALLS TODAY
        # =================================================

        failed_calls = db.query(

            func.count(
                VoiceCall.id
            )

        ).filter(

            VoiceCall.created_at >= today_start,

            VoiceCall.created_at < tomorrow_start,

            func.lower(
                VoiceCall.status
            ).in_([

                "failed",

                "missed",

                "cancelled",

                "canceled",

                "rejected"

            ])

        ).scalar() or 0


        # =================================================
        # COMPLETED CALLS TODAY
        # =================================================

        completed_calls = db.query(

            func.count(
                VoiceCall.id
            )

        ).filter(

            VoiceCall.created_at >= today_start,

            VoiceCall.created_at < tomorrow_start,

            func.lower(
                VoiceCall.status
            ).in_([

                "completed",

                "ended"

            ])

        ).scalar() or 0


        # =================================================
        # AVERAGE DURATION TODAY
        # =================================================

        completed_duration = db.query(

            func.coalesce(

                func.sum(
                    VoiceCall.duration
                ),

                0

            )

        ).filter(

            VoiceCall.created_at >= today_start,

            VoiceCall.created_at < tomorrow_start,

            func.lower(
                VoiceCall.status
            ).in_([

                "completed",

                "ended"

            ])

        ).scalar() or 0


        if completed_calls > 0:

            average_duration = (

                float(
                    completed_duration
                ) * 60

            ) / completed_calls

        else:

            average_duration = 0


        # =================================================
        # TOTAL CALLS ALL TIME
        # =================================================

        total_calls = db.query(

            func.count(
                VoiceCall.id
            )

        ).scalar() or 0


        # =================================================
        # TOTAL REVENUE ALL TIME
        # =================================================

        total_revenue = db.query(

            func.coalesce(

                func.sum(
                    VoiceCall.revenue
                ),

                0

            )

        ).scalar() or 0


        # =================================================
        # TOTAL MINUTES ALL TIME
        # =================================================

        total_duration_all = db.query(

            func.coalesce(

                func.sum(
                    VoiceCall.duration
                ),

                0

            )

        ).scalar() or 0


        # =================================================
        # AVERAGE DURATION ALL TIME
        # =================================================

        completed_count_all = db.query(

            func.count(
                VoiceCall.id
            )

        ).filter(

            func.lower(
                VoiceCall.status
            ).in_([

                "completed",

                "ended"

            ])

        ).scalar() or 0


        completed_duration_all = db.query(

            func.coalesce(

                func.sum(
                    VoiceCall.duration
                ),

                0

            )

        ).filter(

            func.lower(
                VoiceCall.status
            ).in_([

                "completed",

                "ended"

            ])

        ).scalar() or 0


        if completed_count_all:

            average_duration_all = (

                float(
                    completed_duration_all
                ) * 60

            ) / completed_count_all

        else:

            average_duration_all = 0


        # =================================================
        # RESPONSE
        # =================================================

        return {

            "status_code": 200,

            "message": (
                "Voice call dashboard fetched successfully"
            ),

            "data": {

                "total_calls_today": int(
                    total_calls_today
                ),

                "active_now": int(
                    active_calls
                ),

                "total_minutes": round(
                    total_minutes,
                    2
                ),

                "average_duration_minutes": round(
                    average_duration,
                    2
                ),

                "revenue": round(
                    float(revenue_today),
                    2
                ),

                "failed_calls": int(
                    failed_calls
                ),

                "total_calls_this_month": int(
                    total_calls_this_month
                ),

                "revenue_this_month": round(
                    float(revenue_this_month),
                    2
                ),

                "total_minutes_this_month": round(
                    total_minutes_this_month,
                    2
                ),

                "failed_calls_this_month": int(
                    failed_calls_this_month
                ),

                "total_calls": int(
                    total_calls
                ),

                "total_revenue": round(
                    float(total_revenue),
                    2
                ),

                "total_minutes_all_time": round(
                    float(total_duration_all) * 60,
                    2
                ),

                "average_duration_all_time": round(
                    average_duration_all,
                    2
                )

            }

        }


    except Exception as e:

        print(
            "Voice call dashboard error:",
            str(e)
        )

        raise HTTPException(

            status_code=500,

            detail="Failed to fetch voice call dashboard"

        )


# =========================================================
# 2. VOICE CALL REVENUE TREND
# =========================================================

@router.get("/admin/revenue-trend")
def admin_voice_call_revenue_trend(

    db: Session = Depends(get_db),

):

    try:

        result = []

        for day in get_current_month_dates():

            start = get_utc_datetime(
                day,
                time.min
            )

            end = get_utc_datetime(

                day + timedelta(days=1),

                time.min

            )


            revenue = db.query(

                func.coalesce(

                    func.sum(
                        VoiceCall.revenue
                    ),

                    0

                )

            ).filter(

                VoiceCall.created_at >= start,

                VoiceCall.created_at < end

            ).scalar() or 0


            result.append({

                "date": day.isoformat(),

                "day": day.strftime("%a"),

                "revenue": round(
                    float(revenue),
                    2
                )

            })


        return {

            "status_code": 200,

            "message": (
                "Voice call revenue trend fetched successfully"
            ),

            "data": result

        }


    except Exception as e:

        print(
            "Voice call revenue trend error:",
            str(e)
        )

        raise HTTPException(

            status_code=500,

            detail="Failed to fetch revenue trend"

        )


# =========================================================
# 3. VOICE CALL USAGE TREND
# =========================================================

@router.get("/admin/usage-trend")
def admin_voice_call_usage_trend(

    db: Session = Depends(get_db),

):

    try:

        result = []

        for day in get_current_month_dates():

            start = get_utc_datetime(
                day,
                time.min
            )

            end = get_utc_datetime(

                day + timedelta(days=1),

                time.min

            )


            duration = db.query(

                func.coalesce(

                    func.sum(
                        VoiceCall.duration
                    ),

                    0

                )

            ).filter(

                VoiceCall.created_at >= start,

                VoiceCall.created_at < end

            ).scalar() or 0


            result.append({

                "date": day.isoformat(),

                "day": day.strftime("%a"),

                "minutes": round(

                    float(duration) * 60,

                    2

                )

            })


        return {

            "status_code": 200,

            "message": (
                "Voice call usage trend fetched successfully"
            ),

            "data": result

        }


    except Exception as e:

        print(
            "Voice call usage trend error:",
            str(e)
        )

        raise HTTPException(

            status_code=500,

            detail="Failed to fetch usage trend"

        )


# =========================================================
# 4. VOICE CALL AVERAGE DURATION TREND
# =========================================================

@router.get("/admin/average-duration-trend")
def admin_voice_call_average_duration_trend(

    db: Session = Depends(get_db),

):

    try:

        result = []

        for day in get_current_month_dates():

            start = get_utc_datetime(
                day,
                time.min
            )

            end = get_utc_datetime(

                day + timedelta(days=1),

                time.min

            )


            completed_calls = db.query(

                func.count(
                    VoiceCall.id
                )

            ).filter(

                VoiceCall.created_at >= start,

                VoiceCall.created_at < end,

                func.lower(
                    VoiceCall.status
                ).in_([

                    "completed",

                    "ended"

                ])

            ).scalar() or 0


            duration = db.query(

                func.coalesce(

                    func.sum(
                        VoiceCall.duration
                    ),

                    0

                )

            ).filter(

                VoiceCall.created_at >= start,

                VoiceCall.created_at < end,

                func.lower(
                    VoiceCall.status
                ).in_([

                    "completed",

                    "ended"

                ])

            ).scalar() or 0


            if completed_calls:

                average_minutes = (

                    float(duration) * 60

                ) / completed_calls

            else:

                average_minutes = 0


            result.append({

                "date": day.isoformat(),

                "day": day.strftime("%a"),

                "average_minutes": round(
                    average_minutes,
                    2
                )

            })


        return {

            "status_code": 200,

            "message": (
                "Average duration trend fetched successfully"
            ),

            "data": result

        }


    except Exception as e:

        print(
            "Average duration trend error:",
            str(e)
        )

        raise HTTPException(

            status_code=500,

            detail="Failed to fetch average duration trend"

        )


# =========================================================
# 5. CREATOR PERFORMANCE
# =========================================================

@router.get("/admin/creator-performance")
def admin_voice_call_creator_performance(

    db: Session = Depends(get_db),

    limit: int = Query(
        10,
        ge=1,
        le=100
    ),

):

    try:

        rows = db.query(

            VoiceCall.creator_id,

            func.count(
                VoiceCall.id
            ).label(
                "total_calls"
            ),

            func.coalesce(

                func.sum(
                    VoiceCall.duration
                ),

                0

            ).label(
                "total_duration"
            ),

            func.coalesce(

                func.sum(
                    VoiceCall.revenue
                ),

                0

            ).label(
                "total_revenue"
            ),

            func.coalesce(

                func.sum(
                    VoiceCall.coins
                ),

                0

            ).label(
                "total_coins"
            )

        ).group_by(

            VoiceCall.creator_id

        ).order_by(

            func.sum(
                VoiceCall.revenue
            ).desc()

        ).limit(

            limit

        ).all()


        result = []

        for row in rows:

            creator = get_user(
                db,
                row.creator_id
            )


            result.append({

                "creator_id": row.creator_id,

                "creator": user_name(
                    creator
                ),

                "total_calls": int(
                    row.total_calls or 0
                ),

                "total_minutes": round(

                    float(
                        row.total_duration or 0
                    ) * 60,

                    2

                ),

                "total_revenue": round(

                    float(
                        row.total_revenue or 0
                    ),

                    2

                ),

                "total_coins": int(
                    row.total_coins or 0
                )

            })


        return {

            "status_code": 200,

            "message": (
                "Creator performance fetched successfully"
            ),

            "data": result

        }


    except Exception as e:

        print(
            "Creator performance error:",
            str(e)
        )

        raise HTTPException(

            status_code=500,

            detail="Failed to fetch creator performance"

        )


# =========================================================
# 6. VOICE CALL LIST
# Search + filters + pagination
# =========================================================

@router.get("/admin/admin-list")
def admin_voice_call_list(

    db: Session = Depends(get_db),

    search: Optional[str] = None,

    status: Optional[str] = "all",

    customer_id: Optional[int] = None,

    creator_id: Optional[int] = None,

    start_date: Optional[date] = None,

    end_date: Optional[date] = None,

    page: int = Query(
        1,
        ge=1
    ),

    limit: int = Query(
        20,
        ge=1,
        le=100
    ),

):

    try:

        query = db.query(
            VoiceCall
        )


        query = apply_voice_call_filters(

            db=db,

            query=query,

            search=search,

            status=status,

            customer_id=customer_id,

            creator_id=creator_id,

            start_date=start_date,

            end_date=end_date

        )


        total = query.count()


        calls = query.order_by(

            VoiceCall.created_at.desc()

        ).offset(

            (page - 1) * limit

        ).limit(

            limit

        ).all()


        return {

            "status_code": 200,

            "message": (
                "Voice calls fetched successfully"
            ),

            "total": total,

            "page": page,

            "limit": limit,

            "total_pages": (

                (total + limit - 1) // limit

            ),

            "data": [

                serialize_voice_call(
                    db,
                    call
                )

                for call in calls

            ]

        }


    except Exception as e:

        print(
            "Voice call list error:",
            str(e)
        )

        raise HTTPException(

            status_code=500,

            detail="Failed to fetch voice calls"

        )


# =========================================================
# 7. VOICE CALL DETAILS
# =========================================================

@router.get("/admin/admin-list/{call_id}")
def admin_voice_call_details(

    call_id: str,

    db: Session = Depends(get_db),

):

    try:

        call = db.query(

            VoiceCall

        ).filter(

            VoiceCall.call_id == call_id

        ).first()


        if not call:

            raise HTTPException(

                status_code=404,

                detail="Voice call not found"

            )


        return {

            "status_code": 200,

            "message": (
                "Voice call details fetched successfully"
            ),

            "data": serialize_voice_call(

                db,

                call

            )

        }


    except HTTPException:

        raise


    except Exception as e:

        print(
            "Voice call details error:",
            str(e)
        )

        raise HTTPException(

            status_code=500,

            detail="Failed to fetch voice call details"

        )


# =========================================================
# 8. VOICE CALL CSV EXPORT
# =========================================================

@router.get("/admin/admin-export")
def admin_voice_call_export(

    db: Session = Depends(get_db),

    search: Optional[str] = None,

    status: Optional[str] = "all",

    customer_id: Optional[int] = None,

    creator_id: Optional[int] = None,

    start_date: Optional[date] = None,

    end_date: Optional[date] = None,

):

    try:

        query = db.query(
            VoiceCall
        )


        query = apply_voice_call_filters(

            db=db,

            query=query,

            search=search,

            status=status,

            customer_id=customer_id,

            creator_id=creator_id,

            start_date=start_date,

            end_date=end_date

        )


        calls = query.order_by(

            VoiceCall.created_at.desc()

        ).all()


        output = io.StringIO()

        writer = csv.writer(
            output
        )


        writer.writerow([

            "Call ID",

            "Customer",

            "Creator",

            "Start Time",

            "End Time",

            "Duration",

            "Coins",

            "Revenue",

            "Status",

            "Free Call"

        ])


        for call in calls:

            item = serialize_voice_call(

                db,

                call

            )


            writer.writerow([

                item["call_id"],

                item["customer"],

                item["creator"],

                item["start_time"],

                item["end_time"],

                item["duration_formatted"],

                item["coins"],

                item["revenue"],

                item["status"],

                item["is_free_call"]

            ])


        output.seek(0)


        return StreamingResponse(

            iter([

                output.getvalue()

            ]),

            media_type="text/csv",

            headers={

                "Content-Disposition":

                "attachment; filename=voice_calls.csv"

            }

        )


    except Exception as e:

        print(
            "Voice call export error:",
            str(e)
        )

        raise HTTPException(

            status_code=500,

            detail="Failed to export voice calls"

        )
