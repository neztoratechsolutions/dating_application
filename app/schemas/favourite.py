from pydantic import BaseModel


class FavoriteCreate(BaseModel):
    customer_id: int
    creator_id: int


class FavoriteResponse(BaseModel):
    id: int
    customer_id: int
    creator_id: int

    class Config:
        from_attributes = True