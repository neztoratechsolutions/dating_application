# from fastapi import APIRouter, Depends, HTTPException, Query
# from fastapi.responses import StreamingResponse
# from sqlalchemy.orm import Session
# from sqlalchemy import func, or_
# from datetime import date, datetime, time, timedelta
# from typing import Optional
# from decimal import Decimal
# import csv
# import io

# from database import SessionLocal
# from models.users import User
# from models.video_call import VideoCall


# # =========================================================
# # EXISTING VIDEO CALL ROUTER
# # Keep your existing router and endpoints.
# # Add these APIs to the same router.
# # =========================================================

# router = APIRouter(
#     prefix="/video-calls",
#     tags=["Video Calls"],
# )


# # =========================================================
# # DATABASE
# # =========================================================

# def get_db():
#     db = SessionLocal()

#     try:
#         yield db
#     finally:
#         db.close()


# # =========================================================
# # HELPERS
# # =========================================================

# def user_name(user):
#     if not user:
#         return "Unknown User"

#     for field in (
#         "display_name",
#         "full_name",
#         "name",
#         "username",
#         "email",
#     ):
#         value = getattr(user, field, None)

#         if value:
#             return str(value)

#     return f"User {user.id}"


# def get_user(db: Session, user_id: Optional[int]):
#     if not user_id:
#         return None

#     return db.query(User).filter(
#         User.id == user_id
#     ).first()


# def duration_seconds(call: VideoCall) -> int:

#     if call.start_time and call.end_time:

#         return max(
#             0,
#             int(
#                 (
#                     call.end_time - call.start_time
#                 ).total_seconds()
#             ),
#         )

#     # Existing model stores duration in HOURS.
#     return max(
#         0,
#         int(float(call.duration or 0) * 3600),
#     )


# def duration_minutes(call: VideoCall) -> float:

#     return round(
#         float(call.duration or 0) * 60,
#         2,
#     )


# def format_duration(seconds: int) -> str:

#     seconds = max(0, int(seconds or 0))

#     hours, remainder = divmod(seconds, 3600)

#     minutes, seconds = divmod(remainder, 60)

#     if hours:
#         return f"{hours}h {minutes}m"

#     if minutes:
#         return f"{minutes}m {seconds}s"

#     return f"{seconds}s"


# def serialize_video_call(
#     db: Session,
#     call: VideoCall,
# ):

#     customer = get_user(
#         db,
#         call.customer_id,
#     )

#     creator = get_user(
#         db,
#         call.creator_id,
#     )

#     seconds = duration_seconds(call)

#     return {
#         "id": call.id,

#         "video_call_id": call.video_call_id,

#         "customer_id": call.customer_id,

#         "customer": user_name(customer),

#         "creator_id": call.creator_id,

#         "creator": user_name(creator),

#         "caller_id": call.caller_id,

#         "receiver_id": call.receiver_id,

#         "start_time": (
#             call.start_time.isoformat()
#             if call.start_time
#             else None
#         ),

#         "end_time": (
#             call.end_time.isoformat()
#             if call.end_time
#             else None
#         ),

#         "duration": duration_minutes(call),

#         "duration_seconds": seconds,

#         "duration_formatted": format_duration(
#             seconds
#         ),

#         "coins": int(call.coins or 0),

#         "revenue": float(call.revenue or 0),

#         "status": call.status,

#         "is_free_call": bool(
#             call.is_free_call
#         ),

#         "created_at": (
#             call.created_at.isoformat()
#             if call.created_at
#             else None
#         ),

#         "updated_at": (
#             call.updated_at.isoformat()
#             if call.updated_at
#             else None
#         ),
#     }


# # =========================================================
# # SEARCH USERS
# # =========================================================

# def search_user_ids(
#     db: Session,
#     search: str,
# ):

#     conditions = []

#     for field in (
#         "email",
#         "username",
#         "display_name",
#         "full_name",
#         "name",
#     ):

#         column = getattr(
#             User,
#             field,
#             None,
#         )

#         if column is not None:

#             try:

