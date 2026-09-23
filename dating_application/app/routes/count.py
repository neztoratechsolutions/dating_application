from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import SessionLocal
from app.models.users import User
from app.models.review import Review

router = APIRouter(
    prefix="/count",
    tags=["Count"]
)

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()

@router.get("/")
def get_user_counts(
    db:Session = Depends(get_db)
):
    customer_count = db.query(User).filter(
        User.role == "customer"
    ).count()

    creator_count = db.query(User).filter(
            User.role == "creator"
    ).count()

    user_count = customer_count + creator_count

    average_rating = db.query(
            func.avg(Review.star_details)
        ).scalar()
    
    total_reviews = db.query(Review).count()
    
    if average_rating is None :
        average_rating = 0.0
    else:
        average_rating=round(float(average_rating),2)
    

    return{
        "customer_count":customer_count,
        "creator_count":creator_count,
        "user_count":user_count,
        "overall_rating": average_rating,
        "total_reviews": total_reviews
    }


