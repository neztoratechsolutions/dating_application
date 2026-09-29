from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.users import User
from app.models.earnings import Earning
from app.models.wallet import Wallet
from app.models.social_models import FollowDetail
from app.models.review import Review
from app.models.kyc_detail import KYCDetail
from app.models.chat_history import ChatMessage, ChatCallLog
from app.models.gift_details import GiftDetail

router = APIRouter(
    prefix="/creator",
    tags=["Creator Dashboard"]
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()

@router.get("/dashboard/{creator_id}")
def get_creator_id(
    creator_id : int,
    db : Session = Depends(get_db)
):
    #  Check creator

    creator = db.query(User).filter(
        User.id == creator_id,
        User.role == "creator"
    ).first()

    if not creator :
        raise HTTPException(
            status_code=404,
            detail="Creator not found"
        )



    #Followers count

    followers_count = db.query(FollowDetail).filter(
        FollowDetail.following_id == creator_id,
        FollowDetail.follow_status == "following"
    ).count()



    #Rating

    rating = db.query(
        func.avg(Review.star_details).filter(
            Review.user_id == creator_id
        )
    ).scalar()

    total_reviews = db.query(Review).filter(
        Review.user_id == creator_id
    ).count()

    if rating is None :
        rating = 0.0
    else:
        rating = round (float(rating),2)

    
    
 
    # Final response
    

    return {
        "creator": {
            "id": creator.id,
            "name": creator.display_name
            
        },


        "summary": {
            "followers": followers_count,
            "rating": rating,
            "total_reviews": total_reviews
        },
    }