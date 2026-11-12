from datetime import datetime
from typing import Optional
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


class CreateFraudAlert(BaseModel):
    admin_id: int
    user_id: int

    state_id: Optional[int] = None

    risk_type: str = Field(
        min_length=2,
        max_length=100
    )

    risk_level: Literal["low", "medium", "high"] = "medium"

    description: Optional[str] = None

    risk_score: Optional[int] = Field(
        default=None,
        ge=0,
        le=100
    )



class UpdateFraudAlert(BaseModel):
    admin_id: int
    risk_type: Optional[str] = Field(default=None, min_length=2, max_length=100)
    description: Optional[str] = None
    risk_score: Optional[int] = Field(default=None, ge=0, le=100)
    status: Optional[str] = None


class AdminActionRequest(BaseModel):
    admin_id: int
    remarks: Optional[str] = None


class SuspendRequest(BaseModel):
    admin_id: int
    remarks: Optional[str] = None
    suspend_until: Optional[datetime] = None


class FraudAlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    alert_code: str
    user_id: int
    risk_score: int
    risk_level: str
    risk_type: str
    description: Optional[str]
    state_id: Optional[int]
    status: str
    created_at: Optional[datetime]