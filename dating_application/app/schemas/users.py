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
    gender: Literal["Male", "Female", "Other"]


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    display_name: Optional[str] = None
    bio: Optional[str] = None
    description: Optional[str] = None
    state_id: Optional[int] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    gender: Optional[Literal["Male", "Female", "Other"]] = None


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
    gender: str
    role: str

    model_config = ConfigDict(from_attributes=True)