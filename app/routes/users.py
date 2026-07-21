import os
from fastapi import (APIRouter,Depends,HTTPException,status,UploadFile,File,Form)
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

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
def create_user(
    email: str = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    display_name: str = Form(...),
    bio: str = Form(None),
    description: str = Form(None),
    state_id: int = Form(...),
    gender: str = Form(...),
    profile_photo: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Email check
    existing_user = db.query(User).filter(
        User.email == email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already exists"
        )

    # Phone check
    existing_phone = db.query(User).filter(
        User.phone == phone
    ).first()

    if existing_phone:
        raise HTTPException(
            status_code=400,
            detail="Mobile number already exists"
        )

    if gender == "Male":
        role = "customer"
    elif gender == "Female":
        role = "creator"
    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid gender"
        )

    file_path = os.path.join(
        UPLOAD_DIR,
        profile_photo.filename
    )

    with open(file_path, "wb") as buffer:
        buffer.write(profile_photo.file.read())

    new_user = User(
        email=email,
        phone=phone,
        password=hash_password(password),
        display_name=display_name,
        bio=bio,
        description=description,
        state_id=state_id,
        profile_photo=file_path,
        gender=gender,
        role=role,
        referral_code=generate_referral_code()
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


# -----------------------------------------------------
# ADMIN CREATE
# -----------------------------------------------------

@router.post(
    "/admins",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
def create_admin(
    email: str = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    display_name: str = Form(...),
    bio: str = Form(None),
    description: str = Form(None),
    state_id: int = Form(...),
    gender: str = Form(...),
    profile_photo: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Email check
    existing_user = db.query(User).filter(
        User.email == email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already exists"
        )

    # Mobile number check
    existing_phone = db.query(User).filter(
        User.phone == phone
    ).first()

    if existing_phone:
        raise HTTPException(
            status_code=400,
            detail="Mobile number already exists"
        )

    file_path = os.path.join(
        UPLOAD_DIR,
        profile_photo.filename
    )

    with open(file_path, "wb") as buffer:
        buffer.write(profile_photo.file.read())

    new_admin = User(
        email=email,
        phone=phone,
        password=hash_password(password),
        display_name=display_name,
        bio=bio,
        description=description,
        state_id=state_id,
        profile_photo=file_path,
        gender=gender,
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
    email: str | None = Form(None),
    phone: str | None = Form(None),
    display_name: str | None = Form(None),
    bio: str | None = Form(None),
    description: str | None = Form(None),
    state_id: int | None = Form(None),
    is_active: bool | None = Form(None),
    is_verified: bool | None = Form(None),
    profile_photo: UploadFile | None = File(None),
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

    # Email validation
    if email is not None:

        existing_email = db.query(User).filter(
            User.email == email,
            User.id != user_id
        ).first()

        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )

        user.email = email

    # Phone validation
    if phone is not None:

        existing_phone = db.query(User).filter(
            User.phone == phone,
            User.id != user_id
        ).first()

        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mobile number already exists"
            )

        user.phone = phone

    # State validation
    if state_id is not None:

        state = db.query(State).filter(
            State.id == state_id
        ).first()

        if not state:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid state_id"
            )

        user.state_id = state_id

    if display_name is not None:
        user.display_name = display_name

    if bio is not None:
        user.bio = bio

    if description is not None:
        user.description = description

    if is_active is not None:
        user.is_active = is_active

    if is_verified is not None:
        user.is_verified = is_verified

    # Profile photo upload
    if (
        profile_photo is not None
        and hasattr(profile_photo, "filename")
        and profile_photo.filename
    ):

        file_path = os.path.join(
            UPLOAD_DIR,
            profile_photo.filename
        )

        with open(file_path, "wb") as buffer:
            buffer.write(
                profile_photo.file.read()
            )

        user.profile_photo = file_path

    db.commit()
    db.refresh(user)

    return user


# ---------------------------------------------- DELETE ------------------------------------------


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