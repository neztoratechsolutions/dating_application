from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from decimal import Decimal

from database import SessionLocal

from models.gift_details import GiftDetail
from models.gift_master import GiftMaster
from models.users import User


router = APIRouter(
    prefix="/gift",
    tags=["Gift History"]
)


# =====================================================
# DATABASE
# =====================================================

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# =====================================================
# GET CURRENT MONTH GIFTS BY SENDER ID
# =====================================================

@router.get("/sender/{sender_id}")
def get_sender_gifts(
    sender_id: int,
    db: Session = Depends(get_db)
):

    try:

        # ---------------------------------------------
        # CURRENT MONTH
        # ---------------------------------------------

        now = datetime.now()

        month_start = datetime(
            year=now.year,
            month=now.month,
            day=1
        )

        if now.month == 12:

            next_month_start = datetime(
                year=now.year + 1,
                month=1,
                day=1
            )

        else:

            next_month_start = datetime(
                year=now.year,
                month=now.month + 1,
                day=1
            )

        # ---------------------------------------------
        # GET CURRENT MONTH GIFTS
        # ---------------------------------------------

        gifts = (
            db.query(
                GiftDetail,
                GiftMaster,
                User
            )
            .join(
                GiftMaster,
                GiftDetail.gift_id == GiftMaster.id
            )
            .join(
                User,
                GiftDetail.user_id == User.id
            )
            .filter(
                GiftDetail.sender_id == sender_id,
                GiftDetail.created_at >= month_start,
                GiftDetail.created_at < next_month_start
            )
            .order_by(
                GiftDetail.created_at.desc()
            )
            .all()
        )

        # ---------------------------------------------
        # NO GIFTS
        # ---------------------------------------------

        if not gifts:

            return {
                "status_code": 200,
                "message": "No gifts found for this sender in the current month",
                "data": {
                    "sender_id": sender_id,
                    "month": now.strftime("%B"),
                    "year": now.year,
                    "total_gifts": 0,
                    "total_coins_spent": 0,
                    "total_earnings": 0,
                    "gifts": []
                }
            }

        # ---------------------------------------------
        # RESPONSE
        # ---------------------------------------------

        gift_list = []

        total_coins_spent = Decimal("0.00")

        total_earnings = Decimal("0.00")

        for gift_detail, gift_master, creator in gifts:

            # -----------------------------------------
            # CREATOR EARNINGS
            # -----------------------------------------

            earnings = Decimal(
                str(gift_detail.earnings or 0)
            )

            # -----------------------------------------
            # COINS SPENT
            # -----------------------------------------

            coins_spent = Decimal(
                str(gift_master.coins or 0)
            )

            total_coins_spent += coins_spent

            total_earnings += earnings

            # -----------------------------------------
            # CREATOR NAME
            # -----------------------------------------

            creator_name = (
                getattr(creator, "name", None)
                or getattr(creator, "display_name", None)
                or getattr(creator, "username", None)
                or "Creator"
            )

            # -----------------------------------------
            # GIFT RESPONSE
            # -----------------------------------------

            gift_list.append({

                "gift_detail_id": gift_detail.id,

                "gift_id": gift_detail.gift_id,

                "catalog_name": gift_master.catalog_name,

                "icon": gift_master.icon,

                "sender_id": gift_detail.sender_id,

                "creator_name": creator_name,

                "coins_spent": float(coins_spent),

                "earnings": float(earnings),

                "created_at": (
                    gift_detail.created_at.isoformat()
                    if gift_detail.created_at
                    else None
                )

            })

        # ---------------------------------------------
        # FINAL RESPONSE
        # ---------------------------------------------

        return {
            "status_code": 200,
            "message": "Current month gift history retrieved successfully",
            "data": {
                "sender_id": sender_id,
                "month": now.strftime("%B"),
                "year": now.year,
                "total_gifts": len(gift_list),
                "total_coins_spent": float(total_coins_spent),
                "total_earnings": float(total_earnings),
                "gifts": gift_list
            }
        }

    except Exception as e:

        print(
            "Current month sender gift history error:",
            str(e)
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve current month gift history"
        )
