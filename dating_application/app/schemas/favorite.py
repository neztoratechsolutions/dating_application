from pydantic import BaseModel


class FavoriteCreate(BaseModel):
    customer_id: int
    creator_id: int


class FavoriteResponse(BaseModel):
    id: int
    customer_id: int
    creator_id: int

class UserBasicDetails(BaseModel):
    id: int
    display_name: str
    email: str
    profile_photo: str | None = None
    role: str


class FavoriteDetailResponse(BaseModel):
    favorite_id: int

    customer_id: int
    customer_name: str

    creator_id: int
    creator_name: str

    followers_count: int
    following_count: int

    followers: list[UserBasicDetails]
    following: list[UserBasicDetails]


    class Config:
        from_attributes = True