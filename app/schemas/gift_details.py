from decimal import Decimal
from pydantic import BaseModel, ConfigDict
from datetime import datetime


class GiftDetailCreate(BaseModel):
    user_id: int
    sender_id: int
    gift_id: int
    earnings: Decimal = 0.00


class GiftDetailResponse(BaseModel):
    id: int
    user_id: int
    sender_id: int
    gift_id: int
    earnings: Decimal
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )