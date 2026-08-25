from pydantic import BaseModel
from typing import Optional


class ChatMessageCreate(BaseModel):
    chat_id: int
    sender_id: int
    receiver_id: int
    message: Optional[str] = None
    message_type: str = "text"


class ChatMessageUpdate(BaseModel):
    message: Optional[str] = None
    message_type: Optional[str] = None
    is_read: Optional[bool] = None
    is_delivered: Optional[bool] = None