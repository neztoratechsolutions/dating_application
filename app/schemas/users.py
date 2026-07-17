from pydantic import BaseModel, EmailStr
from typing import Optional
from models.users import User


class UserCreate(BaseModel):
    email: EmailStr
    phone: Optional[str] = None
    password: str
    display_name: str
    bio: Optional[str] = None
    description: Optional[str] = None
    state_id: int
    profile_photo: Optional[str] = None


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    display_name: Optional[str] = None
    bio: Optional[str] = None
    description: Optional[str] = None
    state_id: Optional[int] = None
    profile_photo: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None


class UserResponse(BaseModel):
    id: int
    email: str
    phone: str | None
    display_name: str
    bio: str | None
    description: str | None
    referral_code: str
    state_id: int | None
    profile_photo: str | None
    is_active: bool
    is_verified: bool

    class Config:
        from_attributes = True