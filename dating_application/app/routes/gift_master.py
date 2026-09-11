from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.gift_master import GiftMaster
from app.schemas.gift_master import ( GiftCreate, GiftUpdate, GiftResponse)

router = APIRouter(prefix="/gifts",tags=["Gift Master"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "/",
    response_model=GiftResponse,
    status_code=status.HTTP_201_CREATED
)
def create_gift(
    data: GiftCreate,
    db: Session = Depends(get_db)
):
    gift = GiftMaster(**data.model_dump())

    db.add(gift)
    db.commit()
    db.refresh(gift)

    return gift


@router.get(
    "/",
    response_model=list[GiftResponse],
    status_code=status.HTTP_200_OK
)
def get_gifts(db: Session = Depends(get_db)):
    return db.query(GiftMaster).all()


@router.get(
    "/{gift_id}",
    response_model=GiftResponse,
    status_code=status.HTTP_200_OK
)
def get_gift(
    gift_id: int,
    db: Session = Depends(get_db)
):
    gift = db.query(GiftMaster).filter(
        GiftMaster.id == gift_id
    ).first()

    if not gift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gift not found"
        )

    return gift


@router.put(
    "/{gift_id}",
    response_model=GiftResponse,
    status_code=status.HTTP_200_OK
)
def update_gift(
    gift_id: int,
    data: GiftUpdate,
    db: Session = Depends(get_db)
):
    gift = db.query(GiftMaster).filter(
        GiftMaster.id == gift_id
    ).first()

    if not gift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gift not found"
        )

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(gift, key, value)

    db.commit()
    db.refresh(gift)

    return gift


@router.delete(
    "/{gift_id}",
    status_code=status.HTTP_200_OK
)
def delete_gift(
    gift_id: int,
    db: Session = Depends(get_db)
):
    gift = db.query(GiftMaster).filter(
        GiftMaster.id == gift_id
    ).first()

    if not gift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gift not found"
        )

    db.delete(gift)
    db.commit()

    return {
        "message": "Gift deleted successfully"
    }