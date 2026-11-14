
from typing import Optional, Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from database import get_db

from models.users import User
from models.kyc_detail import CreatorKYC
from models.creator_bank_details import CreatorBankDetails
from models.creator_verify import CreatorVerification
from models.state import State
from models.creator_account_status import CreatorAccountStatus
from models.fraud_alert import FraudAlert

from models.creator_agreement_acceptance import CreatorAgreementAcceptance
from models.cms_models import CreatorAgreement


router = APIRouter(
    prefix="/kyc/review",
    tags=["KYC REVIEW"]
)


# ==========================================================
# REQUEST SCHEMAS
# ==========================================================

class CreatorRejectRequest(BaseModel):
    reason: str


class CreatorReUploadRequest(BaseModel):
    reason: str


class CreatorSuspendRequest(BaseModel):
    reason: str
    admin_id: Optional[int] = None
    suspend_days: Optional[int] = Field(
        default=None,
        ge=1,
        le=365
    )


class CreatorBanRequest(BaseModel):
    reason: str
    admin_id: Optional[int] = None
    fraud_alert_id: Optional[int] = None


# ==========================================================
# HELPER FUNCTIONS
# ==========================================================

def build_file_url(file_path: Optional[str]):

    if not file_path:
        return None

    if file_path.startswith(("http://", "https://")):
        return file_path

    file_path = file_path.replace("\\", "/").lstrip("/")

    if file_path.startswith("uploads/"):
        return f"/{file_path}"

    return f"/uploads/{file_path}"


def get_overall_kyc_status(
    bank_status,
    selfie_status,
    voice_status
):

    statuses = [
        str(bank_status or "Pending").lower(),
        str(selfie_status or "Pending").lower(),
        str(voice_status or "Pending").lower()
    ]

    if "rejected" in statuses:
        return "Rejected"

    if all(status == "approved" for status in statuses):
        return "Approved"

    if "re-uploaded" in statuses:
        return "Re-uploaded"

    return "Pending"


# ==========================================================
# 1. GET CREATOR KYC REVIEW
# ==========================================================

