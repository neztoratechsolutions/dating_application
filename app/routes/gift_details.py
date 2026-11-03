from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models.users import User
from models.gift_master import GiftMaster
from models.gift_details import GiftDetail
from schemas.gift_details import (GiftDetailCreate,GiftDetailResponse,UserGiftEarningsResponse)
from models.wallet_transaction import WalletTransaction
from models.wallet import Wallet
import uuid
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from collections import defaultdict
from decimal import Decimal
router = APIRouter(prefix="/gift-details",tags=["Gift Details"])
def _generate_transaction_id() -> str:
    """Unique, 30-char-safe transaction id (TXN + uuid hex)."""
    return f"TXN{uuid.uuid4().hex[:24]}"
@router.post(
    "/",
    response_model=GiftDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_gift_detail(
    data: GiftDetailCreate,
    db: Session = Depends(get_db),
):
    # ================================================
    # 1. VALIDATE GIFT
    # ================================================
    # The gift's server-side coin price is the source of
    # truth for the deduction (never trust the client's
    # `earnings` value alone). We fall back to data.earnings
    # only if the GiftMaster row has no coins column/value.
    gift = db.query(GiftMaster).filter(
        GiftMaster.id == data.gift_id
    ).first()

    if not gift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gift not found",
        )

    server_coins = getattr(gift, "coins", None)
    coin_amount = (
        int(server_coins)
        if server_coins is not None
        else int(data.earnings)
    )

    if coin_amount < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid gift coin amount.",
        )

    # ================================================
    # 2. VALIDATE USER (creator receiving earnings)
    # ================================================
    user = db.query(User).filter(
        User.id == data.user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # ================================================
    # 3. VALIDATE SENDER (customer paying)
    # ================================================
    sender = db.query(User).filter(
        User.id == data.sender_id
    ).first()

    if not sender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sender not found",
        )

    # A user must not send a gift to themselves.
    if data.sender_id == data.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot send a gift to yourself.",
        )

    # ================================================
    # 4. LOAD SENDER'S WALLET
    # ================================================
    sender_wallet = db.query(Wallet).filter(
        Wallet.user_id == data.sender_id
    ).first()

    if not sender_wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sender wallet not found",
        )

    if sender_wallet.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sender wallet is not active",
        )

    current_coins = int(sender_wallet.coins or 0)

    # ================================================
    # 5. INSUFFICIENT BALANCE CHECK
    # ================================================
    # Free gift (0 coins) skips the deduction but still
    # records the gift detail below.
    if coin_amount > 0 and current_coins < coin_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Insufficient coins. "
                f"You have {current_coins}, "
                f"need {coin_amount}."
            ),
        )

    # ================================================
    # 6. ATOMIC: DEDUCT + RECORD TXN + GIFT DETAIL
    # ================================================
    try:
        if coin_amount > 0:
            # Deduct coins from the sender's wallet.
            sender_wallet.coins = current_coins - coin_amount
            sender_wallet.last_transaction = datetime.utcnow()

            # Record the debit as a wallet transaction.
            txn = WalletTransaction(
                transaction_id=_generate_transaction_id(),
                user_id=data.sender_id,
                wallet_id=sender_wallet.id,
                type="debit",
                amount=0.00,
                coins=coin_amount,
                method="gift",
                status="completed",
            )
            db.add(txn)

        # Store the earnings record (gift detail).
        gift_detail = GiftDetail(
            user_id=data.user_id,
            sender_id=data.sender_id,
            gift_id=data.gift_id,
            earnings=coin_amount,
        )
        db.add(gift_detail)

        db.commit()
        db.refresh(gift_detail)

        return gift_detail

    except HTTPException:
        # Re-raise FastAPI exceptions as-is.
        db.rollback()
        raise

    except Exception as exc:
        # Anything else: roll back the whole transaction
        # so no partial deduction / record is persisted.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process gift: {exc}",
        )

# @router.post(
#     "/",
#     response_model=GiftDetailResponse,
#     status_code=status.HTTP_201_CREATED
# )
# def create_gift_detail(
#     data: GiftDetailCreate,
#     db: Session = Depends(get_db)
# ):
#     user = db.query(User).filter(
#         User.id == data.user_id
#     ).first()

#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="User not found"
#         )

#     sender = db.query(User).filter(
#         User.id == data.sender_id
#     ).first()

#     if not sender:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Sender not found"
#         )

#     gift = db.query(GiftMaster).filter(
#         GiftMaster.id == data.gift_id
#     ).first()

#     if not gift:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Gift not found"
#         )

#     gift_detail = GiftDetail(
#         user_id=data.user_id,
#         sender_id=data.sender_id,
#         gift_id=data.gift_id,
#         earnings=data.earnings
#     )

#     db.add(gift_detail)
#     db.commit()
#     db.refresh(gift_detail)

#     return gift_detail



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

#------------Earnings ---------#
@router.get(
    "/user/{user_id}/earnings",
    response_model=UserGiftEarningsResponse,
    status_code=status.HTTP_200_OK,
)
def get_user_gift_earnings(
    user_id: int,
    db: Session = Depends(get_db),
):

    # =========================================
    # 1. VALIDATE USER
    # =========================================

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # =========================================
    # 2. GET TOTAL EARNINGS
    # =========================================

    total_earnings = db.query(
        func.coalesce(
            func.sum(GiftDetail.earnings),
            0
        )
    ).filter(
        GiftDetail.user_id == user_id
    ).scalar()

    # =========================================
    # 3. GET TOTAL GIFTS RECEIVED
    # =========================================

    total_gifts_received = db.query(
        func.count(GiftDetail.id)
    ).filter(
        GiftDetail.user_id == user_id
    ).scalar()

    # =========================================
    # 4. GET GIFT DETAILS WITH SENDER + GIFT
    # =========================================

    gift_details = (
        db.query(
            GiftDetail,
            User,
            GiftMaster
        )
        .join(
            User,
            GiftDetail.sender_id == User.id
        )
        .join(
            GiftMaster,
            GiftDetail.gift_id == GiftMaster.id
        )
        .filter(
            GiftDetail.user_id == user_id
        )
        .order_by(
            GiftDetail.created_at.desc()
        )
        .all()
    )

    # =========================================
    # 5. PREPARE RESPONSE
    # =========================================

    result = []

    for gift_detail, sender, gift in gift_details:

        result.append({

            "id": gift_detail.id,

            "sender": {
                "id": sender.id,
                "username": sender.display_name,
                "profile_image": sender.profile_photo,
            },

            "gift": {
                "id": gift.id,
                "name": gift.catalog_name,
                "image": gift.icon,
                "coins": gift.coins,
            },

            "earnings": gift_detail.earnings,

            "created_at": gift_detail.created_at,

        })

    # =========================================
    # 6. RETURN RESPONSE
    # =========================================

    return {

        "user_id": user_id,

        "total_earnings": total_earnings,

        "total_gifts_received": total_gifts_received,

        "gift_details": result,

    }


