import os

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Form,
    Query,
)

from sqlalchemy.orm import Session
from sqlalchemy import func

from database import SessionLocal

from models.users import User
from models.state import State
from models.gallery import Gallery
from models.user_status import UserStatus
from models.review import Review
from models.pricing_details import PricingDetail
from models.social_models import FollowDetail

from schemas.users import (
    UserCreate,
    UserStatusUpdate,
    UserUpdate,
    UserResponse,
)

from security import (
    hash_password,
    generate_referral_code,
)


router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


UPLOAD_DIR = "uploads"


# ==========================================================
# DATABASE
# ==========================================================

def get_db():
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


# ==========================================================
# CREATE USER
# ==========================================================

@router.post(
    "/",
    response_model=UserResponse
)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db)
):

    existing_user = (
        db.query(User)
        .filter(User.email == user.email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already exists"
        )

    # ------------------------------------------------------
    # Set role based on gender
    # ------------------------------------------------------

    if user.gender == "Male":
        role = "customer"

    elif user.gender == "Female":
        role = "creator"

    else:
        role = "customer"

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


# ==========================================================
# CREATE ADMIN
# ==========================================================

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

    # ------------------------------------------------------
    # Check email
    # ------------------------------------------------------

    existing_user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already exists"
        )

    # ------------------------------------------------------
    # Check phone
    # ------------------------------------------------------

    existing_phone = (
        db.query(User)
        .filter(User.phone == phone)
        .first()
    )

    if existing_phone:
        raise HTTPException(
            status_code=400,
            detail="Mobile number already exists"
        )

    # ------------------------------------------------------
    # Create upload directory
    # ------------------------------------------------------

    os.makedirs(
        UPLOAD_DIR,
        exist_ok=True
    )

    # ------------------------------------------------------
    # Save profile photo
    # ------------------------------------------------------

    file_path = os.path.join(
        UPLOAD_DIR,
        profile_photo.filename
    )

    with open(
        file_path,
        "wb"
    ) as buffer:

        buffer.write(
            profile_photo.file.read()
        )

    # ------------------------------------------------------
    # Create admin
    # ------------------------------------------------------

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


# ==========================================================
# FILTER USERS
# ==========================================================

@router.get(
    "/filter",
    status_code=status.HTTP_200_OK
)
def get_users_filter(
    role: str | None = Query(
        None,
        description="creator or customer"
    ),

    state_id: int | None = Query(
        None,
        description="State ID"
    ),

    is_online: bool | None = Query(
        None,
        description="true/false"
    ),

    db: Session = Depends(get_db)
):

    query = (
        db.query(
            User,
            UserStatus,
            PricingDetail,

            func.coalesce(
                func.avg(Review.star_details),
                0
            ).label("average_rating"),

            func.count(
                Review.id
            ).label("total_reviews")
        )

        .outerjoin(
            UserStatus,
            User.id == UserStatus.user_id
        )

        .outerjoin(
            PricingDetail,
            User.id == PricingDetail.user_id
        )

        .outerjoin(
            Review,
            User.id == Review.user_id
        )

        .filter(
            User.role != "admin"
        )
    )

    # ------------------------------------------------------
    # Role filter
    # ------------------------------------------------------

    if role:

        query = query.filter(
            User.role == role
        )

    # ------------------------------------------------------
    # State filter
    # ------------------------------------------------------

    if state_id:

        query = query.filter(
            User.state_id == state_id
        )

    # ------------------------------------------------------
    # Group By
    # ------------------------------------------------------

    query = query.group_by(
        User.id,
        UserStatus.id,
        PricingDetail.id
    )

    results = query.all()

    data = []

    # ------------------------------------------------------
    # Response
    # ------------------------------------------------------

    for (
        user,
        status_obj,
        pricing,
        avg_rating,
        total_reviews
    ) in results:

        online = (
            status_obj.is_online
            if status_obj
            else False
        )

        # --------------------------------------------------
        # Online filter
        # --------------------------------------------------

        if (
            is_online is not None
            and online != is_online
        ):

            continue

        data.append(
            {
                "id": user.id,

                "display_name":
                    user.display_name,

                "email":
                    user.email,

                "phone":
                    user.phone,

                "role":
                    user.role,

                "state_id":
                    user.state_id,

                "profile_photo":
                    user.profile_photo,

                "is_online":
                    online,

                "reviews": {

                    "average_rating":
                        round(
                            float(avg_rating),
                            1
                        ),

                    "total_reviews":
                        total_reviews
                },

                "pricing": {

                    "chat_amount":
                        (
                            float(
                                pricing.chat_amount
                            )
                            if pricing
                            else 0
                        ),

                    "voice_call_amount":
                        (
                            float(
                                pricing.voice_call_amount
                            )
                            if pricing
                            else 0
                        ),

                    "video_call_amount":
                        (
                            float(
                                pricing.video_call_amount
                            )
                            if pricing
                            else 0
                        )
                }
            }
        )

    return {
        "status_code": 200,
        "message": "Users fetched successfully",
        "count": len(data),
        "data": data
    }


# ==========================================================
# GET ALL USERS
# ==========================================================

@router.get(
    "/",
    response_model=list[UserResponse]
)
def get_users(
    db: Session = Depends(get_db)
):

    users = (
        db.query(User)
        .filter(
            User.role != "admin"
        )
        .all()
    )

    return users


# ==========================================================
# GET USER BY ID
# ==========================================================

