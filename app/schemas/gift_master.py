from pydantic import BaseModel
from decimal import Decimal
from models.gift_master import GiftMaster


class GiftCreate(BaseModel):
    catalog_name: str
    icon: str | None = None
    coins: int

class GiftUpdate(BaseModel):
    catalog_name: str | None = None
    icon: str | None = None
    coins: int | None = None
    status: bool | None = None


class GiftResponse(BaseModel):
    id: int
    catalog_name: str
    icon: str | None
    coins: int

    class Config:
        from_attributes = True