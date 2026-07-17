from pydantic import BaseModel
from decimal import Decimal
from app.models.gift_master import GiftMaster


class GiftCreate(BaseModel):
    catalog_name: str
    icon: str | None = None
    coins: int
    creator_revenue: Decimal
    platform_revenue: Decimal


class GiftUpdate(BaseModel):
    catalog_name: str | None = None
    icon: str | None = None
    coins: int | None = None
    creator_revenue: Decimal | None = None
    platform_revenue: Decimal | None = None
    status: bool | None = None


class GiftResponse(BaseModel):
    id: int
    catalog_name: str
    icon: str | None
    coins: int
    creator_revenue: Decimal
    platform_revenue: Decimal
    status: bool

    class Config:
        from_attributes = True