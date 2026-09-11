from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.users import User
from app.models.gift_master import GiftMaster
from app.models.gift_details import GiftDetail
from app.schemas.gift_details import (GiftDetailCreate,GiftDetailResponse)


router = APIRouter(prefix="/gift-details",tags=["Gift Details"])


@router.post(
    "/",
    response_model=GiftDetailResponse,
    status_code=status.HTTP_201_CREATED
)
def create_gift_detail(
    data: GiftDetailCreate,
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

    sender = db.query(User).filter(
        User.id == data.sender_id
    ).first()

    if not sender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sender not found"
        )

    gift = db.query(GiftMaster).filter(
        GiftMaster.id == data.gift_id
    ).first()

    if not gift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gift not found"
        )

    gift_detail = GiftDetail(
        user_id=data.user_id,
        sender_id=data.sender_id,
        gift_id=data.gift_id,
        earnings=data.earnings
    )

    db.add(gift_detail)
    db.commit()
    db.refresh(gift_detail)

    return gift_detail



@router.get(
    "/",
    response_model=list[GiftDetailResponse],
    status_code=status.HTTP_200_OK
)
def get_gift_details(
    db: Session = Depends(get_db)
):
    gift_details = db.query(
        GiftDetail
    ).all()

    if not gift_details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No data found"
        )

    return gift_details




@router.get(
    "/{gift_detail_id}",
    response_model=GiftDetailResponse,
    status_code=status.HTTP_200_OK
)
def get_gift_detail(
    gift_detail_id: int,
    db: Session = Depends(get_db)
):
    gift_detail = db.query(
        GiftDetail
    ).filter(
        GiftDetail.id == gift_detail_id
    ).first()

    if not gift_detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gift detail not found"
        )

    return gift_detail




@router.delete(
    "/{gift_detail_id}",
    status_code=status.HTTP_200_OK
)
def delete_gift_detail(
    gift_detail_id: int,
    db: Session = Depends(get_db)
):
    gift_detail = db.query(
        GiftDetail
    ).filter(
        GiftDetail.id == gift_detail_id
    ).first()

    if not gift_detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gift detail not found"
        )

    db.delete(gift_detail)
    db.commit()

    return {
        "status": "success",
        "message": "Gift detail deleted successfully"
    }