#                 conditions.append(
#                     column.ilike(
#                         f"%{search}%"
#                     )
#                 )

#             except AttributeError:
#                 pass

#     if not conditions:
#         return []

#     rows = db.query(
#         User.id
#     ).filter(
#         or_(*conditions)
#     ).all()

#     return [
#         row[0]
#         for row in rows
#     ]


# # =========================================================
# # COMMON FILTERS
# # =========================================================

# def apply_video_call_filters(
#     db: Session,
#     query,
#     search: Optional[str] = None,
#     status: Optional[str] = "all",
#     customer_id: Optional[int] = None,
#     creator_id: Optional[int] = None,
#     start_date: Optional[date] = None,
#     end_date: Optional[date] = None,
# ):

#     # Search call ID, customer, creator.
#     if search and search.strip():

#         value = search.strip()

#         matching_ids = search_user_ids(
#             db,
#             value,
#         )

#         conditions = [
#             VideoCall.video_call_id.ilike(
#                 f"%{value}%"
#             )
#         ]

#         if matching_ids:

#             conditions.extend([
#                 VideoCall.customer_id.in_(
#                     matching_ids
#                 ),

#                 VideoCall.creator_id.in_(
#                     matching_ids
#                 ),
#             ])

#         query = query.filter(
#             or_(*conditions)
#         )

#     # Status filter.
#     if status and status.lower() != "all":

#         query = query.filter(
#             func.lower(VideoCall.status)
#             == status.lower()
#         )

#     # Customer filter.
#     if customer_id is not None:

#         query = query.filter(
#             VideoCall.customer_id
#             == customer_id
#         )

#     # Creator filter.
#     if creator_id is not None:

#         query = query.filter(
#             VideoCall.creator_id
#             == creator_id
#         )

#     # Start date.
#     if start_date:

#         query = query.filter(
#             VideoCall.created_at
#             >= datetime.combine(
#                 start_date,
#                 time.min,
#             )
#         )

#     # End date inclusive.
#     if end_date:

#         query = query.filter(
#             VideoCall.created_at
#             < datetime.combine(
#                 end_date + timedelta(days=1),
#                 time.min,
#             )
#         )

#     return query


# # =========================================================
# # WEEK DATE HELPER
# # =========================================================

# def get_current_week_dates():

#     today = date.today()

#     monday = today - timedelta(
#         days=today.weekday()
#     )

#     return [
#         monday + timedelta(days=i)
#         for i in range(7)
#     ]


# # =========================================================
# # 1. ADMIN DASHBOARD
# # =========================================================

# @router.get("/admin/dashboard")
# def admin_video_call_dashboard(
#     db: Session = Depends(get_db),
# ):

#     # Total video calls.
#     total_calls = db.query(
#         func.count(VideoCall.id)
#     ).scalar() or 0

#     # Active calls.
#     active_calls = db.query(
#         func.count(VideoCall.id)
#     ).filter(
#         func.lower(VideoCall.status).in_([
#             "ringing",
#             "ongoing",
#             "active",
#             "connected",
#         ])
#     ).scalar() or 0

#     # Total completed duration.
#     total_duration = db.query(
#         func.coalesce(
#             func.sum(VideoCall.duration),
#             0,
#         )
#     ).filter(
#         func.lower(VideoCall.status)
#         == "completed"
#     ).scalar() or 0

#     # Total revenue.
#     total_revenue = db.query(
#         func.coalesce(
#             func.sum(VideoCall.revenue),
#             0,
#         )
#     ).scalar() or 0

#     # Average completed duration.
#     average_duration = db.query(
#         func.coalesce(
#             func.avg(VideoCall.duration),
#             0,
#         )
#     ).filter(
#         func.lower(VideoCall.status)
#         == "completed"
#     ).scalar() or 0

#     # Failed / missed / cancelled calls.
#     failed_calls = db.query(
#         func.count(VideoCall.id)
#     ).filter(
#         func.lower(VideoCall.status).in_([
#             "failed",
#             "missed",
#             "cancelled",
#             "canceled",
#             "rejected",
#         ])
#     ).scalar() or 0

