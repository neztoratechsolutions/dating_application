
from decimal import Decimal, InvalidOperation

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

# Replace these imports with your actual model paths.
from models import Wallet, PricingDetails, ChatMessage


def process_paid_chat_message(
    db: Session,
    customer_id: int,
    creator_id: int,
    content: str,
) -> dict:
    """
    Deduct the creator's configured chat price and save the message
    in one transaction.

    Wallet, PricingDetails and ChatMessage are assumed model names.
    """

    content = content.strip()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty.",
        )

    try:
        with db.begin():
            # Lock the wallet row to prevent concurrent messages from
            # spending the same coins.
            wallet = db.execute(
                select(Wallet)
                .where(Wallet.user_id == customer_id)
                .with_for_update()
            ).scalar_one_or_none()

            if wallet is None:
                raise HTTPException(
                    status_code=404,
                    detail="Customer wallet not found.",
                )

            if getattr(wallet, "status", "active") != "active":
                raise HTTPException(
                    status_code=403,
                    detail="Customer wallet is not active.",
                )

            # Load the creator's configured chat price.
            pricing = db.execute(
                select(PricingDetails)
                .where(PricingDetails.user_id == creator_id)
            ).scalars().first()

            if pricing is None:
                raise HTTPException(
                    status_code=404,
                    detail="Creator pricing not found.",
                )

            try:
                price = Decimal(str(pricing.chat_amount))
                available_coins = Decimal(str(wallet.coins))
            except (InvalidOperation, TypeError, ValueError):
                raise HTTPException(
                    status_code=500,
                    detail="Invalid wallet balance or chat price.",
                )

            if not price.is_finite() or price < 0:
                raise HTTPException(
                    status_code=500,
                    detail="Invalid creator chat price.",
                )

            if not available_coins.is_finite() or available_coins < price:
                raise HTTPException(
                    status_code=402,
                    detail="Insufficient coins. Please recharge your wallet.",
                )

            # Deduct the amount using Decimal, not floating-point math.
            remaining_coins = available_coins - price

            # If Wallet.coins is an Integer column, ensure your configured
            # chat prices are whole coins before converting to int.
            wallet.coins = remaining_coins

            # IMPORTANT: Adapt these fields to your actual ChatMessage model.
            message = ChatMessage(
                sender_id=customer_id,
                receiver_id=creator_id,
                content=content,
            )

            db.add(message)
            db.flush()

            result = {
                "type": "message",
                "message": {
                    "id": message.id,
                    "sender_id": customer_id,
                    "receiver_id": creator_id,
                    "content": content,
                },
                "billing": {
                    "deducted_coins": str(price),
                    "remaining_coins": str(remaining_coins),
                },
            }

        # The transaction commits after both wallet update and message save.
        return result

    except Exception:
        # SQLAlchemy rolls back an uncommitted transaction when its
        # transaction context exits with an exception.
        raise
