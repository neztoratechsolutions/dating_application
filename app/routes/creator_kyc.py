import os
import uuid

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    UploadFile,
    HTTPException,
    status
)

from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models.users import User
from models.kyc_detail import CreatorKYC
from models.creator_bank_details import CreatorBankDetails
from models.creator_verify import CreatorVerification
from typing import Literal

router = APIRouter(
    prefix="/creator-kyc",
    tags=["Creator KYC"]
)


# ============================================================
# BANK IMAGE UPLOAD
# ============================================================

@router.post("/bank-photo")
async def upload_bank_photo(
    user_id: int = Form(...),
    bank_photo: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # --------------------------------------------------------
    # Check user
    # --------------------------------------------------------

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # --------------------------------------------------------
    # Validate image
    # --------------------------------------------------------

    if not bank_photo.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bank image is required"
        )

    allowed_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp"
    }

    file_extension = os.path.splitext(
        bank_photo.filename
    )[1].lower()

    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPG, JPEG, PNG and WEBP images are allowed"
        )

    # --------------------------------------------------------
    # Upload directory
    # --------------------------------------------------------

    upload_directory = "uploads/creator_kyc/bank"

    os.makedirs(
        upload_directory,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Generate unique filename
    # --------------------------------------------------------

    unique_filename = (
        f"bank_{user_id}_"
        f"{uuid.uuid4().hex}"
        f"{file_extension}"
    )

    file_path = os.path.join(
        upload_directory,
        unique_filename
    )

    # --------------------------------------------------------
    # Save image
    # --------------------------------------------------------

    content = await bank_photo.read()

    with open(file_path, "wb") as file:
        file.write(content)

    # --------------------------------------------------------
    # Check existing Creator KYC
    # --------------------------------------------------------

    creator_kyc = db.query(CreatorKYC).filter(
        CreatorKYC.user_id == user_id
    ).first()

    # --------------------------------------------------------
    # Create new record
    # --------------------------------------------------------

    if not creator_kyc:

        creator_kyc = CreatorKYC(
            user_id=user_id,
            bank_photo=file_path
        )

        db.add(creator_kyc)

    # --------------------------------------------------------
    # Update existing record
    # --------------------------------------------------------

    else:

        # Delete old image
        if creator_kyc.bank_photo:
            old_file_path = creator_kyc.bank_photo

            if os.path.exists(old_file_path):
                try:
                    os.remove(old_file_path)
                except OSError:
                    pass

        creator_kyc.bank_photo = file_path

    # --------------------------------------------------------
    # Save database
    # --------------------------------------------------------

    db.commit()
    db.refresh(creator_kyc)

    # --------------------------------------------------------
    # Response
    # --------------------------------------------------------

    return {
        "status": 200,
        "message": "Bank image uploaded successfully",
        "data": {
            "id": creator_kyc.id,
            "user_id": creator_kyc.user_id,
            "bank_photo": creator_kyc.bank_photo
        }
    }


# ============================================================
# STATUS UPDATE SCHEMA
# ============================================================

class CreatorKYCStatusUpdate(BaseModel):
    bank_status: str


# ============================================================
# GET ALL CREATOR KYC
# ============================================================

@router.get("")
def get_all_creator_kyc(
    db: Session = Depends(get_db)
):
    creator_kycs = db.query(CreatorKYC).all()

    if not creator_kycs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Creator KYC data not found"
        )

    data = []

    for creator_kyc in creator_kycs:
        data.append({
            "user_id": creator_kyc.user_id,
            "bank_photo": creator_kyc.bank_photo,
            "bank_status": creator_kyc.bank_status,
            "created_at": creator_kyc.created_at,
            "updated_at": creator_kyc.updated_at
        })

    return {
        "status": 200,
        "message": "Creator KYC details fetched successfully",
        "data": data
    }


# ============================================================
# GET CREATOR KYC BY USER ID
# ============================================================

@router.get("/{user_id}")
def get_creator_kyc_by_user_id(
    user_id: int,
    db: Session = Depends(get_db)
):
    # --------------------------------------------------------
    # Check user
    # --------------------------------------------------------

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # --------------------------------------------------------
    # Get Creator KYC
    # --------------------------------------------------------

    creator_kyc = db.query(CreatorKYC).filter(
        CreatorKYC.user_id == user_id
    ).first()

    if not creator_kyc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Creator KYC data not found"
        )

    return {
        "status": 200,
        "message": "Creator KYC details fetched successfully",
        "data": {
            "user_id": creator_kyc.user_id,
            "bank_photo": creator_kyc.bank_photo,
            "bank_status": creator_kyc.bank_status,
            "created_at": creator_kyc.created_at,
            "updated_at": creator_kyc.updated_at
        }
    }


# ============================================================
# ADMIN - UPDATE BANK STATUS BY USER ID
# ============================================================

# @router.put("/{user_id}/status")
# def update_creator_kyc_status(
#     user_id: int,
#     request: CreatorKYCStatusUpdate,
#     db: Session = Depends(get_db)
# ):
#     # --------------------------------------------------------
#     # Check user
#     # --------------------------------------------------------

#     user = db.query(User).filter(
#         User.id == user_id
#     ).first()

#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="User not found"
#         )

#     # --------------------------------------------------------
#     # Get Creator KYC
#     # --------------------------------------------------------

#     creator_kyc = db.query(CreatorKYC).filter(
#         CreatorKYC.user_id == user_id
#     ).first()

#     if not creator_kyc:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Creator KYC data not found"
#         )

#     # --------------------------------------------------------
#     # Validate status
#     # --------------------------------------------------------

#     allowed_statuses = {
#         "Pending",
#         "Approved",
#         "Rejected"
#     }

#     if request.bank_status not in allowed_statuses:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Invalid status. Use Pending, Approved or Rejected"
#         )

#     # --------------------------------------------------------
#     # Update status
#     # --------------------------------------------------------

#     creator_kyc.bank_status = request.bank_status

#     db.commit()
#     db.refresh(creator_kyc)

#     return {
#         "status": 200,
#         "message": "Bank status updated successfully",
#         "data": {
#             "user_id": creator_kyc.user_id,
#             "bank_photo": creator_kyc.bank_photo,
#             "bank_status": creator_kyc.bank_status
#         }
#     }

@router.put("/{user_id}/status")
def update_creator_kyc_status(
    user_id: int,
    request: CreatorKYCStatusUpdate,
    db: Session = Depends(get_db)
):
    try:
        # --------------------------------------------------------
        # Check user
        # --------------------------------------------------------

        user = db.query(User).filter(
            User.id == user_id,
            User.role == "creator"
        ).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Creator not found"
            )

        # --------------------------------------------------------
        # Check Creator Bank Details
        # --------------------------------------------------------

        bank_details = db.query(CreatorBankDetails).filter(
            CreatorBankDetails.creator_id == user_id
        ).first()

        if not bank_details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Creator bank details not found"
            )

        # --------------------------------------------------------
        # Check Creator Verification
        # --------------------------------------------------------

        verification = db.query(CreatorVerification).filter(
            CreatorVerification.creator_id == user_id
        ).first()

        if not verification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Creator verification data not found"
            )

        # --------------------------------------------------------
        # Validate Voice and Selfie Verification
        # --------------------------------------------------------

        if request.bank_status == "Approved":

            if (
                verification.voice_status.lower() != "approved"
                or verification.selfie_status.lower() != "approved"
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Voice and selfie verification must be approved first"
                )

        # --------------------------------------------------------
        # Update Bank Status
        # --------------------------------------------------------

        bank_details.bank_status = request.bank_status

        db.commit()
        db.refresh(bank_details)

        return {
            "status": 200,
            "message": "Bank status updated successfully",
            "data": {
                "user_id": user_id,
                "holder_name": bank_details.holder_name,
                "account_number": bank_details.account_number,
                "ifsc_code": bank_details.ifsc_code,
                "bank_name": bank_details.bank_name,
                "bank_status": bank_details.bank_status,
                "voice_status": verification.voice_status,
                "selfie_status": verification.selfie_status
            }
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update bank status: {str(e)}"
        )