#     return {
#         "status_code": 200,

#         "message": "Video call dashboard fetched successfully",

#         "data": {
#             "total_video_calls": total_calls,

#             "active_now": active_calls,

#             "total_minutes": round(
#                 float(total_duration) * 60,
#                 2,
#             ),

#             "revenue": round(
#                 float(total_revenue),
#                 2,
#             ),

#             "average_duration_minutes": round(
#                 float(average_duration) * 60,
#                 2,
#             ),

#             "failed_calls": failed_calls,
#         },
#     }


# # =========================================================
# # 2. VIDEO CALL REVENUE TREND
# # =========================================================

# @router.get("/admin/revenue-trend")
# def admin_video_call_revenue_trend(
#     db: Session = Depends(get_db),
# ):

#     result = []

#     for day in get_current_week_dates():

#         start = datetime.combine(
#             day,
#             time.min,
#         )

#         end = start + timedelta(days=1)

#         revenue = db.query(
#             func.coalesce(
#                 func.sum(VideoCall.revenue),
#                 0,
#             )
#         ).filter(
#             VideoCall.created_at >= start,

#             VideoCall.created_at < end,
#         ).scalar() or 0

#         result.append({

#             "date": day.isoformat(),

#             "day": day.strftime("%a"),

#             "revenue": round(
#                 float(revenue),
#                 2,
#             ),

#         })

#     return {
#         "status_code": 200,

#         "message": "Revenue trend fetched successfully",

#         "data": result,
#     }


# # =========================================================
# # 3. VIDEO CALL USAGE TREND
# # =========================================================

# @router.get("/admin/usage-trend")
# def admin_video_call_usage_trend(
#     db: Session = Depends(get_db),
# ):

#     result = []

#     for day in get_current_week_dates():

#         start = datetime.combine(
#             day,
#             time.min,
#         )

#         end = start + timedelta(days=1)

#         duration = db.query(
#             func.coalesce(
#                 func.sum(VideoCall.duration),
#                 0,
#             )
#         ).filter(
#             VideoCall.created_at >= start,

#             VideoCall.created_at < end,
#         ).scalar() or 0

#         result.append({

#             "date": day.isoformat(),

#             "day": day.strftime("%a"),

#             # Existing duration column is in hours.
#             "minutes": round(
#                 float(duration) * 60,
#                 2,
#             ),

#         })

#     return {
#         "status_code": 200,

#         "message": "Usage trend fetched successfully",

#         "data": result,
#     }


# # =========================================================
# # 4. CREATOR PERFORMANCE
# # =========================================================

# @router.get("/admin/creator-performance")
# def admin_creator_performance(
#     db: Session = Depends(get_db),

#     limit: int = Query(
#         10,
#         ge=1,
#         le=100,
#     ),
# ):

#     rows = db.query(

#         VideoCall.creator_id,

#         func.count(
#             VideoCall.id
#         ).label("total_calls"),

#         func.coalesce(
#             func.sum(VideoCall.duration),
#             0,
#         ).label("total_duration"),

#         func.coalesce(
#             func.sum(VideoCall.revenue),
#             0,
#         ).label("total_revenue"),

#         func.coalesce(
#             func.sum(VideoCall.coins),
#             0,
#         ).label("total_coins"),

#     ).group_by(
#         VideoCall.creator_id
#     ).order_by(
#         func.sum(VideoCall.revenue).desc()
#     ).limit(
#         limit
#     ).all()

#     result = []

#     for row in rows:

#         creator = get_user(
#             db,
#             row.creator_id,
#         )

#         result.append({

#             "creator_id": row.creator_id,

#             "creator": user_name(creator),

#             "total_calls": int(
#                 row.total_calls or 0
#             ),

#             "total_minutes": round(
#                 float(row.total_duration or 0) * 60,
#                 2,
#             ),

#             "total_revenue": round(
#                 float(row.total_revenue or 0),
#                 2,
#             ),

#             "total_coins": int(
#                 row.total_coins or 0
#             ),

#         })

#     return {
#         "status_code": 200,

#         "message": "Creator performance fetched successfully",

#         "data": result,
#     }


# # =========================================================
# # 5. VIDEO CALL LIST
# # Search + filters + pagination
# # =========================================================

# @router.get("/admin/admin-list")
# def admin_video_call_list(

#     db: Session = Depends(get_db),

#     search: Optional[str] = None,

#     status: Optional[str] = "all",

#     customer_id: Optional[int] = None,

#     creator_id: Optional[int] = None,

#     start_date: Optional[date] = None,

#     end_date: Optional[date] = None,

#     page: int = Query(
#         1,
#         ge=1,
#     ),

#     limit: int = Query(
#         20,
#         ge=1,
#         le=100,
#     ),

# ):

#     query = db.query(VideoCall)

#     query = apply_video_call_filters(
#         db=db,
#         query=query,
#         search=search,
#         status=status,
#         customer_id=customer_id,
#         creator_id=creator_id,
#         start_date=start_date,
#         end_date=end_date,
#     )

#     total = query.count()

#     calls = query.order_by(
#         VideoCall.created_at.desc()
#     ).offset(
#         (page - 1) * limit
#     ).limit(
#         limit
#     ).all()

#     return {

#         "status_code": 200,

#         "message": "Video calls fetched successfully",

#         "total": total,

#         "page": page,

#         "limit": limit,

#         "total_pages": (
#             (total + limit - 1) // limit
#         ),

#         "data": [
#             serialize_video_call(db, call)
#             for call in calls
#         ],

#     }


# # =========================================================
# # 6. VIDEO CALL DETAILS
# # =========================================================

# @router.get("/admin/admin-list/{video_call_id}")
# def admin_video_call_details(

#     video_call_id: str,

#     db: Session = Depends(get_db),

# ):

#     call = db.query(
#         VideoCall
#     ).filter(
#         VideoCall.video_call_id
#         == video_call_id
#     ).first()

#     if not call:

#         raise HTTPException(
#             status_code=404,
#             detail="Video call not found",
#         )

#     return {

#         "status_code": 200,

#         "message": "Video call details fetched successfully",

#         "data": serialize_video_call(
#             db,
#             call,
#         ),

#     }


# # =========================================================
# # 7. VIDEO CALL CSV EXPORT
# # =========================================================

# @router.get("/admin/admin-export")
# def admin_video_call_export(

#     db: Session = Depends(get_db),

#     search: Optional[str] = None,

#     status: Optional[str] = "all",

#     customer_id: Optional[int] = None,

#     creator_id: Optional[int] = None,

#     start_date: Optional[date] = None,

#     end_date: Optional[date] = None,

# ):

#     query = db.query(VideoCall)

#     query = apply_video_call_filters(
#         db=db,
#         query=query,
#         search=search,
#         status=status,
#         customer_id=customer_id,
#         creator_id=creator_id,
#         start_date=start_date,
#         end_date=end_date,
#     )

#     calls = query.order_by(
#         VideoCall.created_at.desc()
#     ).all()

#     output = io.StringIO()

#     writer = csv.writer(output)

#     writer.writerow([

#         "Video Call ID",

#         "Customer",

#         "Creator",

#         "Start Time",

#         "End Time",

#         "Duration",

#         "Coins",

#         "Revenue",

#         "Status",

#     ])

#     for call in calls:

#         item = serialize_video_call(
#             db,
#             call,
#         )

#         writer.writerow([

#             item["video_call_id"],

#             item["customer"],

#             item["creator"],

#             item["start_time"],

#             item["end_time"],

#             item["duration_formatted"],

#             item["coins"],

#             item["revenue"],

#             item["status"],

#         ])

#     output.seek(0)

#     return StreamingResponse(

#         iter([
#             output.getvalue()
#         ]),

#         media_type="text/csv",

#         headers={

#             "Content-Disposition":
#             "attachment; filename=video_calls.csv"

#         },

#     )