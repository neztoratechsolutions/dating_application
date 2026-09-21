from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import date

from database import get_db
from models.review import Review
from models.users import User
from schemas.review import ReviewCreate, ReviewResponse


router = APIRouter(
    prefix="/reviews",
    tags=["Reviews"]
)


# ==========================================================
# CREATE REVIEW
# ==========================================================

@router.post(
    "/",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED
)
def create_review(
    review: ReviewCreate,
    db: Session = Depends(get_db)
):

    # ------------------------------------------------------
    # Check Reviewer
    # ------------------------------------------------------

    reviewer = db.query(User).filter(
        User.id == review.reviewer_id
    ).first()

    if not reviewer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reviewer not found"
        )

    # ------------------------------------------------------
    # Check Reviewee
    # ------------------------------------------------------

    reviewee = db.query(User).filter(
        User.id == review.reviewee_id
    ).first()

    if not reviewee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reviewee not found"
        )

    # ------------------------------------------------------
    # Reviewer cannot review themselves
    # ------------------------------------------------------

    if review.reviewer_id == review.reviewee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reviewer and reviewee cannot be the same"
        )

    # ------------------------------------------------------
    # Create Review
    # ------------------------------------------------------

    new_review = Review(
        reviewer_id=review.reviewer_id,
        reviewee_id=review.reviewee_id,
        star_details=review.star_details,
        description=review.description
    )

    db.add(new_review)
    db.commit()
    db.refresh(new_review)

    return new_review


# ==========================================================
# GET ALL REVIEWS
# ==========================================================

@router.get(
    "/",
    response_model=list[ReviewResponse],
    status_code=status.HTTP_200_OK
)
def get_reviews(
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db)
):

    query = db.query(Review)

    # ------------------------------------------------------
    # Start Date Filter
    # ------------------------------------------------------

    if start_date:
        query = query.filter(
            Review.submitted_at >= start_date
        )

    # ------------------------------------------------------
    # End Date Filter
    # ------------------------------------------------------

    if end_date:
        query = query.filter(
            Review.submitted_at < end_date
        )

    reviews = query.order_by(
        Review.submitted_at.desc()
    ).all()

    if not reviews:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No review data found"
        )

    return reviews


# ==========================================================
# GET REVIEW BY ID
# ==========================================================

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


# ==========================================================
# DELETE REVIEW
# ==========================================================

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