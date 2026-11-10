from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ==========================================================
# CREATE KYC RESPONSE
# ==========================================================

class KYCResponse(BaseModel):

    id: int
    user_id: int

    aadhar_photo: str
    pan_photo: str
    selfie_photo: str

    aadhar_status: str
    pan_status: str
    selfie_status: str

    status: str
    rejection_reason: Optional[str] = None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


# ==========================================================
# ADMIN KYC LIST RESPONSE
# ==========================================================

class KYCAdminResponse(BaseModel):

    id: int
    user_id: int

    creator_id: str

    display_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

    state_id: Optional[int] = None
    state_name: Optional[str] = None

    profile_photo: Optional[str] = None

    joined_date: datetime

    aadhar_photo: str
    pan_photo: str
    selfie_photo: str

    aadhar_status: str
    pan_status: str
    selfie_status: str

    status: str
    rejection_reason: Optional[str] = None

    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


# ==========================================================
# DOCUMENT STATUS UPDATE
# ==========================================================

class KYCDocumentStatusUpdate(BaseModel):

    aadhar_status: Optional[str] = None
    pan_status: Optional[str] = None
    selfie_status: Optional[str] = None

    rejection_reason: Optional[str] = None


# ==========================================================
# OVERALL STATUS UPDATE
# ==========================================================

class KYCOverallStatusUpdate(BaseModel):

    status: str

    rejection_reason: Optional[str] = None


# ==========================================================
# DASHBOARD SUMMARY
# ==========================================================

class KYCDashboardSummary(BaseModel):

    total_creators: int
    pending_kyc: int
    approved: int
    rejected: int
    re_upload: int
    completed_today: int