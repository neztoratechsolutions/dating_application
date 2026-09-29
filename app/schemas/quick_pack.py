from datetime import datetime
from pydantic import BaseModel, ConfigDict


class QuickPackCreate(BaseModel):
    coins: int
    bonus: int = 0
    mrp: int
    is_active: bool = True
    display_order: int = 0


class QuickPackUpdate(BaseModel):
    coins: int | None = None
    bonus: int | None = None
    mrp: int | None = None
    is_active: bool | None = None
    display_order: int | None = None


class QuickPackResponse(BaseModel):
    id: int
    coins: int
    bonus: int
    mrp: int
    is_active: bool
    display_order: int
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)