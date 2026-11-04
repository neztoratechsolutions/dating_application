from datetime import datetime
from pydantic import BaseModel, ConfigDict


class PrivacyPolicyCreate(BaseModel):
    details: str


class PrivacyPolicyUpdate(BaseModel):
    details: str | None = None
    status: bool | None = None


class PrivacyPolicyResponse(BaseModel):
    id: int
    details: str
    status: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )