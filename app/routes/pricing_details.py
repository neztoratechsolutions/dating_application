from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import SessionLocal
from models.pricing_details import PricingDetail
from models.users import User
from schemas.pricing_details import (PricingDetailCreate,PricingDetailUpdate,PricingDetailResponse)

router = APIRouter(prefix="/pricing-details",tags=["Pricing Details"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "/",
    response_model=PricingDetailResponse,
    status_code=status.HTTP_201_CREATED
)
def create_pricing_detail(
    data: PricingDetailCreate,
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

    existing = db.query(PricingDetail).filter(
        PricingDetail.user_id == data.user_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pricing detail already exists for this user"
        )

    pricing = PricingDetail(**data.model_dump())

    db.add(pricing)
    db.commit()
    db.refresh(pricing)

    return pricing


@router.get(
    "/",
    response_model=list[PricingDetailResponse],
    status_code=status.HTTP_200_OK
)
def get_pricing_details(
    db: Session = Depends(get_db)
):
    pricing_details = db.query(
        PricingDetail
    ).all()

    if not pricing_details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No data found"
        )

    return pricing_details


@router.get(
    "/{pricing_id}",
    response_model=PricingDetailResponse,
    status_code=status.HTTP_200_OK
)
def get_pricing_detail(
    pricing_id: int,
    db: Session = Depends(get_db)
):
    pricing = db.query(PricingDetail).filter(
        PricingDetail.id == pricing_id
    ).first()

    if not pricing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pricing detail not found"
        )

    return pricing


@router.put(
    "/{pricing_id}",
    response_model=PricingDetailResponse,
    status_code=status.HTTP_200_OK
)
def update_pricing_detail(
    pricing_id: int,
    data: PricingDetailUpdate,
    db: Session = Depends(get_db)
):
    pricing = db.query(PricingDetail).filter(
        PricingDetail.id == pricing_id
    ).first()

    if not pricing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pricing detail not found"
        )

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(pricing, key, value)

    db.commit()
    db.refresh(pricing)

    return pricing


@router.delete(
    "/{pricing_id}",
    status_code=status.HTTP_200_OK
)
def delete_pricing_detail(
    pricing_id: int,
    db: Session = Depends(get_db)
):
    pricing = db.query(PricingDetail).filter(
        PricingDetail.id == pricing_id
    ).first()

    if not pricing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pricing detail not found"
        )

    db.delete(pricing)
    db.commit()

    return {
        "message": "Pricing detail deleted successfully"
    }