@router.get(
    "/user/{user_id}/received-summary",
    status_code=status.HTTP_200_OK,
)
def get_gifts_received_summary(
    user_id: int,
    db: Session = Depends(get_db),
):

    SHARE_PERCENTAGE = Decimal("20")

    # =========================================
    # 1. VALIDATE CREATOR
    # =========================================

    creator = db.query(User).filter(
        User.id == user_id
    ).first()

    if not creator:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # =========================================
    # 2. GET TOTAL GIFT COINS
    # =========================================

    total_gift_coins = db.query(
        func.coalesce(
            func.sum(GiftDetail.earnings),
            0,
        )
    ).filter(
        GiftDetail.user_id == user_id
    ).scalar()

    total_gift_coins = Decimal(
        str(total_gift_coins)
    )

    # =========================================
    # 3. GET TOTAL GIFTS
    # =========================================

    total_gifts = db.query(
        func.count(GiftDetail.id)
    ).filter(
        GiftDetail.user_id == user_id
    ).scalar()

    # =========================================
    # 4. CALCULATE CREATOR EARNINGS
    # =========================================

    total_earnings = (
        total_gift_coins
        * SHARE_PERCENTAGE
        / Decimal("100")
    )

    # =========================================
    # 5. FETCH GIFT DETAILS + SENDER + GIFT
    # =========================================

    records = (
        db.query(
            GiftDetail,
            User,
            GiftMaster,
        )
        .join(
            User,
            GiftDetail.sender_id == User.id,
        )
        .join(
            GiftMaster,
            GiftDetail.gift_id == GiftMaster.id,
        )
        .filter(
            GiftDetail.user_id == user_id,
        )
        .order_by(
            GiftDetail.created_at.desc()
        )
        .all()
    )

    # =========================================
    # 6. GROUP GIFTS
    # =========================================

    gift_groups = defaultdict(
        lambda: {
            "gift_id": None,
            "gift_name": None,
            "gift_icon": None,
            "quantity": 0,
            "total_coins": Decimal("0"),
        }
    )

    # =========================================
    # 7. GROUP SUPPORTERS
    # =========================================

    supporters = defaultdict(
        lambda: {
            "sender_id": None,
            "name": None,
            "profile_image": None,
            "gift_count": 0,
            "total_coins": Decimal("0"),
            "gift_types": defaultdict(int),
        }
    )

    # =========================================
    # 8. PROCESS GIFT RECORDS
    # =========================================

    for gift_detail, sender, gift in records:

        # -------------------------------------
        # GIFT COINS
        # -------------------------------------

        coins = Decimal(
            str(gift_detail.earnings or 0)
        )

        # -------------------------------------
        # GIFT BREAKDOWN
        # -------------------------------------

        gift_group = gift_groups[gift.id]

        gift_group["gift_id"] = gift.id

        gift_group["gift_name"] = (
            gift.catalog_name
        )

        gift_group["gift_icon"] = (
            gift.icon
        )

        gift_group["quantity"] += 1

        gift_group["total_coins"] += coins

        # -------------------------------------
        # SUPPORTER INFORMATION
        # -------------------------------------

        supporter = supporters[sender.id]

        supporter["sender_id"] = sender.id

        supporter["name"] = (
            sender.display_name
        )

        supporter["profile_image"] = (
            sender.profile_photo
        )

        supporter["gift_count"] += 1

        supporter["total_coins"] += coins

        supporter["gift_types"][gift.id] += 1

    # =========================================
    # 9. PREPARE GIFT BREAKDOWN
    # =========================================

    gift_breakdown = list(
        gift_groups.values()
    )

    gift_breakdown.sort(
        key=lambda item: item["quantity"],
        reverse=True,
    )

    # =========================================
    # 10. PREPARE SUPPORTER LIST
    # =========================================

    supporter_list = []

    for supporter in supporters.values():

        gift_types = supporter["gift_types"]

        most_sent_gift_id = None

        most_sent_gift_count = 0

        # -------------------------------------
        # FIND MOST SENT GIFT
        # -------------------------------------

        if gift_types:

            most_sent_gift_id = max(
                gift_types,
                key=gift_types.get,
            )

            most_sent_gift_count = (
                gift_types[most_sent_gift_id]
            )

        # -------------------------------------
        # GET MOST SENT GIFT DETAILS
        # -------------------------------------

        most_sent_gift = None

        if most_sent_gift_id is not None:

            most_sent_gift = next(
                (
                    item
                    for item in gift_breakdown
                    if item["gift_id"]
                    == most_sent_gift_id
                ),
                None,
            )

        # -------------------------------------
        # SUPPORTER RESPONSE
        # -------------------------------------

        supporter_list.append({

            "sender_id": (
                supporter["sender_id"]
            ),

            "name": (
                supporter["name"]
            ),

            "profile_image": (
                supporter["profile_image"]
            ),

            "gift_count": (
                supporter["gift_count"]
            ),

            "most_sent_gift": (
                most_sent_gift
            ),

            "most_sent_gift_count": (
                most_sent_gift_count
            ),

            "total_coins": (
                supporter["total_coins"]
            ),

        })

    # =========================================
    # 11. SORT SUPPORTERS BY TOTAL COINS
    # =========================================

    supporter_list.sort(
        key=lambda item: item["total_coins"],
        reverse=True,
    )

    # =========================================
    # 12. GET TOP 5 SUPPORTERS
    # =========================================

    top_supporters = []

    for rank, supporter in enumerate(
        supporter_list[:5],
        start=1,
    ):

        supporter["rank"] = rank

        top_supporters.append(
            supporter
        )

    # =========================================
    # 13. GET TOP SUPPORTER
    # =========================================

    top_supporter = None

    if top_supporters:

        first = top_supporters[0]

        top_supporter = {

            "sender_id": (
                first["sender_id"]
            ),

            "name": (
                first["name"]
            ),

            "profile_image": (
                first["profile_image"]
            ),

            "total_coins": (
                first["total_coins"]
            ),

        }

    # =========================================
    # 14. RETURN DASHBOARD RESPONSE
    # =========================================

    return {

        "user_id": user_id,

        "share_percentage": SHARE_PERCENTAGE,

        "total_gifts": total_gifts,

        "total_gift_coins": total_gift_coins,

        "total_earnings": total_earnings,

        "top_supporter": top_supporter,

        "gift_breakdown": gift_breakdown,

        "top_supporters": top_supporters,

    }
