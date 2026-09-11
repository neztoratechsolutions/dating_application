from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.review import Review
from app.models.users import User
from app.schemas.review import ReviewCreate, ReviewResponse

router = APIRouter(prefix="/reviews",tags=["Reviews"])


@router.post(
    "/",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED
)
def create_review(
    review: ReviewCreate,
    user_id: int,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    new_review = Review(
        user_id=user_id,
        star_details=review.star_details,
        description=review.description
    )

    db.add(new_review)
    db.commit()
    db.refresh(new_review)

    return new_review


@router.get(
    "/",
    response_model=list[ReviewResponse],
    status_code=status.HTTP_200_OK
)
def get_reviews(db: Session = Depends(get_db)):
    reviews = db.query(Review).all()
    return reviews


@router.get(
    "/{review_id}",
    response_model=ReviewResponse,
    status_code=status.HTTP_200_OK
)
def get_review(
    review_id: int,
    db: Session = Depends(get_db)
):
    review = db.query(Review).filter(
        Review.id == review_id
    ).first()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )

    return review


@router.delete(
    "/{review_id}",
    status_code=status.HTTP_200_OK
)
def delete_review(
    review_id: int,
    db: Session = Depends(get_db)
):
    review = db.query(Review).filter(
        Review.id == review_id
    ).first()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )

    db.delete(review)
    db.commit()

    return {
        "message": "Review deleted successfully"
    }