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

from models.kyc_detail import CreatorKYC
from models.creator_verify import CreatorVerification
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


# ==========================================================
# GET CREATOR BANK DETAILS
# ==========================================================


# ==========================================================
# GET COMPLETE CREATOR BANK AND VERIFICATION DETAILS
# ==========================================================

@router.get(
    "/{creator_id}",
    status_code=status.HTTP_200_OK
)
def get_creator_bank_details(
    creator_id: int,
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Creator not found"
        )

    # ------------------------------------------------------
    # Get Creator Bank Details
    # ------------------------------------------------------

    bank_details = db.query(CreatorBankDetails).filter(
        CreatorBankDetails.creator_id == creator_id
    ).first()

    if not bank_details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Creator bank details not found"
        )

    # ------------------------------------------------------
    # Get Creator KYC Details
    # ------------------------------------------------------

    creator_kyc = db.query(CreatorKYC).filter(
        CreatorKYC.user_id == creator_id
    ).first()

    # ------------------------------------------------------
    # Get Creator Verification Details
    # ------------------------------------------------------

    verification = db.query(CreatorVerification).filter(
        CreatorVerification.creator_id == creator_id
    ).first()

    # ------------------------------------------------------
    # Response
    # ------------------------------------------------------

    return {
        "status": True,
        "message": "Creator bank and verification details fetched successfully",

        "data": {

            # Bank Details
            "bank_details": {
                "id": bank_details.id,
                "creator_id": bank_details.creator_id,
                "holder_name": bank_details.holder_name,
                "account_number": bank_details.account_number,
                "ifsc_code": bank_details.ifsc_code,
                "bank_name": bank_details.bank_name,
                "created_at": bank_details.created_at,
                "updated_at": bank_details.updated_at
            },

            # Bank KYC Details
            "bank_kyc": {
                "id": creator_kyc.id if creator_kyc else None,
                "bank_photo": creator_kyc.bank_photo if creator_kyc else None,
                "bank_status": creator_kyc.bank_status if creator_kyc else "Pending",
                "created_at": creator_kyc.created_at if creator_kyc else None,
                "updated_at": creator_kyc.updated_at if creator_kyc else None
            },

            # Voice and Selfie Verification
            "verification": {
                "id": verification.id if verification else None,
                "voice_file": verification.voice_file if verification else None,
                "voice_duration": verification.voice_duration if verification else None,
                "voice_status": verification.voice_status if verification else "pending",
                "selfie_image": verification.selfie_image if verification else None,
                "selfie_status": verification.selfie_status if verification else "pending",
                "created_at": verification.created_at if verification else None,
                "updated_at": verification.updated_at if verification else None
            }
        }
    }
