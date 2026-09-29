from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CustomerResponse(BaseModel):

    id: int
    display_name: str

    email: str
    phone: Optional[str] = None

    profile_photo: Optional[str] = None

    gender: str
    state: Optional[str] = None

    status: str

    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True



class CreatorResponse(BaseModel):

    id: int
    display_name: str

    email: str
    phone: Optional[str] = None

    profile_photo: Optional[str] = None

    gender: str
    state: Optional[str] = None

    status: str

    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True