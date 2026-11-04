from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


StatusType = Literal["Active", "Inactive"]


class UserSettingsCreate(BaseModel):
    customer_id: int
    push_notifications: StatusType = "Active"
    online_status: StatusType = "Active"
    show_in_search: StatusType = "Active"
    auto_recharge_coins: StatusType = "Inactive"


class UserSettingsUpdate(BaseModel):
    push_notifications: Optional[StatusType] = None
    online_status: Optional[StatusType] = None
    show_in_search: Optional[StatusType] = None
    auto_recharge_coins: Optional[StatusType] = None


class UserSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    push_notifications: str
    online_status: str
    show_in_search: str
    auto_recharge_coins: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None