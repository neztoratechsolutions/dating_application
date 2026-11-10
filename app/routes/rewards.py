from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import SessionLocal
from models.users import User
from models.referral import Referral
from models.gift_details import GiftDetail
from models.gift_master import GiftMaster
from schemas.rewards import (
    RewardsResponse
)


router = APIRouter(
    prefix="/rewards",
    tags=["Rewards"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get(
    "/{user_id}",
    response_model= RewardsResponse
)
def get_rewards(
    user_id : int ,
    db : Session = Depends(get_db)
):
    #check user
    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # Referral details
    referrals = db.query(Referral).filter(
        Referral.referrer_id == user_id
    ).all()

    friends_joined = len(referrals)

    coins_earned = sum(
        referral.reward_coins
        for referral in referrals
    )

    referral_link = f"velora.live/ref/{user.referral_code}"

    # Gifts sent by user
    gifts_sent = db.query(GiftDetail).filter(
        GiftDetail.sender_id == user_id
    ).count()

    #check diamond ring

    diamond_ring = db.query(GiftDetail).join(
        GiftMaster,
        GiftMaster.id == GiftDetail.gift_id
    ).filter(
        GiftDetail.sender_id == user_id,
        GiftMaster.catalog_name.ilike("Diamond Ring")
    )

    # Badge 1 - First Spark
    first_spark = gifts_sent >= 1


    #Badge 2 - Top Supportes
    top_supporter = gifts_sent >= 10

    # Badge 3 - Diamond Heart

    diamond_heart = diamond_ring is not None

    # Badge 4 - Social Star

    social_star = friends_joined >= 5

    # Prepare badges

    badges = [
        {
            "id": 1,
            "name": "First Spark",
            "description": "Sent your 1st gift",
            "icon": "spark",
            "unlocked": first_spark
        },
        {
            "id": 2,
            "name": "Top Supporter",
            "description": "Sent 10 gifts",
            "icon": "trophy",
            "unlocked": top_supporter
        },
        {
            "id": 3,
            "name": "Diamond Heart",
            "description": "Sent a Diamond Ring",
            "icon": "diamond",
            "unlocked": diamond_heart
        },
        {
            "id": 4,
            "name": "Social Star",
            "description": "Refer 5 friends",
            "icon": "users",
            "unlocked": social_star
        }
    ]

    # --------------------------------
    # Final response
    # --------------------------------

    return {
        "referral": {
            "referral_code": user.referral_code,
            "referral_link": referral_link,
            "friends_joined": friends_joined,
            "coins_earned": coins_earned
        },
        "badges": badges
    }
