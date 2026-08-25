from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ==========================================================
# CREATE VIDEO CALL
# ==========================================================

class VideoCallCreate(BaseModel):

    customer_id: int
    creator_id: int

    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    duration: Optional[int] = None

    coins: Optional[int] = 0
    revenue: Optional[float] = 0

    status: Optional[str] = "pending"


# ==========================================================
# UPDATE VIDEO CALL
# ==========================================================

class VideoCallUpdate(BaseModel):

    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    duration: Optional[int] = None

    coins: Optional[int] = None
    revenue: Optional[float] = None

    status: Optional[str] = None


# ==========================================================
# VIDEO CALL RESPONSE
# ==========================================================

class VideoCallResponse(BaseModel):

    id: int
    video_call_id: str

    customer_id: int
    creator_id: int

    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    duration: Optional[int] = None

    coins: int
    revenue: float

    status: str

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True