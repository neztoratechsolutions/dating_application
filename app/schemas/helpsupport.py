from datetime import datetime

from pydantic import BaseModel, ConfigDict


class HelpSupportCreate(BaseModel):
    question: str
    answer: str
    is_active: bool = True


class HelpSupportUpdate(BaseModel):
    question: str | None = None
    answer: str | None = None
    is_active: bool | None = None


class HelpSupportResponse(BaseModel):
    id: int
    question: str
    answer: str
    is_active: bool
    created_at: datetime | None
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)