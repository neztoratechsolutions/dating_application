from pydantic import BaseModel
from decimal import Decimal
from models.pricing_details import PricingDetail


class PricingDetailCreate(BaseModel):
    user_id: int
    chat_amount: Decimal
    voice_call_amount: Decimal
    video_call_amount: Decimal


class PricingDetailUpdate(BaseModel):
    chat_amount: Decimal | None = None
    voice_call_amount: Decimal | None = None
    video_call_amount: Decimal | None = None


class PricingDetailResponse(BaseModel):
    id: int
    user_id: int
    chat_amount: Decimal
    voice_call_amount: Decimal
    video_call_amount: Decimal

    class Config:
        from_attributes = True