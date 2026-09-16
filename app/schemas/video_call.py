from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ==========================================================
# INITIATE VIDEO CALL
# ==========================================================

class VideoCallInitiate(BaseModel):
    caller_id: int
    receiver_id: int


# ==========================================================
# CREATE VIDEO CALL
# ==========================================================

class VideoCallCreate(BaseModel):
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
# UPDATE VIDEO CALL
# ==========================================================

class VideoCallUpdate(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    duration: Optional[Decimal] = None
    coins: Optional[int] = None
    revenue: Optional[Decimal] = None

    status: Optional[str] = None


# ==========================================================
# RESPONSE
# ==========================================================

class VideoCallResponse(BaseModel):
    id: int
    video_call_id: str

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

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True
    )