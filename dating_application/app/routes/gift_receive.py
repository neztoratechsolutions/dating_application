from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import SessionLocal
from models.users import User
from models.gift_receive import Gift
from schemas.gift_receive import SendGiftRequest

router = APIRouter(
    prefix="/gifts",
    tags=["Gifts"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ----------------------------------------- Send Gift ----------------------------------------

@router.post(
    "/send",
    status_code=status.HTTP_201_CREATED
)
def send_gift(
    data:SendGiftRequest,
    db : Session = Depends(get_db)
):

    # Check sender
    sender = db.query(User).filter(
        User.id == data.sender_id
    ).first()

    if not sender:
        raise HTTPException(
            status_code=404,
            detail="Sender user not found"
        )

    # Check receiver
    receiver = db.query(User).filter(
        User.id == data.receiver_id
    ).first()

    if not receiver:
        raise HTTPException(
            status_code=404,
            detail="Reciver user not found"
        )

    # Prevent sending gift to yourself

    if data.sender_id == data.receiver_id:
        raise HTTPException(
            status_code=400,
            detail="You cannot send a gift to yourself"
        )

    #create gift
    
    gift = Gift(
        sender_id=data.sender_id,
        receiver_id=data.receiver_id,
        gift_name=data.gift_name,
        gift_image=data.gift_image,
        message=data.message,
        status="received"
    )

    db.add(gift)
    db.commit()
    db.refresh(gift)

    return{
        "status_code": 201,
        "message":"Gift send successfully",
        "gift":{
            "id":gift.id,
            "sender_id":gift.sender_id,
            "receiver_id":gift.receiver_id,
            "gift_name":gift.gift_name,
            "gift_image":gift.gift_image,
            "message":gift.message,
            "status":gift.status
        }
    }

# ----------------------------------------- Get Received Gifts ----------------------------------------

@router.get(
    "/received/{user_id}"
)
def get_received_gifts(
    user_id: int,
    db: Session = Depends(get_db)
):
    user=db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    gifts=db.query(Gift).filter(
        Gift.receiver_id == user_id
    ).order_by(
        Gift.created_at.desc()
    ).all()

    return{
    "status_code":200,
    "message":"Received gifts fetched successfully",
    "total_gifts":len(gifts),
    "gifts":gifts
    }

# ----------------------------------------- Get Send Gifts ----------------------------------------

@router.get(
    "/sent/{user_id}"
)
def get_sent_gifts(
    user_id:int,
    db: Session = Depends(get_db)
):
    user=db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not Found"
        )

    gifts = db.query(Gift).filter(
        Gift.sender_id == user_id
    ).order_by(
        Gift.created_at.desc()
    ).all()

    return{
        "status_code":200,
        "message":"Sent gifts fetched successfully",
        "total_gifts":len(gifts),
        "gifts":gifts
    }