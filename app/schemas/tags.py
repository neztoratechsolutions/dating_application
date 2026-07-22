from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional


class TagCreate(BaseModel):
    user_id: int
    tag_name: str


class TagUpdate(BaseModel):
    tag_name: Optional[str] = None


class TagResponse(BaseModel):
    id: int
    user_id: int
    tag_name: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )