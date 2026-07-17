from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.pricing_details import PricingDetail
from app.schemas.pricing_details import (PricingDetailCreate,PricingDetailUpdate,PricingDetailResponse)

router = APIRouter(prefix="/pricing-details",tags=["Pricing Details"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=PricingDetailResponse)
def create_pricing_detail(
    data: PricingDetailCreate,
    db: Session = Depends(get_db)
):
    existing = db.query(PricingDetail).filter(
        PricingDetail.user_id == data.user_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Pricing detail already exists for this user"
        )

    pricing = PricingDetail(**data.model_dump())

    db.add(pricing)
    db.commit()
    db.refresh(pricing)

    return pricing


@router.get("/", response_model=list[PricingDetailResponse])
def get_pricing_details(
    db: Session = Depends(get_db)
):
    return db.query(PricingDetail).all()


@router.get("/{pricing_id}", response_model=PricingDetailResponse)
def get_pricing_detail(
    pricing_id: int,
    db: Session = Depends(get_db)
):
    pricing = db.query(PricingDetail).filter(
        PricingDetail.id == pricing_id
    ).first()

    if not pricing:
        raise HTTPException(
            status_code=404,
            detail="Pricing detail not found"
        )

    return pricing


@router.put("/{pricing_id}", response_model=PricingDetailResponse)
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
            status_code=404,
            detail="Pricing detail not found"
        )

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(pricing, key, value)

    db.commit()
    db.refresh(pricing)

    return pricing


@router.delete("/{pricing_id}")
def delete_pricing_detail(
    pricing_id: int,
    db: Session = Depends(get_db)
):
    pricing = db.query(PricingDetail).filter(
        PricingDetail.id == pricing_id
    ).first()

    if not pricing:
        raise HTTPException(
            status_code=404,
            detail="Pricing detail not found"
        )

    db.delete(pricing)
    db.commit()

    return {
        "message": "Pricing detail deleted successfully"
    }