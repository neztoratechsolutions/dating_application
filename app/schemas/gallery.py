from pydantic import BaseModel


class GalleryCreate(BaseModel):
    user_id: int
    photo: str


class GalleryResponse(BaseModel):
    id: int
    user_id: int
    photo: str

    class Config:
        from_attributes = True