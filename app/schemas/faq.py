from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional


class FAQCreate(BaseModel):
    question: str
    answer: str
    created_by: Optional[int] = None
    status: bool = True


class FAQUpdate(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None
    created_by: Optional[int] = None
    status: Optional[bool] = None


class FAQResponse(BaseModel):
    id: int
    question: str
    answer: str
    created_by: int | None
    status: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )