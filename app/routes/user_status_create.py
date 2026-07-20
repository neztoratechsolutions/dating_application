from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import SessionLocal
from models.users import User
from models.user_status import UserStatus
from schemas.user_status_create import UserStatusCreate

router = APIRouter(prefix="/user-status",tags=["User Status"])


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
def create_user_status(
    data: UserStatusCreate,
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(
        User.id == data.user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    existing_status = db.query(UserStatus).filter(
        UserStatus.user_id == data.user_id
    ).first()

    if existing_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User status already exists"
        )

    user_status = UserStatus(
        user_id=data.user_id,
        is_online=data.is_online
    )

    db.add(user_status)
    db.commit()
    db.refresh(user_status)

    return {
        "status_code": 200,
        "message": "User status created successfully",
        "data": {
            "id": user_status.id,
            "user_id": user_status.user_id,
            "is_online": user_status.is_online
        }
    }