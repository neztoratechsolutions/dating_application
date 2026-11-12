from typing import Optional, Literal
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from database import get_db

from models.users import User
from models.kyc_detail import KYCDetail, CreatorKYC
from models.creator_bank_details import CreatorBankDetails
from models.state import State
from models.creator_account_status import CreatorAccountStatus
from models.fraud_alert import FraudAlert
from models.fraud_action_log import FraudActionLog

# Creator Agreement models
from models.creator_agreement_acceptance import CreatorAgreementAcceptance
from models.cms_models import CreatorAgreement


router = APIRouter(
    prefix="/kyc/review",
    tags=["KYC REVIEW"]
)


# ==========================================================
# REQUEST SCHEMAS
# ==========================================================

class CreatorStatusUpdate(BaseModel):

    status: Literal[
        "Approved",
        "Rejected",
        "Re-upload Required"
    ]

    reason: Optional[str] = None

    document: Optional[
        Literal["aadhar", "pan", "selfie"]
    ] = None


class CreatorAccountStatusUpdate(BaseModel):

    status: Literal[
        "Suspended",
        "Banned"
    ]

    reason: str

    admin_id: Optional[int] = None

    fraud_alert_id: Optional[int] = None

    suspend_days: Optional[int] = Field(
        default=None,
        ge=1,
        le=365
    )


# ==========================================================
# HELPER FUNCTION
# ==========================================================

def build_file_url(file_path: Optional[str]):

    if not file_path:
        return None

    if file_path.startswith("http://"):
        return file_path

    if file_path.startswith("https://"):
        return file_path

    return f"/uploads/{file_path.lstrip('/').replace('uploads/', '')}"


# ==========================================================
# 1. GET CREATOR KYC REVIEW
# ==========================================================

