from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional


class CommunityGuidelineCreate(BaseModel):
    details: str
    status: bool = True


class CommunityGuidelineUpdate(BaseModel):
    details: Optional[str] = None
    status: Optional[bool] = None


class CommunityGuidelineResponse(BaseModel):
    id: int
    details: str
    status: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )