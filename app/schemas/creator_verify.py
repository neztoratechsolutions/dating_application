from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CreatorVerificationResponse(BaseModel):
    creator_id: int

    voice_file: Optional[str] = None
    voice_duration: Optional[float] = None
    voice_status: str

    selfie_image: Optional[str] = None
    selfie_status: str

    completed_steps: int
    total_steps: int = 3

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None