from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
import os

from app.database import SessionLocal
from app.models.gallery import Gallery
from app.models.users import User
from app.schemas.gallery import GalleryResponse

router = APIRouter(prefix="/gallery",tags=["Gallery"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED
)
async def create_gallery(
    user_id: int = Form(...),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    os.makedirs("uploads/gallery", exist_ok=True)

    file_path = f"uploads/gallery/{photo.filename}"

    with open(file_path, "wb") as buffer:
        buffer.write(await photo.read())

    gallery = Gallery(
        user_id=user_id,
        photo=file_path
    )

    db.add(gallery)
    db.commit()
    db.refresh(gallery)

    return {
        "status_code": 201,
        "message": "Photo uploaded successfully",
        "data": gallery
    }




@router.get(
    "/user/{user_id}",
    response_model=list[GalleryResponse],
    status_code=status.HTTP_200_OK
)
def get_user_gallery(
    user_id: int,
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    photos = db.query(Gallery).filter(
        Gallery.user_id == user_id
    ).all()

    return photos