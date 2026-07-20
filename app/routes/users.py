from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import SessionLocal
from models.users import User
from models.state import State
from schemas.users import (UserCreate,UserUpdate,UserResponse)
from security import (hash_password,generate_referral_code)

router = APIRouter(prefix="/users",tags=["Users"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ------------------------------------- USER CREATE -----------------------------------------------

@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db)
):
    # Email check
    existing_user = db.query(User).filter(
        User.email == user.email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already exists"
        )

    # Phone check
    existing_phone = db.query(User).filter(
        User.phone == user.phone
    ).first()

    if existing_phone:
        raise HTTPException(
            status_code=400,
            detail="Mobile number already exists"
        )

    if user.gender == "Male":
        role = "customer"
    elif user.gender == "Female":
        role = "creator"
    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid gender"
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
        gender=user.gender,
        role=role,
        referral_code=generate_referral_code()
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


# ----------------------------------------------------- ADMIN_CREATE -----------------------------


@router.post(
    "/admins",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
def create_admin(
    user: UserCreate,
    db: Session = Depends(get_db)
):
    # Email check
    existing_user = db.query(User).filter(
        User.email == user.email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already exists"
        )

    # Mobile number check
    existing_phone = db.query(User).filter(
        User.phone == user.phone
    ).first()

    if existing_phone:
        raise HTTPException(
            status_code=400,
            detail="Mobile number already exists"
        )

    new_admin = User(
        email=user.email,
        phone=user.phone,
        password=hash_password(user.password),
        display_name=user.display_name,
        bio=user.bio,
        description=user.description,
        state_id=user.state_id,
        profile_photo=user.profile_photo,
        gender=user.gender,
        role="admin",
        referral_code=generate_referral_code()
    )

    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)

    return new_admin



# --------------------------------------------- GET_USER ----------------------------------------


@router.get(
    "/",
    response_model=list[UserResponse],
    status_code=status.HTTP_200_OK
)
def get_users(
    db: Session = Depends(get_db)
):
    return db.query(User).all()


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK
)
def get_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user


# --------------------------------------- Update_user --------------------------------------------

@router.put(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK
)
def update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    update_data = data.model_dump(
        exclude_unset=True
    )

    
    if update_data.get("state_id") == 0:
        update_data.pop("state_id")

    
    if "gender" in update_data:

        if update_data["gender"] == "Male":
            update_data["role"] = "customer"

        elif update_data["gender"] == "Female":
            update_data["role"] = "creator"

        elif update_data["gender"] == "Other":
            update_data["role"] = user.role

    
    if "state_id" in update_data:
        state = db.query(State).filter(
            State.id == update_data["state_id"]
        ).first()

        if not state:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid state_id"
            )

    for key, value in update_data.items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)

    return user


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_200_OK
)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    db.delete(user)
    db.commit()

    return {
        "message": "User deleted successfully"
    }