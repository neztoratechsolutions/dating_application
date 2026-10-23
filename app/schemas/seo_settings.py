from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional


class SEOSettingCreate(BaseModel):
    meta_title: str
    meta_description: Optional[str] = None
    status: bool = True


class SEOSettingUpdate(BaseModel):
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    status: Optional[bool] = None


class SEOSettingResponse(BaseModel):
    id: int
    meta_title: str
    meta_description: Optional[str]
    status: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )