from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ==========================================================
# INITIATE VOICE CALL
# ==========================================================

class VoiceCallInitiate(BaseModel):
    caller_id: int
    receiver_id: int


# ==========================================================
# CREATE VOICE CALL
# ==========================================================

class VoiceCallCreate(BaseModel):
    customer_id: int
    creator_id: int
    caller_id: int
    receiver_id: int

    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    duration: Decimal = Decimal("0.00")
    coins: int = 0
    revenue: Decimal = Decimal("0.00")

    status: str = "ringing"


# ==========================================================
# UPDATE VOICE CALL
# ==========================================================

class VoiceCallUpdate(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[Decimal] = None
    coins: Optional[int] = None
    revenue: Optional[Decimal] = None
    status: Optional[str] = None


# ==========================================================
# RESPONSE
# ==========================================================

class VoiceCallResponse(BaseModel):
    id: int
    call_id: str

    customer_id: int
    creator_id: int

    caller_id: Optional[int] = None
    receiver_id: Optional[int] = None

    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    duration: Decimal
    coins: int
    revenue: Decimal

    status: str
    is_free_call: bool

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)