@router.get("/{user_id}")
def get_creator_kyc_review(
    user_id: int,
    db: Session = Depends(get_db)
):

    # ======================================================
    # GET CREATOR
    # ======================================================

    user = db.query(User).filter(
        User.id == user_id,
        User.role == "creator"
    ).first()

    if not user:

        raise HTTPException(
            status_code=404,
            detail="Creator not found"
        )

    # ======================================================
    # GET KYC DETAILS
    # ======================================================

    kyc = db.query(KYCDetail).filter(
        KYCDetail.user_id == user_id
    ).first()

    # ======================================================
    # GET BANK KYC DETAILS
    # ======================================================

    bank_kyc = db.query(CreatorKYC).filter(
        CreatorKYC.user_id == user_id
    ).first()

    # ======================================================
    # GET CREATOR BANK ACCOUNT DETAILS
    # ======================================================

    bank_details_record = db.query(
        CreatorBankDetails
    ).filter(
        CreatorBankDetails.creator_id == user_id
    ).first()

    # ======================================================
    # GET STATE
    # ======================================================

    state = None

    if user.state_id:

        state = db.query(State).filter(
            State.id == user.state_id
        ).first()

    # ======================================================
    # GET ACCOUNT STATUS
    # ======================================================

    account = db.query(CreatorAccountStatus).filter(
        CreatorAccountStatus.creator_id == user_id
    ).first()

    current_account_status = (
        account.status
        if account
        else "Active"
    )

    # ======================================================
    # GET FRAUD SIGNALS
    # ======================================================

    fraud_alerts = (
        db.query(FraudAlert)
        .filter(
            FraudAlert.user_id == user_id
        )
        .order_by(
            FraudAlert.created_at.desc()
        )
        .all()
    )

    # ======================================================
    # PERSONAL DETAILS
    # ======================================================

    personal_details = {

        "creator_id": user.id,

        "creator_code": user.referral_code,

        "display_name": user.display_name,

        "email": user.email,

        "phone": user.phone,

        "state_id": user.state_id,

        "state_name": (
            state.state_name
            if state
            else None
        ),

        "profile_photo": build_file_url(
            user.profile_photo
        ),

        "joined_date": user.created_at
    }

    # ======================================================
    # BANK DETAILS
    # ======================================================

    bank_details = {

        # Existing bank KYC document details
        "bank_photo": build_file_url(
            bank_kyc.bank_photo
            if bank_kyc
            else None
        ),

        "bank_status": (
            bank_kyc.bank_status
            if bank_kyc
            else "Pending"
        ),

        # New creator bank account details
        "holder_name": (
            bank_details_record.holder_name
            if bank_details_record
            else None
        ),

        "account_number": (
            bank_details_record.account_number
            if bank_details_record
            else None
        ),

        "masked_account_number": None,

        "ifsc_code": (
            bank_details_record.ifsc_code
            if bank_details_record
            else None
        ),

        "bank_name": (
            bank_details_record.bank_name
            if bank_details_record
            else None
        ),

        "created_at": (
            bank_details_record.created_at
            if bank_details_record
            else None
        ),

        "updated_at": (
            bank_details_record.updated_at
            if bank_details_record
            else None
        )
    }

    # ======================================================
    # MASK ACCOUNT NUMBER
    # ======================================================

    account_number = bank_details["account_number"]

    if account_number:

        account_number = str(account_number)

        if len(account_number) > 4:

            bank_details["masked_account_number"] = (
                "*" * (
                    len(account_number) - 4
                )
                + account_number[-4:]
            )

        else:

            bank_details["masked_account_number"] = (
                account_number
            )

    # ======================================================
    # DOCUMENTS
    # ======================================================

    documents = {

        "aadhar_front": {

            "photo": build_file_url(
                kyc.aadhar_photo
                if kyc
                else None
            ),

            "status": (
                kyc.aadhar_status
                if kyc
                else "Pending"
            )
        },

        "aadhar_back": {

            "photo": build_file_url(
                getattr(
                    kyc,
                    "aadhar_back_photo",
                    None
                )
                if kyc
                else None
            ),

            "status": (
                getattr(
                    kyc,
                    "aadhar_back_status",
                    None
                )
                if kyc
                else None
            )
        },

        "pan": {

            "photo": build_file_url(
                kyc.pan_photo
                if kyc
                else None
            ),

            "status": (
                kyc.pan_status
                if kyc
                else "Pending"
            )
        },

        "selfie": {

            "photo": build_file_url(
                kyc.selfie_photo
                if kyc
                else None
            ),

            "status": (
                kyc.selfie_status
                if kyc
                else "Pending"
            )
        }
    }

    # ======================================================
    # OVERALL KYC STATUS
    # ======================================================

    kyc_details = {

        "status": (
            kyc.status
            if kyc
            else "Pending"
        ),

        "rejection_reason": (
            kyc.rejection_reason
            if kyc
            else None
        ),

        "created_at": (
            kyc.created_at
            if kyc
            else None
        ),

        "updated_at": (
            kyc.updated_at
            if kyc
            else None
        )
    }

    # ======================================================
    # ACCOUNT STATUS
    # ======================================================

    account_details = {

        "status": current_account_status,

        "reason": (
            account.reason
            if account
            else None
        ),

        "action_by": (
            account.action_by
            if account
            else None
        ),

        "created_at": (
            account.created_at
            if account
            else None
        ),

        "updated_at": (
            account.updated_at
            if account
            else None
        )
    }

    # ======================================================
    # FRAUD SIGNALS
    # ======================================================

    fraud_signals = [

        {
            "fraud_alert_id": alert.id,

            "alert_code": alert.alert_code,

            "risk_score": alert.risk_score,

            "risk_level": alert.risk_level,

            "risk_type": alert.risk_type,

            "description": alert.description,

            "state_id": alert.state_id,

            "status": alert.status,

            "created_at": alert.created_at
        }

        for alert in fraud_alerts
    ]

    # ======================================================
    # CREATOR AGREEMENT
    # ======================================================

    agreement_acceptance = (
        db.query(
            CreatorAgreementAcceptance
        )
        .filter(
            CreatorAgreementAcceptance.creator_id
            == user_id
        )
        .order_by(
            CreatorAgreementAcceptance.created_at.desc()
        )
        .first()
    )

    creator_agreement = None

    if agreement_acceptance:

        agreement = db.query(
            CreatorAgreement
        ).filter(
            CreatorAgreement.id
            == agreement_acceptance.agreement_id
        ).first()

        agreement_pdf_url = None

        if agreement_acceptance.agreement_pdf:

            agreement_pdf_url = build_file_url(
                agreement_acceptance.agreement_pdf
            )

        creator_agreement = {

            "status": agreement_acceptance.status,

            "date": agreement_acceptance.accepted_at,

            "ip_address": agreement_acceptance.ip_address,

            "agreement_id": (
                agreement_acceptance.agreement_id
            ),

            "agreement_details": (
                agreement.details
                if agreement
                else None
            ),

            "agreement_pdf_url": agreement_pdf_url
        }

    # ======================================================
    # TIMELINE
    # ======================================================

    timeline = []

    # Signup

    if user.created_at:

        timeline.append({

            "event": "Signup completed",

            "date": user.created_at
        })

    # Aadhaar

    if kyc and kyc.aadhar_photo:

        timeline.append({

            "event": "Aadhaar uploaded",

            "date": getattr(
                kyc,
                "aadhar_uploaded_at",
                None
            ) or kyc.created_at
        })

    # PAN

    if kyc and kyc.pan_photo:

        timeline.append({

            "event": "PAN uploaded",

            "date": getattr(
                kyc,
                "pan_uploaded_at",
                None
            ) or kyc.created_at
        })

    # Selfie

    if kyc and kyc.selfie_photo:

        timeline.append({

            "event": "Selfie captured",

            "date": getattr(
                kyc,
                "selfie_uploaded_at",
                None
            ) or kyc.created_at
        })

    # KYC Submitted

    if kyc:

        timeline.append({

            "event": "KYC submitted for review",

            "date": getattr(
                kyc,
                "submitted_at",
                None
            ) or kyc.created_at
        })

    # Fraud timeline

    for alert in fraud_alerts:

        timeline.append({

            "event": (
                f"Fraud signal detected: "
                f"{alert.risk_type}"
            ),

            "date": alert.created_at
        })

    # Sort timeline

    timeline.sort(
        key=lambda x: (
            x["date"]
            or user.created_at
        )
    )

    # ======================================================
    # FINAL RESPONSE
    # ======================================================

    return {

        "status": True,

        "message": (
            "Creator KYC review details "
            "fetched successfully"
        ),

        "personal_details": personal_details,

        "bank_details": bank_details,

        "documents": documents,

        "creator_agreement": creator_agreement,

        "kyc_details": kyc_details,

        "account_status": account_details,

        "fraud_signals": fraud_signals,

        "timeline": timeline
    }


# ==========================================================
# 2. UPDATE CREATOR KYC STATUS
# ==========================================================

@router.post("/{creator_id}/status")
def update_creator_review_status(

    creator_id: int,

    data: CreatorStatusUpdate,

    db: Session = Depends(get_db)
):

    try:

        # ==================================================
        # CHECK CREATOR
        # ==================================================

        creator = db.query(User).filter(
            User.id == creator_id,
            User.role == "creator"
        ).first()

        if not creator:

            raise HTTPException(
                status_code=404,
                detail="Creator not found"
            )

        # ==================================================
        # GET KYC
        # ==================================================

        kyc = db.query(KYCDetail).filter(
            KYCDetail.user_id == creator_id
        ).first()

        # ==================================================
        # GET ACCOUNT STATUS
        # ==================================================

        account = db.query(
            CreatorAccountStatus
        ).filter(
            CreatorAccountStatus.creator_id
            == creator_id
        ).first()

        # ==================================================
        # PERMANENT BAN CHECK
        # ==================================================

        if account and account.status == "Banned":

            raise HTTPException(
                status_code=403,
                detail=(
                    "Permanently banned creator "
                    "status cannot be changed"
                )
            )

        # ==================================================
        # CLEAN REASON
        # ==================================================

        reason = (
            data.reason.strip()
            if data.reason
            else None
        )

        # ==================================================
        # REASON VALIDATION
        # ==================================================

        if data.status in [
            "Rejected",
            "Re-upload Required"
        ]:

            if not reason:

                raise HTTPException(
                    status_code=400,
                    detail="Reason is required"
                )

        # ==================================================
        # APPROVED
        # ==================================================

        if data.status == "Approved":

            if not kyc:

                raise HTTPException(
                    status_code=404,
                    detail="KYC details not found"
                )

            kyc.aadhar_status = "Verified"

            kyc.pan_status = "Verified"

            kyc.selfie_status = "Verified"

            kyc.status = "Approved"

            kyc.rejection_reason = None

            message = (
                "Creator KYC approved successfully"
            )

        # ==================================================
        # REJECTED
        # ==================================================

        elif data.status == "Rejected":

            if not kyc:

                raise HTTPException(
                    status_code=404,
                    detail="KYC details not found"
                )

            kyc.status = "Rejected"

            kyc.rejection_reason = reason

            message = (
                "Creator KYC rejected successfully"
            )

        # ==================================================
        # RE-UPLOAD REQUIRED
        # ==================================================

        elif data.status == "Re-upload Required":

            if not data.document:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Document is required "
                        "for re-upload"
                    )
                )

            if not kyc:

                raise HTTPException(
                    status_code=404,
                    detail="KYC details not found"
                )

            if data.document == "aadhar":

                kyc.aadhar_status = "Re-upload"

            elif data.document == "pan":

                kyc.pan_status = "Re-upload"

            elif data.document == "selfie":

                kyc.selfie_status = "Re-upload"

            kyc.status = "Re-upload Required"

            kyc.rejection_reason = reason

            message = (
                f"{data.document} re-upload "
                "requested successfully"
            )

        # ==================================================
        # SAVE
        # ==================================================

        db.commit()

        db.refresh(kyc)

        return {

            "status": True,

            "message": message,

            "creator_id": creator_id,

            "kyc_status": kyc.status,

            "reason": kyc.rejection_reason
        }

    except HTTPException:

        db.rollback()

        raise

    except Exception as e:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to update creator KYC status: "
                f"{str(e)}"
            )
        )


