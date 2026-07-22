from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional


class AdSettingCreate(BaseModel):
    title: str
    description: Optional[str] = None
    placement: str
    status: bool = True


class AdSettingUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    placement: Optional[str] = None
    status: Optional[bool] = None


class AdSettingResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    placement: str
    status: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )