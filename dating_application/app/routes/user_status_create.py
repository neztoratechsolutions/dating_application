from fastapi import APIRouter, Depends, HTTPException, status,Query
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.users import User
from app.models.user_status import UserStatus
from app.schemas.user_status_create import UserStatusCreate

router = APIRouter(
    prefix="/user-status",
    tags=["User Status"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "/",
    status_code=status.HTTP_200_OK
)
def create_or_update_user_status(
    data: UserStatusCreate,
    db: Session = Depends(get_db)
):
    # Check if user exists
    user = db.query(User).filter(User.id == data.user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if status already exists
    user_status = (
        db.query(UserStatus)
        .filter(UserStatus.user_id == data.user_id)
        .first()
    )

    if user_status:
        # Update existing status
        user_status.is_online = data.is_online
        message = "User status updated successfully"
    else:
        # Create new status
        user_status = UserStatus(
            user_id=data.user_id,
            is_online=data.is_online
        )
        db.add(user_status)
        message = "User status created successfully"

    db.commit()
    db.refresh(user_status)

    return {
        "status_code": status.HTTP_200_OK,
        "message": message,
        "data": {
            "id": user_status.id,
            "user_id": user_status.user_id,
            "is_online": user_status.is_online,
        },
    }

#-----------------Get Online status-------------#
@router.get(
    "/online-users",
    status_code=status.HTTP_200_OK
)
def get_online_users(
    role: str | None = Query(
        None,
        description="Filter by role (creator or customer)"
    ),
    state_id: int | None = Query(
        None,
        description="Filter by State ID"
    ),
    is_online: bool | None = Query(
        None,
        description="Filter by online status (true/false)"
    ),
    db: Session = Depends(get_db)
):
    query = (
    db.query(User, UserStatus)
    .outerjoin(UserStatus, User.id == UserStatus.user_id)
    .filter(User.role != "admin")   # Exclude admins
)

    # Filter by role
    if role:
        query = query.filter(User.role == role)

    # Filter by state
    if state_id:
        query = query.filter(User.state_id == state_id)

    users = query.all()

    data = []

    for user, status_obj in users:
        online_status = status_obj.is_online if status_obj else False

        # Filter by online/offline status
        if is_online is not None and online_status != is_online:
            continue

        data.append({
            "id": user.id,
            "display_name": user.display_name,
            "email": user.email,
            "phone": user.phone,
            "role": user.role,
            "state_id": user.state_id,
            "profile_photo": user.profile_photo,
            "is_online": online_status,
        })

    return {
        "status_code": status.HTTP_200_OK,
        "message": "Users fetched successfully",
        "count": len(data),
        "data": data,
    }