@router.get(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK
)
def get_user(
    user_id: int,
    db: Session = Depends(get_db)
):

    result = (
        db.query(
            User,
            State
        )

        .outerjoin(
            State,
            User.state_id == State.id
        )

        .filter(
            User.id == user_id
        )

        .first()
    )

    if not result:

        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    user, state = result

    # ------------------------------------------------------
    # User status
    # ------------------------------------------------------

    status_obj = (
        db.query(UserStatus)
        .filter(
            UserStatus.user_id == user.id
        )
        .first()
    )

    # ------------------------------------------------------
    # Pricing
    # ------------------------------------------------------

    pricing = (
        db.query(PricingDetail)
        .filter(
            PricingDetail.user_id == user.id
        )
        .first()
    )

    # ------------------------------------------------------
    # Gallery
    # ------------------------------------------------------

    gallery = (
        db.query(Gallery)
        .filter(
            Gallery.user_id == user.id
        )
        .all()
    )

    # ------------------------------------------------------
    # Reviews
    # ------------------------------------------------------

    review_data = (
        db.query(

            func.coalesce(
                func.avg(
                    Review.star_details
                ),
                0
            ).label(
                "average_rating"
            ),

            func.count(
                Review.id
            ).label(
                "total_reviews"
            )
        )

        .filter(
            Review.user_id == user.id
        )

        .first()
    )

    # ------------------------------------------------------
    # Followers count
    # ------------------------------------------------------

    followers_count = (
        db.query(
            func.count(
                FollowDetail.id
            )
        )

        .filter(
            FollowDetail.following_id == user.id,
            FollowDetail.follow_status == "following"
        )

        .scalar()
    )

    # ------------------------------------------------------
    # Following count
    # ------------------------------------------------------

    following_count = (
        db.query(
            func.count(
                FollowDetail.id
            )
        )

        .filter(
            FollowDetail.follower_id == user.id,
            FollowDetail.follow_status == "following"
        )

        .scalar()
    )

    # ------------------------------------------------------
    # Response
    # ------------------------------------------------------

    return {
        "status_code": status.HTTP_200_OK,

        "message":
            "User details fetched successfully",

        "data": {

            "id":
                user.id,

            "display_name":
                user.display_name,

            "email":
                user.email,

            "phone":
                user.phone,

            "bio":
                user.bio,

            "description":
                user.description,

            "role":
                user.role,

            "state": {

                "id":
                    state.id
                    if state
                    else None,

                "name":
                    state.state_name
                    if state
                    else None
            },

            "profile_photo":
                user.profile_photo,

            "is_online":
                (
                    status_obj.is_online
                    if status_obj
                    else False
                ),

            "followers_count":
                followers_count,

            "following_count":
                following_count,

            "reviews": {

                "average_rating":
                    round(
                        float(
                            review_data.average_rating
                        ),
                        1
                    ),

                "total_reviews":
                    review_data.total_reviews
            },

            "pricing": {

                "chat_amount":
                    (
                        float(
                            pricing.chat_amount
                        )
                        if pricing
                        else 0
                    ),

                "voice_call_amount":
                    (
                        float(
                            pricing.voice_call_amount
                        )
                        if pricing
                        else 0
                    ),

                "video_call_amount":
                    (
                        float(
                            pricing.video_call_amount
                        )
                        if pricing
                        else 0
                    )
            },

            "gallery": [

                {
                    "id":
                        image.id,

                    "photo":
                        image.photo
                }

                for image in gallery
            ]
        }
    }


# ==========================================================
# UPDATE USER
# ==========================================================

@router.put(
    "/{user_id}",
    response_model=UserResponse
)
async def update_user(
    user_id: int,

    display_name: str | None = Form(None),

    bio: str | None = Form(None),

    profile_photo: UploadFile | None = File(None),

    db: Session = Depends(get_db)
):

    # ------------------------------------------------------
    # Get user
    # ------------------------------------------------------

    user = (
        db.query(User)
        .filter(
            User.id == user_id
        )
        .first()
    )

    if not user:

        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # ------------------------------------------------------
    # Update display name
    # ------------------------------------------------------

    if display_name is not None:

        user.display_name = display_name

    # ------------------------------------------------------
    # Update bio
    # ------------------------------------------------------

    if bio is not None:

        user.bio = bio

    # ------------------------------------------------------
    # Update profile photo
    # ------------------------------------------------------

    if (
        profile_photo is not None
        and profile_photo.filename
    ):

        os.makedirs(
            UPLOAD_DIR,
            exist_ok=True
        )

        file_path = os.path.join(
            UPLOAD_DIR,
            profile_photo.filename
        )

        with open(
            file_path,
            "wb"
        ) as buffer:

            buffer.write(
                await profile_photo.read()
            )

        user.profile_photo = file_path

    # ------------------------------------------------------
    # Save
    # ------------------------------------------------------

    db.commit()
    db.refresh(user)

    return {
        "message":
            "User updated successfully",

        "data": {

            "id":
                user.id,

            "display_name":
                user.display_name,

            "bio":
                user.bio,

            "description":
                user.description,

            "updated_at":
                user.updated_at
        }
    }


# ==========================================================
# DELETE USER
# ==========================================================

@router.delete(
    "/{user_id}"
)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db)
):

    user = (
        db.query(User)
        .filter(
            User.id == user_id
        )
        .first()
    )

    if not user:

        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    db.delete(user)
    db.commit()

    return {
        "message":
            "User deleted successfully"
    }


# ==========================================================
# UPDATE USER STATUS
# ==========================================================

@router.patch(
    "/{user_id}/status"
)
def update_user_status(
    user_id: int,
    data: UserStatusUpdate,
    db: Session = Depends(get_db)
):

    user = (
        db.query(User)
        .filter(
            User.id == user_id
        )
        .first()
    )

    if not user:

        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    user.status = data.status

    db.commit()
    db.refresh(user)

    return {
        "message":
            "User status updated successfully",

        "user_id":
            user.id,

        "status":
            user.status
    }