from fastapi import APIRouter , Depends , HTTPException , status
from sqlalchemy.orm import Session

from app.models.social_models import FollowDetail
from app.database import SessionLocal
from app.models.users import User
from app.models.favorite import Favorite
from app.schemas.favorite import FavoriteCreate, FavoriteResponse , FavoriteDetailResponse

router = APIRouter(
    prefix="/favorites",
    tags= ["Favorites"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Add creator to customer's favourite

@router.post(
    "/",
    response_model=FavoriteResponse,
    status_code=status.HTTP_201_CREATED
)
def add_favourite(
    data : FavoriteCreate,
    db : Session =Depends(get_db)
):
    #check customer 

    customer = db.query(User).filter(
        User.id == data.customer_id,
        User.role == "customer"
    ).first()

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    #check creator

    creator = db.query(User).filter(
        User.id == data.creator_id,
        User.role == "creator"
    ).first()

    if not creator:
        raise HTTPException(
            status_code=404,
            detail="Creator not found"
        )

    # Check whether already favourite
    existing_favorite = db.query(Favorite).filter(
        Favorite.customer_id == data.customer_id,
        Favorite.creator_id == data.creator_id
    ).first()

    if existing_favorite:
        raise HTTPException(
            status_code=400,
            detail="Creator is already in favourites"
        )

    # Create favourite
    favorite = Favorite(
        customer_id = data.customer_id,
        creator_id = data.creator_id
    )

    db.add(favorite)
    db.commit()
    db.refresh(favorite)

    return favorite

# Get favourite creators of a customer

@router.get(
    "{customer_id}",
    response_model=list[FavoriteResponse]
)
def get_favorite_creators(
    customer_id : int,
    db: Session = Depends(get_db)
):
    # Check customer
    customer = db.query(User).filter(
        User.id == customer_id ,
        User.role == "customer"
    ).first()

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    favorites = db.query(Favorite).filter(
        Favorite.customer_id == customer_id
    ).all()

    return favorites

@router.get(
    "/details/{customer_id}",
    response_model= list[FavoriteDetailResponse]
)
def get_favorite_details(
    customer_id : int,
    db: Session = Depends(get_db)
):
    #check customer
    customer = db.query(User).filter(
        User.id == customer_id,
        User.role == "customer"
    ).first()

    if not customer:
        raise HTTPException(
            status_code = 404,
            detail="Customer not found"
        )

    # Get customer's favourite creators

    favorites = db.query(Favorite).filter(
    Favorite.customer_id == customer_id
    ).all()

    result = []

    for favorite in favorites:

        creator = db.query(User).filter(
            User.id == favorite.creator_id,
            User.role == "creator"
        ).first()

        if not creator:
            continue

        # Followers
        follower_rows = db.query(FollowDetail).filter(
            FollowDetail.following_id == creator.id,
            FollowDetail.follow_status == "following"
        ).all()

        followers = []

        for row in follower_rows:
            follower = db.query(User).filter(
                User.id == row.follower_id
            ).first()

            if follower:
                followers.append({
                    "id": follower.id,
                    "display_name": follower.display_name,
                    "email": follower.email,
                    "profile_photo": follower.profile_photo,
                    "role": follower.role
                })

        # Following
        following_rows = db.query(FollowDetail).filter(
            FollowDetail.follower_id == creator.id,
            FollowDetail.follow_status == "following"
        ).all()

        following = []

        for row in following_rows:
            following_user = db.query(User).filter(
                User.id == row.following_id
            ).first()

            if following_user:
                following.append({
                    "id": following_user.id,
                    "display_name": following_user.display_name,
                    "email": following_user.email,
                    "profile_photo": following_user.profile_photo,
                    "role": following_user.role
                })

        result.append({
            "favorite_id": favorite.id,
            "customer_id": customer.id,
            "customer_name": customer.display_name,
            "creator_id": creator.id,
            "creator_name": creator.display_name,
            "followers_count": len(followers),
            "following_count": len(following),
            "followers": followers,
            "following": following
        })

    return result

@router.delete(
    "/{customer_id}/{creator_id}"
)
def remove_favorite(
    customer_id : int,
    creator_id : int ,
    db : Session = Depends(get_db)
):
    customer = db.query(User).filter(
        User.id == customer_id,
        User.role == "customer"
    ).first()

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    creator = db.query(User).filter(
        User.id == creator_id,
        User.role == "creator"
    ).first()

    if not creator:
        raise HTTPException(
            status_code=404,
            detail="Creator not found"
        )

    favorite = db.query(Favorite).filter(
        Favorite.customer_id == customer_id,
        Favorite.creator_id == creator_id
    ).first()

    if not favorite:
        raise HTTPException(
            status_code=404,
            detail="Creator is not in favourites"
        )
    
    db.delete(favorite)
    db.commit()

    return {
        "message": "Creator removed from favourites successfully"
    }