# ==========================================================
# 3. GET SUSPENDED / BANNED CREATORS
# ==========================================================

@router.get("/account-status/{status}")
def get_creators_by_account_status(

    status: Literal[
        "Suspended",
        "Banned"
    ],

    db: Session = Depends(get_db)
):

    # ======================================================
    # GET ACCOUNT STATUS RECORDS
    # ======================================================

    accounts = (
        db.query(
            CreatorAccountStatus
        )
        .join(
            User,
            User.id ==
            CreatorAccountStatus.creator_id
        )
        .filter(
            CreatorAccountStatus.status
            == status,

            User.role == "creator"
        )
        .order_by(
            CreatorAccountStatus.updated_at.desc()
        )
        .all()
    )

    data = []

    # ======================================================
    # BUILD RESPONSE
    # ======================================================

    for account in accounts:

        creator = db.query(User).filter(
            User.id == account.creator_id,
            User.role == "creator"
        ).first()

        if not creator:
            continue

        kyc = db.query(KYCDetail).filter(
            KYCDetail.user_id
            == creator.id
        ).first()

        state = None

        if creator.state_id:

            state = db.query(
                State
            ).filter(
                State.id ==
                creator.state_id
            ).first()

        data.append({

            "creator_id": creator.id,

            "creator_code": (
                creator.referral_code
            ),

            "name": (
                creator.display_name
            ),

            "email": creator.email,

            "phone": creator.phone,

            "profile_photo": build_file_url(
                creator.profile_photo
            ),

            "state": (
                state.state_name
                if state
                else None
            ),

            "kyc_status": (
                kyc.status
                if kyc
                else "Pending"
            ),

            "account_status": account.status,

            "reason": account.reason,

            "action_by": account.action_by,

            "created_at": account.created_at,

            "updated_at": account.updated_at
        })

    # ======================================================
    # RESPONSE
    # ======================================================

    return {

        "status": True,

        "message": (
            f"{status} creators "
            "fetched successfully"
        ),

        "total": len(data),

        "data": data
    }