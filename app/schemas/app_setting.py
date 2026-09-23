from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr
from typing import Optional


class AppSettingResponse(BaseModel):
    id: int
    app_name: str
    logo: Optional[str]
    favicon: Optional[str]
    support_email: Optional[str]
    support_number: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )