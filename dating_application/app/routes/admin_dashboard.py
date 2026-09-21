# from datetime import date, datetime, timedelta

# from fastapi import APIRouter, Depends, Query
# from sqlalchemy import func
# from sqlalchemy.orm import Session

# from app.database import SessionLocal
# from app.models.users import User
# from app.models.user_status import UserStatus

# router = APIRouter(
#     prefix="/admin/dashboard",
#     tags=["Admin Dashboard"]
# )


# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()


# @router.get("/summary")
# def get_dashboard_summary(
#     db: Session = Depends(get_db)
# ):
#     # Total users excluding admin
#     total_users = db.query(
#         func.count(User.id)
#     ).filter(
#         User.role != "admin"
#     ).scalar() or 0

#     # Total creators
#     total_creators = db.query(
#         func.count(User.id)
#     ).filter(
#         User.role == "creator"
#     ).scalar() or 0

#     # Live users
#     live_now = db.query(
#         func.count(UserStatus.id)
#     ).filter(
#         UserStatus.is_online == True
#     ).scalar() or 0

#     return {
#         "total_users": total_users,
#         "total_creators": total_creators,
#         "live_now": live_now,
#         "revenue_today": 0,
#         "pending_kyc": 0,
#         "pending_withdrawals": 0
#     }


# @router.get("/revenue-trend")
# def get_revenue_trend(
#     days: int = Query(7, ge=1, le=31),
#     db: Session = Depends(get_db)
# ):
#     today = date.today()
#     start_date = today - timedelta(days=days - 1)

#     result = []

#     for i in range(days):
#         current_date = start_date + timedelta(days=i)

#         result.append({
#             "date": current_date.isoformat(),
#             "day": current_date.strftime("%a"),
#             "revenue": 0
#         })

#     return result


# @router.get("/top-creators")
# def get_top_creators(
#     limit: int = Query(5, ge=1, le=20),
#     db: Session = Depends(get_db)
# ):
#     creators = db.query(
#         User
#     ).filter(
#         User.role == "creator"
#     ).limit(limit).all()

#     return [
#         {
#             "rank": index + 1,
#             "creator_id": creator.id,
#             "name": creator.display_name,
#             "state_id": creator.state_id,
#             "profile_photo": creator.profile_photo,
#             "earnings_today": 0
#         }
#         for index, creator in enumerate(creators)
#     ]