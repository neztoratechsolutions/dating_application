from decimal import Decimal
from pydantic import BaseModel, ConfigDict
from datetime import datetime

from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal


class GiftSenderResponse(BaseModel):
    id: int
    username: str
    profile_image: str | None = None

    class Config:
        from_attributes = True


class GiftMasterDetailsResponse(BaseModel):
    id: int
    name: str
    image: str | None = None
    coins: int

    class Config:
        from_attributes = True


class GiftReceivedDetailsResponse(BaseModel):
    id: int
    sender: GiftSenderResponse
    gift: GiftMasterDetailsResponse
    earnings: Decimal
    created_at: datetime


class UserGiftEarningsResponse(BaseModel):
    user_id: int
    total_earnings: Decimal
    total_gifts_received: int
    gift_details: list[GiftReceivedDetailsResponse]

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