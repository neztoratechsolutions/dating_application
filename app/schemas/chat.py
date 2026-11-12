from pydantic import BaseModel
from typing import Optional


class ChatCreate(BaseModel):
    user_one_id: int
    user_two_id: int


class ChatUpdate(BaseModel):
    user_one_id: Optional[int] = None
    user_two_id: Optional[int] = None
    status: Optional[bool] = None