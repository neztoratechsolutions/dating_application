from pydantic import BaseModel
from models.user_status import UserStatus

class UserStatusCreate(BaseModel):
    user_id: int
    is_online: bool = False