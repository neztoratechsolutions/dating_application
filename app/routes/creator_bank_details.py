from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)

from pydantic import BaseModel, Field

from sqlalchemy.orm import Session

from database import get_db

from models.users import User
from models.creator_bank_details import CreatorBankDetails


router = APIRouter(
    prefix="/creator-bank-details",
    tags=["Creator Bank Details"]
)


# ==========================================================
# SCHEMAS
# ==========================================================

class CreatorBankDetailsCreate(BaseModel):

    holder_name: str = Field(
        ...,
        min_length=2,
        max_length=150
    )

    account_number: str = Field(
        ...,
        min_length=4,
        max_length=50
    )

    ifsc_code: str = Field(
        ...,
        min_length=11,
        max_length=11
    )

    bank_name: str = Field(
        ...,
        min_length=2,
        max_length=150
    )


# ==========================================================
# CREATE BANK DETAILS
# ==========================================================

@router.post(
    "/{creator_id}",
    status_code=status.HTTP_201_CREATED
)
def create_creator_bank_details(
    creator_id: int,
    data: CreatorBankDetailsCreate,
    db: Session = Depends(get_db)
):

    # ------------------------------------------------------
    # Check Creator
    # ------------------------------------------------------

    creator = db.query(User).filter(
        User.id == creator_id,
        User.role == "creator"
    ).first()

    if not creator:

        raise HTTPException(
            status_code=404,
            detail="Creator not found"
        )

    # ------------------------------------------------------
    # Check Existing Bank Details
    # ------------------------------------------------------

    existing = db.query(
        CreatorBankDetails
    ).filter(
        CreatorBankDetails.creator_id == creator_id
    ).first()

    if existing:

        raise HTTPException(
            status_code=400,
            detail="Bank details already exist for this creator"
        )

    # ------------------------------------------------------
    # Create
    # ------------------------------------------------------

    bank_details = CreatorBankDetails(
        creator_id=creator_id,
        holder_name=data.holder_name,
        account_number=data.account_number,
        ifsc_code=data.ifsc_code.upper(),
        bank_name=data.bank_name
    )

    db.add(bank_details)

    db.commit()

    db.refresh(bank_details)

    return {
        "status": True,
        "message": "Creator bank details created successfully",
        "data": {
            "id": bank_details.id,
            "creator_id": bank_details.creator_id,
            "holder_name": bank_details.holder_name,
            "account_number": bank_details.account_number,
            "ifsc_code": bank_details.ifsc_code,
            "bank_name": bank_details.bank_name,
            "created_at": bank_details.created_at
        }
    }