@router.get("/{user_id}")
def get_creator_kyc_review(
    user_id: int,
    db: Session = Depends(get_db)
):

    # GET CREATOR

    user = db.query(User).filter(
        User.id == user_id,
        User.role == "creator"
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Creator not found"
        )

    # GET CREATOR BANK KYC

    bank_kyc = db.query(CreatorKYC).filter(
        CreatorKYC.user_id == user_id
    ).first()

    # GET BANK ACCOUNT DETAILS

    bank_details_record = db.query(
        CreatorBankDetails
    ).filter(
        CreatorBankDetails.creator_id == user_id
    ).first()

    # GET VOICE AND SELFIE VERIFICATION

    verification = db.query(
        CreatorVerification
    ).filter(
        CreatorVerification.creator_id == user_id
    ).first()

    # GET STATE

    state = None

    if user.state_id:
        state = db.query(State).filter(
            State.id == user.state_id
        ).first()

    # GET ACCOUNT STATUS

    account = db.query(
        CreatorAccountStatus
    ).filter(
        CreatorAccountStatus.creator_id == user_id
    ).first()

    current_account_status = (
        account.status if account else "Active"
    )

    # GET FRAUD SIGNALS

    fraud_alerts = (
        db.query(FraudAlert)
        .filter(FraudAlert.user_id == user_id)
        .order_by(FraudAlert.created_at.desc())
        .all()
    )

    # PERSONAL DETAILS

    personal_details = {
        "creator_id": user.id,
        "creator_code": user.referral_code,
        "display_name": user.display_name,
        "email": user.email,
        "phone": user.phone,
        "state_id": user.state_id,
        "state_name": state.state_name if state else None,
        "profile_photo": build_file_url(user.profile_photo),
        "joined_date": user.created_at
    }

    # BANK DETAILS

    account_number = (
        bank_details_record.account_number
        if bank_details_record else None
    )

    masked_account_number = None

    if account_number:
        account_number = str(account_number)

        masked_account_number = (
            "*" * (len(account_number) - 4) + account_number[-4:]
            if len(account_number) > 4
            else account_number
        )

    bank_details = {
        "bank_image": build_file_url(
            bank_kyc.bank_photo if bank_kyc else None
        ),
        "bank_status": (
            bank_kyc.bank_status if bank_kyc else "Pending"
        ),
        "holder_name": (
            bank_details_record.holder_name
            if bank_details_record else None
        ),
        "account_number": account_number,
        "masked_account_number": masked_account_number,
        "ifsc_code": (
            bank_details_record.ifsc_code
            if bank_details_record else None
        ),
        "bank_name": (
            bank_details_record.bank_name
            if bank_details_record else None
        ),
        "created_at": (
            bank_details_record.created_at
            if bank_details_record else None
        ),
        "updated_at": (
            bank_details_record.updated_at
            if bank_details_record else None
        )
    }

    # SELFIE AND VOICE VERIFICATION

    verification_details = {
        "selfie": {
            "photo": build_file_url(
                verification.selfie_image
                if verification else None
            ),
            "status": (
                verification.selfie_status
                if verification else "Pending"
            )
        },
        "voice": {
            "file": build_file_url(
                verification.voice_file
                if verification else None
            ),
            "duration": (
                verification.voice_duration
                if verification else None
            ),
            "status": (
                verification.voice_status
                if verification else "Pending"
            )
        }
    }

    # OVERALL KYC STATUS

    bank_status = (
        bank_kyc.bank_status if bank_kyc else "Pending"
    )

    selfie_status = (
        verification.selfie_status
        if verification else "Pending"
    )

    voice_status = (
        verification.voice_status
        if verification else "Pending"
    )

    overall_status = get_overall_kyc_status(
        bank_status,
        selfie_status,
        voice_status
    )

    kyc_details = {
        "status": overall_status,
        "bank_status": bank_status,
        "selfie_status": selfie_status,
        "voice_status": voice_status
    }

    # ACCOUNT STATUS

    account_details = {
        "status": current_account_status,
        "reason": account.reason if account else None,
        "action_by": account.action_by if account else None,
        "created_at": account.created_at if account else None,
        "updated_at": account.updated_at if account else None
    }

    # FRAUD SIGNALS

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

    # CREATOR AGREEMENT

    agreement_acceptance = (
        db.query(CreatorAgreementAcceptance)
        .filter(
            CreatorAgreementAcceptance.creator_id == user_id
        )
        .order_by(
            CreatorAgreementAcceptance.created_at.desc()
        )
        .first()
    )

    creator_agreement = None

    if agreement_acceptance:

        creator_agreement = {
            "status": agreement_acceptance.status,
            "date": agreement_acceptance.accepted_at,
            "ip_address": agreement_acceptance.ip_address,
            "agreement_id": agreement_acceptance.agreement_id,
            "agreement_pdf_url": build_file_url(
                agreement_acceptance.agreement_pdf
            )
        }

    # TIMELINE

    timeline = []

    if user.created_at:
        timeline.append({
            "event": "Signup completed",
            "date": user.created_at
        })

    if bank_kyc and bank_kyc.bank_photo:
        timeline.append({
            "event": "Bank image uploaded",
            "date": getattr(
                bank_kyc,
                "created_at",
                None
            )
        })

    if bank_details_record:
        timeline.append({
            "event": "Bank details submitted",
            "date": bank_details_record.created_at
        })

    if verification and verification.selfie_image:
        timeline.append({
            "event": "Selfie uploaded",
            "date": verification.created_at
        })

    if verification and verification.voice_file:
        timeline.append({
            "event": "Voice uploaded",
            "date": verification.created_at
        })

    if agreement_acceptance and agreement_acceptance.accepted_at:
        timeline.append({
            "event": "Creator agreement accepted",
            "date": agreement_acceptance.accepted_at
        })

    for alert in fraud_alerts:
        timeline.append({
            "event": f"Fraud signal detected: {alert.risk_type}",
            "date": alert.created_at
        })

    timeline.sort(
        key=lambda x: x["date"] or user.created_at
    )

    # FINAL RESPONSE

    return {
        "status": True,
        "message": "Creator KYC review details fetched successfully",
        "personal_details": personal_details,
        "bank_details": bank_details,
        "verification_details": verification_details,
        "kyc_details": kyc_details,
        "creator_agreement": creator_agreement,
        "account_status": account_details,
        "fraud_signals": fraud_signals,
        "timeline": timeline
    }


# ==========================================================
# 2. APPROVE CREATOR
# ==========================================================

@router.post("/{creator_id}/approve")
def approve_creator(
    creator_id: int,
    db: Session = Depends(get_db)
):

    try:

        creator = db.query(User).filter(
            User.id == creator_id,
            User.role == "creator"
        ).first()

        if not creator:
            raise HTTPException(
                status_code=404,
                detail="Creator not found"
            )

        bank_kyc = db.query(CreatorKYC).filter(
            CreatorKYC.user_id == creator_id
        ).first()

        bank_details = db.query(CreatorBankDetails).filter(
            CreatorBankDetails.creator_id == creator_id
        ).first()

        verification = db.query(
            CreatorVerification
        ).filter(
            CreatorVerification.creator_id == creator_id
        ).first()

        if not bank_kyc:
            raise HTTPException(
                status_code=404,
                detail="Bank KYC details not found"
            )

        if not bank_details:
            raise HTTPException(
                status_code=404,
                detail="Bank account details not found"
            )

        if not verification:
            raise HTTPException(
                status_code=404,
                detail="Creator verification details not found"
            )

        # APPROVE BANK IMAGE AND BANK DETAILS

        bank_kyc.bank_status = "Approved"

        # APPROVE SELFIE

        verification.selfie_status = "Approved"

        # APPROVE VOICE

        verification.voice_status = "Approved"

        db.commit()

        return {
            "status": True,
            "message": "Creator verification approved successfully",
            "creator_id": creator_id,
            "bank_status": bank_kyc.bank_status,
            "selfie_status": verification.selfie_status,
            "voice_status": verification.voice_status,
            "kyc_status": "Approved"
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to approve creator: {str(e)}"
        )


# ==========================================================
# 3. REJECT CREATOR
# ==========================================================

@router.post("/{creator_id}/reject")
def reject_creator(
    creator_id: int,
    data: CreatorRejectRequest,
    db: Session = Depends(get_db)
):

    try:

        creator = db.query(User).filter(
            User.id == creator_id,
            User.role == "creator"
        ).first()

        if not creator:
            raise HTTPException(
                status_code=404,
                detail="Creator not found"
            )

        bank_kyc = db.query(CreatorKYC).filter(
            CreatorKYC.user_id == creator_id
        ).first()

        bank_details = db.query(CreatorBankDetails).filter(
            CreatorBankDetails.creator_id == creator_id
        ).first()

        verification = db.query(
            CreatorVerification
        ).filter(
            CreatorVerification.creator_id == creator_id
        ).first()

        if not bank_kyc:
            raise HTTPException(
                status_code=404,
                detail="Bank KYC details not found"
            )

        if not bank_details:
            raise HTTPException(
                status_code=404,
                detail="Bank account details not found"
            )

        if not verification:
            raise HTTPException(
                status_code=404,
                detail="Creator verification details not found"
            )

        reason = data.reason.strip()

        if not reason:
            raise HTTPException(
                status_code=400,
                detail="Rejection reason is required"
            )

        bank_kyc.bank_status = "Rejected"
        verification.selfie_status = "Rejected"
        verification.voice_status = "Rejected"

        db.commit()

        return {
            "status": True,
            "message": "Creator verification rejected successfully",
            "creator_id": creator_id,
            "bank_status": bank_kyc.bank_status,
            "selfie_status": verification.selfie_status,
            "voice_status": verification.voice_status,
            "kyc_status": "Rejected",
            "reason": reason
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reject creator: {str(e)}"
        )


# ==========================================================
# 4. RE-UPLOAD CREATOR
# ==========================================================

@router.post("/{creator_id}/re-upload")
def reupload_creator_kyc(
    creator_id: int,
    data: CreatorReUploadRequest,
    db: Session = Depends(get_db)
):

    try:

        creator = db.query(User).filter(
            User.id == creator_id,
            User.role == "creator"
        ).first()

        if not creator:
            raise HTTPException(
                status_code=404,
                detail="Creator not found"
            )

        bank_kyc = db.query(CreatorKYC).filter(
            CreatorKYC.user_id == creator_id
        ).first()

        verification = db.query(
            CreatorVerification
        ).filter(
            CreatorVerification.creator_id == creator_id
        ).first()

        if not bank_kyc:
            raise HTTPException(
                status_code=404,
                detail="Bank KYC details not found"
            )

        if not verification:
            raise HTTPException(
                status_code=404,
                detail="Creator verification details not found"
            )

        reason = data.reason.strip()

        if not reason:
            raise HTTPException(
                status_code=400,
                detail="Re-upload reason is required"
            )

        bank_kyc.bank_status = "Re-uploaded"
        verification.selfie_status = "Re-uploaded"
        verification.voice_status = "Re-uploaded"

        db.commit()

        return {
            "status": True,
            "message": "Creator verification marked for re-upload successfully",
            "creator_id": creator_id,
            "bank_status": bank_kyc.bank_status,
            "selfie_status": verification.selfie_status,
            "voice_status": verification.voice_status,
            "reason": reason
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to request re-upload: {str(e)}"
        )


# ==========================================================
# 5. SUSPEND CREATOR
# ==========================================================

