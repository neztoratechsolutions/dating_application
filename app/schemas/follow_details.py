from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class FollowDetailCreate(BaseModel):
    following_id: int
    follower_id: int
    follow_status: str = "following"


class FollowDetailUpdate(BaseModel):
    follow_status: str


class FollowDetailResponse(BaseModel):
    id: int

    following_id: int
    following_name: str

    follower_id: int
    follower_name: str

    follow_status: str
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class UserItem(BaseModel):
    id: int
    display_name: str

    class Config:
        from_attributes = True


class UserFollowResponse(BaseModel):
    following_id: int
    following_name: str

    followers_count: int
    following_count: int

    followers: List[UserItem]
    following: List[UserItem]

    class Config:
        from_attributes = True