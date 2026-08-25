from pydantic import BaseModel
from typing import Optional

class SendGiftRequest(BaseModel):
    sender_id:int
    receiver_id:int
    gift_name:str
    gift_image: Optional[str] = None
    message: Optional[str] = None

class GiftResponse(BaseModel):
    id:int 
    sender_id: int
    receiver_id:int
    gift_name: str
    gift_image: Optional[str] = None
    message: Optional[str] = None
    status: str

    class Config:
        from_attributes = True