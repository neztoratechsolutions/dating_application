from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional


class AboutUsCreate(BaseModel):
    name: str
    details: str
    status: bool = True


class AboutUsUpdate(BaseModel):
    name: Optional[str] = None
    details: Optional[str] = None
    status: Optional[bool] = None


class AboutUsResponse(BaseModel):
    id: int
    name: str
    details: str
    status: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )