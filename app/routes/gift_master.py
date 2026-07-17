from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import SessionLocal
from models.gift_master import GiftMaster
from schemas.gift_master import (GiftCreate,GiftUpdate,GiftResponse)

router = APIRouter(prefix="/gifts",tags=["Gift Master"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=GiftResponse)
def create_gift(data: GiftCreate, db: Session = Depends(get_db)):
    gift = GiftMaster(**data.model_dump())

    db.add(gift)
    db.commit()
    db.refresh(gift)

    return gift


@router.get("/", response_model=list[GiftResponse])
def get_gifts(db: Session = Depends(get_db)):
    return db.query(GiftMaster).all()


@router.get("/{gift_id}", response_model=GiftResponse)
def get_gift(gift_id: int, db: Session = Depends(get_db)):
    gift = db.query(GiftMaster).filter(
        GiftMaster.id == gift_id
    ).first()

    if not gift:
        raise HTTPException(404, "Gift not found")

    return gift


@router.put("/{gift_id}", response_model=GiftResponse)
def update_gift(
    gift_id: int,
    data: GiftUpdate,
    db: Session = Depends(get_db)
):
    gift = db.query(GiftMaster).filter(
        GiftMaster.id == gift_id
    ).first()

    if not gift:
        raise HTTPException(404, "Gift not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(gift, key, value)

    db.commit()
    db.refresh(gift)

    return gift


@router.delete("/{gift_id}")
def delete_gift(
    gift_id: int,
    db: Session = Depends(get_db)
):
    gift = db.query(GiftMaster).filter(
        GiftMaster.id == gift_id
    ).first()

    if not gift:
        raise HTTPException(404, "Gift not found")

    db.delete(gift)
    db.commit()

    return {"message": "Gift deleted successfully"}