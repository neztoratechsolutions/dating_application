from typing import Optional, Literal
from pydantic import BaseModel, EmailStr, ConfigDict


class UserCreate(BaseModel):
    email: EmailStr
    phone: Optional[str] = None
    password: str
    display_name: str
    bio: Optional[str] = None
    description: Optional[str] = None
    state_id: int
    profile_photo: Optional[str] = None
    gender: Literal["Male", "Female", "Other"]


class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    bio: Optional[str] = None
    profile_photo: Optional[str] = None


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
    gender: str | None
    role: str

    model_config = ConfigDict(from_attributes=True)


class UserStatusUpdate(BaseModel):
    status: Literal["Active", "Inactive", "Ban"]