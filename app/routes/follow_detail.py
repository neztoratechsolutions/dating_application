from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import SessionLocal
from models.users import User
from models.social_models import FollowDetail
from schemas.follow_details import (
    FollowDetailCreate,
    FollowDetailUpdate,
    FollowDetailResponse,UserFollowResponse
)
from sqlalchemy.orm import aliased
router = APIRouter(
    prefix="/follow-details",
    tags=["Follow Details"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

#----------------FolloW Create-------------#
from sqlalchemy.orm import aliased

@router.post(
    "/",
    response_model=FollowDetailResponse,
    status_code=status.HTTP_201_CREATED
)
def create_follow(
    request: FollowDetailCreate,
    db: Session = Depends(get_db)
):

    # Prevent self-follow
    if request.following_id == request.follower_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User cannot follow themselves."
        )

    # Check whether the user being followed exists
    following_user = (
        db.query(User)
        .filter(User.id == request.following_id)
        .first()
    )

    # Check whether the follower exists
    follower = (
        db.query(User)
        .filter(User.id == request.follower_id)
        .first()
    )

    if not following_user or not follower:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    # Prevent duplicate follow
    existing = (
        db.query(FollowDetail)
        .filter(
            FollowDetail.following_id == request.following_id,
            FollowDetail.follower_id == request.follower_id
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already following this user."
        )

    # Create follow record
    follow = FollowDetail(
        following_id=request.following_id,
        follower_id=request.follower_id,
        follow_status=request.follow_status
    )

    db.add(follow)
    db.commit()
    db.refresh(follow)

    FollowingUser = aliased(User)
    FollowerUser = aliased(User)

    result = (
        db.query(
            FollowDetail.id,
            FollowDetail.following_id,
            FollowingUser.display_name.label("following_name"),
            FollowDetail.follower_id,
            FollowerUser.display_name.label("follower_name"),
            FollowDetail.follow_status,
            FollowDetail.created_at,
            FollowDetail.updated_at,
        )
        .join(
            FollowingUser,
            FollowDetail.following_id == FollowingUser.id
        )
        .join(
            FollowerUser,
            FollowDetail.follower_id == FollowerUser.id
        )
        .filter(FollowDetail.id == follow.id)
        .first()
    )

    return result

#-------------------Get Followers details--------#
@router.get(
    "/",
    response_model=list[FollowDetailResponse]
)
def get_all_follows(
    db: Session = Depends(get_db)
):
    FollowingUser = aliased(User)
    FollowerUser = aliased(User)

    follows = (
        db.query(
            FollowDetail.id,
            FollowDetail.following_id,
            FollowingUser.display_name.label("following_name"),
            FollowDetail.follower_id,
            FollowerUser.display_name.label("follower_name"),
            FollowDetail.follow_status,
            FollowDetail.created_at,
            FollowDetail.updated_at,
        )
        .join(
            FollowingUser,
            FollowDetail.following_id == FollowingUser.id
        )
        .join(
            FollowerUser,
            FollowDetail.follower_id == FollowerUser.id
        )
        .all()
    )

    return follows
#--------------Get the Followers By Id-----------#
from sqlalchemy.orm import aliased

@router.get(
    "/user/{following_id}",
    response_model=UserFollowResponse
)
def get_user_follow_details(
    following_id: int,
    db: Session = Depends(get_db)
):
    FollowingUser = aliased(User)
    FollowerUser = aliased(User)

    # Check user exists
    user = (
        db.query(User)
        .filter(User.id == following_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    # Users who follow this user
    followers = (
        db.query(
            FollowerUser.id.label("id"),
            FollowerUser.display_name.label("display_name")
        )
        .join(
            FollowDetail,
            FollowDetail.follower_id == FollowerUser.id
        )
        .filter(
            FollowDetail.following_id == following_id,
            FollowDetail.follow_status == "following"
        )
        .all()
    )

    # Users this user follows
    following = (
        db.query(
            FollowingUser.id.label("id"),
            FollowingUser.display_name.label("display_name")
        )
        .join(
            FollowDetail,
            FollowDetail.following_id == FollowingUser.id
        )
        .filter(
            FollowDetail.follower_id == following_id,
            FollowDetail.follow_status == "following"
        )
        .all()
    )

    return {
        "following_id": user.id,
        "following_name": user.display_name,
        "followers_count": len(followers),
        "following_count": len(following),
        "followers": followers,
        "following": following
    }
#-------------------Update--------------#
@router.put(
    "/{follow_id}",
    response_model=FollowDetailResponse,
    status_code=status.HTTP_200_OK
)
def update_follow(
    follow_id: int,
    request: FollowDetailUpdate,
    db: Session = Depends(get_db)
):
    follow = (
        db.query(FollowDetail)
        .filter(FollowDetail.id == follow_id)
        .first()
    )

    if not follow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Follow detail not found."
        )

    follow.follow_status = request.follow_status

    db.commit()
    db.refresh(follow)

    FollowingUser = aliased(User)
    FollowerUser = aliased(User)

    result = (
        db.query(
            FollowDetail.id,
            FollowDetail.following_id,
            FollowingUser.display_name.label("following_name"),
            FollowDetail.follower_id,
            FollowerUser.display_name.label("follower_name"),
            FollowDetail.follow_status,
            FollowDetail.created_at,
            FollowDetail.updated_at,
        )
        .join(
            FollowingUser,
            FollowDetail.following_id == FollowingUser.id
        )
        .join(
            FollowerUser,
            FollowDetail.follower_id == FollowerUser.id
        )
        .filter(FollowDetail.id == follow.id)
        .first()
    )

    return result

#----------------Delete Follow----------------#
@router.delete(
    "/{follow_id}",
    status_code=status.HTTP_200_OK
)
def delete_follow(
    follow_id: int,
    db: Session = Depends(get_db)
):
    follow = (
        db.query(FollowDetail)
        .filter(FollowDetail.id == follow_id)
        .first()
    )

    if not follow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Follow detail not found."
        )

    db.delete(follow)
    db.commit()

    return {
        "message": "Follow detail deleted successfully."
    }