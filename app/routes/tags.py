from fastapi import ( APIRouter, Depends, HTTPException, status)
from sqlalchemy.orm import Session

from database import get_db
from models.tags import Tag
from models.users import User
from schemas.tags import (TagCreate,TagUpdate,TagResponse)

router = APIRouter(prefix="/tags",tags=["Tags"])


@router.post(
    "/",
    response_model=TagResponse,
    status_code=status.HTTP_201_CREATED
)
def create_tag(
    data: TagCreate,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.id == data.user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    tag = Tag(
        user_id=data.user_id,
        tag_name=data.tag_name
    )

    db.add(tag)
    db.commit()
    db.refresh(tag)

    return tag



@router.get(
    "/",
    response_model=list[TagResponse],
    status_code=status.HTTP_200_OK
)
def get_tags(
    db: Session = Depends(get_db)
):
    tags = db.query(Tag).all()

    if not tags:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No data found"
        )

    return tags



@router.get(
    "/{tag_id}",
    response_model=TagResponse,
    status_code=status.HTTP_200_OK
)
def get_tag(
    tag_id: int,
    db: Session = Depends(get_db)
):
    tag = db.query(Tag).filter(
        Tag.id == tag_id
    ).first()

    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )

    return tag



@router.put(
    "/{tag_id}",
    response_model=TagResponse,
    status_code=status.HTTP_200_OK
)
def update_tag(
    tag_id: int,
    data: TagUpdate,
    db: Session = Depends(get_db)
):
    tag = db.query(Tag).filter(
        Tag.id == tag_id
    ).first()

    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )

    update_data = data.model_dump(
        exclude_unset=True
    )

    for key, value in update_data.items():
        setattr(tag, key, value)

    db.commit()
    db.refresh(tag)

    return tag



@router.delete(
    "/{tag_id}",
    status_code=status.HTTP_200_OK
)
def delete_tag(
    tag_id: int,
    db: Session = Depends(get_db)
):
    tag = db.query(Tag).filter(
        Tag.id == tag_id
    ).first()

    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )

    db.delete(tag)
    db.commit()

    return {
        "status": "success",
        "message": "Tag deleted successfully"
    }