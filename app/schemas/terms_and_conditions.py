from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional


class TermsAndConditionCreate(BaseModel):
    details: str
    status: bool = True


class TermsAndConditionUpdate(BaseModel):
    details: Optional[str] = None
    status: Optional[bool] = None


class TermsAndConditionResponse(BaseModel):
    id: int
    details: str
    status: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )