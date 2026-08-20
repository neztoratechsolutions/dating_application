from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class VoiceCallCreate(BaseModel):
    call_id: str
    customer_id: int
    creator_id: int

    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    duration: int = 0
    coins: int = 0
    revenue: Decimal = Decimal("0.00")

    status: str = "ongoing"


class VoiceCallUpdate(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    duration: Optional[int] = None
    coins: Optional[int] = None
    revenue: Optional[Decimal] = None

    status: Optional[str] = None


class VoiceCallResponse(BaseModel):
    id: int
    call_id: str

    customer_id: int
    creator_id: int

    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    duration: int
    coins: int
    revenue: Decimal
    status: str

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)