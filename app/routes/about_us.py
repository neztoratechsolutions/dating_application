from fastapi import (APIRouter,Depends,HTTPException,status)
from sqlalchemy.orm import Session

from database import get_db
from models.cms_models import AboutUs
from schemas.about_us import ( AboutUsCreate, AboutUsUpdate, AboutUsResponse)

router = APIRouter(  prefix="/about-us",  tags=["About Us"])

@router.post(
    "/",
    response_model=AboutUsResponse,
    status_code=status.HTTP_201_CREATED
)
def create_about_us(
    data: AboutUsCreate,
    db: Session = Depends(get_db)
):
    about = AboutUs(
        name=data.name,
        details=data.details,
        status=data.status
    )

    db.add(about)
    db.commit()
    db.refresh(about)

    return about



@router.get(
    "/",
    response_model=list[AboutUsResponse],
    status_code=status.HTTP_200_OK
)
def get_about_us(
    db: Session = Depends(get_db)
):
    about_list = db.query(
        AboutUs
    ).all()

    if not about_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No data found"
        )

    return about_list



@router.get(
    "/{about_id}",
    response_model=AboutUsResponse,
    status_code=status.HTTP_200_OK
)
def get_about_us_by_id(
    about_id: int,
    db: Session = Depends(get_db)
):
    about = db.query(
        AboutUs
    ).filter(
        AboutUs.id == about_id
    ).first()

    if not about:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="About us not found"
        )

    return about



@router.put(
    "/{about_id}",
    response_model=AboutUsResponse,
    status_code=status.HTTP_200_OK
)
def update_about_us(
    about_id: int,
    data: AboutUsUpdate,
    db: Session = Depends(get_db)
):
    about = db.query(
        AboutUs
    ).filter(
        AboutUs.id == about_id
    ).first()

    if not about:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="About us not found"
        )

    update_data = data.model_dump(
        exclude_unset=True
    )

    for key, value in update_data.items():
        setattr(
            about,
            key,
            value
        )

    db.commit()
    db.refresh(about)

    return about



@router.delete(
    "/{about_id}",
    status_code=status.HTTP_200_OK
)
def delete_about_us(
    about_id: int,
    db: Session = Depends(get_db)
):
    about = db.query(
        AboutUs
    ).filter(
        AboutUs.id == about_id
    ).first()

    if not about:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="About us not found"
        )

    db.delete(about)
    db.commit()

    return {
        "status_code": 200,
        "message": "About us deleted successfully"
    }