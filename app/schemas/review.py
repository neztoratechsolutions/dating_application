from datetime import datetime
from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    reviewer_id: int
    reviewee_id: int
    star_details: int = Field(..., ge=1, le=5)
    description: str | None = None


class ReviewResponse(BaseModel):
    id: int
    reviewer_id: int
    reviewee_id: int
    star_details: int
    description: str | None
    submitted_at: datetime

    class Config:
        from_attributes = True

class ReviewByUserResponse(BaseModel):
    id: int
    reviewer_id: int
    reviewer_name: str
    reviewee_id: int
    reviewee_name: str
    star_details: int
    description: str | None = None
    submitted_at: datetime

    class Config:
        from_attributes = True


    