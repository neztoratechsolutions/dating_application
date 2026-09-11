from pydantic import BaseModel
from app.models.user_status import UserStatus

class UserStatusCreate(BaseModel):
    user_id: int
    is_online: bool = False