@router.post("/{creator_id}/suspend")
def suspend_creator(
    creator_id: int,
    data: CreatorSuspendRequest,
    db: Session = Depends(get_db)
):

    try:

        creator = db.query(User).filter(
            User.id == creator_id,
            User.role == "creator"
        ).first()

        if not creator:
            raise HTTPException(
                status_code=404,
                detail="Creator not found"
            )

        reason = data.reason.strip()

        if not reason:
            raise HTTPException(
                status_code=400,
                detail="Suspension reason is required"
            )

        account = db.query(
            CreatorAccountStatus
        ).filter(
            CreatorAccountStatus.creator_id == creator_id
        ).first()

        if account and account.status == "Banned":
            raise HTTPException(
                status_code=403,
                detail="Banned creator cannot be suspended"
            )

        if not account:
            account = CreatorAccountStatus(
                creator_id=creator_id
            )
            db.add(account)

        account.status = "Suspended"
        account.reason = reason
        account.action_by = data.admin_id

        db.commit()
        db.refresh(account)

        return {
            "status": True,
            "message": "Creator suspended successfully",
            "creator_id": creator_id,
            "account_status": account.status,
            "reason": account.reason,
            "admin_id": data.admin_id,
            "suspend_days": data.suspend_days
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to suspend creator: {str(e)}"
        )


# ==========================================================
# 6. BAN CREATOR
# ==========================================================

@router.post("/{creator_id}/ban")
def ban_creator(
    creator_id: int,
    data: CreatorBanRequest,
    db: Session = Depends(get_db)
):

    try:

        creator = db.query(User).filter(
            User.id == creator_id,
            User.role == "creator"
        ).first()

        if not creator:
            raise HTTPException(
                status_code=404,
                detail="Creator not found"
            )

        reason = data.reason.strip()

        if not reason:
            raise HTTPException(
                status_code=400,
                detail="Ban reason is required"
            )

        account = db.query(
            CreatorAccountStatus
        ).filter(
            CreatorAccountStatus.creator_id == creator_id
        ).first()

        if not account:
            account = CreatorAccountStatus(
                creator_id=creator_id
            )
            db.add(account)

        account.status = "Banned"
        account.reason = reason
        account.action_by = data.admin_id

        db.commit()
        db.refresh(account)

        return {
            "status": True,
            "message": "Creator permanently banned successfully",
            "creator_id": creator_id,
            "account_status": account.status,
            "reason": account.reason,
            "admin_id": data.admin_id,
            "fraud_alert_id": data.fraud_alert_id
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to ban creator: {str(e)}"
        )


# ==========================================================
# 7. GET SUSPENDED / BANNED CREATORS
# ==========================================================

@router.get("/account-status/{status}")
def get_creators_by_account_status(
    status: Literal["Suspended", "Banned"],
    db: Session = Depends(get_db)
):

    accounts = (
        db.query(CreatorAccountStatus)
        .join(
            User,
            User.id == CreatorAccountStatus.creator_id
        )
        .filter(
            CreatorAccountStatus.status == status,
            User.role == "creator"
        )
        .order_by(
            CreatorAccountStatus.updated_at.desc()
        )
        .all()
    )

    data = []

    for account in accounts:

        creator = db.query(User).filter(
            User.id == account.creator_id,
            User.role == "creator"
        ).first()

        if not creator:
            continue

        bank_kyc = db.query(CreatorKYC).filter(
            CreatorKYC.user_id == creator.id
        ).first()

        verification = db.query(
            CreatorVerification
        ).filter(
            CreatorVerification.creator_id == creator.id
        ).first()

        state = None

        if creator.state_id:
            state = db.query(State).filter(
                State.id == creator.state_id
            ).first()

        bank_status = (
            bank_kyc.bank_status if bank_kyc else "Pending"
        )

        selfie_status = (
            verification.selfie_status
            if verification else "Pending"
        )

        voice_status = (
            verification.voice_status
            if verification else "Pending"
        )

        data.append({
            "creator_id": creator.id,
            "creator_code": creator.referral_code,
            "name": creator.display_name,
            "email": creator.email,
            "phone": creator.phone,
            "profile_photo": build_file_url(
                creator.profile_photo
            ),
            "state": state.state_name if state else None,
            "kyc_status": get_overall_kyc_status(
                bank_status,
                selfie_status,
                voice_status
            ),
            "bank_status": bank_status,
            "selfie_status": selfie_status,
            "voice_status": voice_status,
            "account_status": account.status,
            "reason": account.reason,
            "action_by": account.action_by,
            "created_at": account.created_at,
            "updated_at": account.updated_at
        })

    return {
        "status": True,
        "message": f"{status} creators fetched successfully",
        "total": len(data),
        "data": data
    }
