import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import SessionLocal
from fastapi import Form, File, UploadFile
from models.users import User
from models.state import State
from schemas.users import (UserCreate,UserStatusUpdate,UserUpdate,UserResponse)
from security import (hash_password,generate_referral_code)
from fastapi import Request

router = APIRouter(prefix="/users",tags=["Users"])


def get_db():
    db = SessionLocal()
    try:
        yield  db
    finally:
        db.close()


@router.post("/", response_model=UserResponse)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db)
):

    existing_user = db.query(User).filter(
        User.email == user.email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already exists"
        )

    new_user = User(
        email=user.email,
        phone=user.phone,
        password=hash_password(user.password),
        display_name=user.display_name,
        bio=user.bio,
        description=user.description,
        state_id=user.state_id,
        profile_photo=user.profile_photo,
        referral_code=generate_referral_code()
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.get("/", response_model=list[UserResponse])
def get_users(
    db: Session = Depends(get_db)
):
    return db.query(User).all()


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return user



@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    display_name: str | None = Form(None),
    bio: str | None = Form(None),
    profile_photo: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if display_name is not None:
        user.display_name = display_name

    if bio is not None:
        user.bio = bio

    if profile_photo is not None and profile_photo.filename:
        os.makedirs("uploads", exist_ok=True)
        file_path = os.path.join("uploads", profile_photo.filename)

        with open(file_path, "wb") as buffer:
            buffer.write(await profile_photo.read())

        user.profile_photo = file_path

    db.commit()
    db.refresh(user)

    return user




@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    db.delete(user)
    db.commit()

    return {
        "message": "User deleted successfully"
    }





@router.patch("/{user_id}/status")
def update_user_status(
    user_id: int,
    data: UserStatusUpdate,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    user.status = data.status

    db.commit()
    db.refresh(user)

    return {
        "message": "User status updated successfully",
        "user_id": user.id,
        "status": user.status
    }