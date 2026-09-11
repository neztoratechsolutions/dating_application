from datetime import datetime
from pydantic import BaseModel
from app.models.settings import Setting


class SettingCreate(BaseModel):
    availability_hour: str


class SettingResponse(BaseModel):
    id: int
    user_id: int
    availability_hour: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True