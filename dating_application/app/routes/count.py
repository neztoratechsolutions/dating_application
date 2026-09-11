from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.users import User

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

    return{
        "customer_count":customer_count,
        "creator_count":creator_count,
        "user_count":user_count
    }

