from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.settings import Setting
from app.models.users import User
from app.schemas.settings import SettingCreate, SettingResponse

router = APIRouter(prefix="/settings",tags=["Settings"])


@router.post(
    "/",
    response_model=SettingResponse,
    status_code=status.HTTP_201_CREATED
)
def create_setting(
    setting: SettingCreate,
    user_id: int,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    existing_setting = (
        db.query(Setting)
        .filter(Setting.user_id == user_id)
        .first()
    )

    if existing_setting:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Setting already exists for this user"
        )

    new_setting = Setting(
        user_id=user_id,
        availability_hour=setting.availability_hour
    )

    db.add(new_setting)
    db.commit()
    db.refresh(new_setting)

    return new_setting


@router.get(
    "/{user_id}",
    response_model=SettingResponse,
    status_code=status.HTTP_200_OK
)
def get_setting(
    user_id: int,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    setting = (
        db.query(Setting)
        .filter(Setting.user_id == user_id)
        .first()
    )

    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setting not found"
        )

    return setting



@router.get(
    "/",
    response_model=list[SettingResponse],
    status_code=status.HTTP_200_OK
)
def get_all_settings(
    db: Session = Depends(get_db)
):
    settings = db.query(Setting).all()

    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No settings found"
        )

    return settings



@router.put(
    "/{user_id}",
    response_model=SettingResponse,
    status_code=status.HTTP_200_OK
)
def update_setting(
    user_id: int,
    setting_data: SettingCreate,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    setting = (
        db.query(Setting)
        .filter(Setting.user_id == user_id)
        .first()
    )

    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setting not found"
        )

    setting.availability_hour = setting_data.availability_hour

    db.commit()
    db.refresh(setting)

    return setting


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_200_OK
)
def delete_setting(
    user_id: int,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    setting = (
        db.query(Setting)
        .filter(Setting.user_id == user_id)
        .first()
    )

    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setting not found"
        )

    db.delete(setting)
    db.commit()

    return {
        "status": "success",
        "message": "Setting deleted successfully"
    }