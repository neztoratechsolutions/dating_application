
# import logging
# from datetime import datetime, timezone
# from typing import Optional

# from sqlalchemy.orm import Session

# from models.chat_history import Chat, ChatMessage

# logger = logging.getLogger(__name__)


# def save_chat_message(
#     db: Session,
#     chat_id: int,
#     sender_id: int,
#     content: Optional[str] = None,
#     message_type: str = "text",
#     attachment: Optional[str] = None,
#     message_metadata: Optional[dict] = None,
#     reply_message_id: Optional[int] = None,
# ) -> ChatMessage:
#     """
#     Save a chat message and update the conversation's last-message details.

#     The caller must pass a valid SQLAlchemy Session.
#     This function commits the transaction before returning the message.
#     """

#     content = (content or "").strip()
#     attachment = attachment or None

#     if not content and not attachment:
#         raise ValueError("Message content or attachment is required")

#     allowed_types = {
#         "text",
#         "image",
#         "video",
#         "audio",
#         "document",
#         "gift",
#         "voice_call",
#         "video_call",
#         "location",
#         "sticker",
#     }

#     if message_type not in allowed_types:
#         raise ValueError("Invalid message type")

#     try:
#         # Lock the conversation while validating and updating it.
#         chat = (
#             db.query(Chat)
#             .filter(
#                 Chat.id == chat_id,
#                 Chat.status.is_(True),
#             )
#             .with_for_update()
#             .first()
#         )

#         if chat is None:
#             raise ValueError("Chat not found or inactive")

#         if sender_id not in (chat.user_one_id, chat.user_two_id):
#             raise ValueError("Sender is not a participant in this chat")

#         receiver_id = (
#             chat.user_two_id
#             if sender_id == chat.user_one_id
#             else chat.user_one_id
#         )

#         if reply_message_id is not None:
#             reply_message = (
#                 db.query(ChatMessage)
#                 .filter(
#                     ChatMessage.id == reply_message_id,
#                     ChatMessage.chat_id == chat_id,
#                     ChatMessage.is_deleted.is_(False),
#                 )
#                 .first()
#             )

#             if reply_message is None:
#                 raise ValueError("Reply message not found in this chat")

#         now = datetime.now(timezone.utc)

#         message = ChatMessage(
#             chat_id=chat_id,
#             sender_id=sender_id,
#             receiver_id=receiver_id,
#             message=content or None,
#             attachment=attachment,
#             message_type=message_type,
#             message_metadata=message_metadata,
#             reply_message_id=reply_message_id,
#             is_read=False,
#             is_delivered=False,
#             is_deleted=False,
#             created_at=now,
#         )

#         db.add(message)
#         db.flush()

#         chat.last_message = content or f"[{message_type}]"
#         chat.last_message_at = now
#         chat.last_message_by = sender_id

#         # Maintain unread counts for the receiving participant.
#         if receiver_id == chat.user_one_id:
#             chat.unread_count_user1 = (
#                 (chat.unread_count_user1 or 0) + 1
#             )
#         else:
#             chat.unread_count_user2 = (
#                 (chat.unread_count_user2 or 0) + 1
#             )

#         db.commit()
#         db.refresh(message)

#         logger.info(
#             "Chat message saved successfully: "
#             "message_id=%s chat_id=%s sender_id=%s receiver_id=%s",
#             message.id,
#             chat_id,
#             sender_id,
#             receiver_id,
#         )

#         return message

#     except ValueError:
#         db.rollback()
#         raise

#     except Exception:
#         db.rollback()
#         logger.exception(
#             "Database error saving chat message: chat_id=%s sender_id=%s",
#             chat_id,
#             sender_id,
#         )
#         raise



import logging
import uuid

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Optional

from sqlalchemy.orm import Session

from models.chat_history import Chat, ChatMessage
from models.users import User
from models.wallet import Wallet
from models.wallet_transaction import WalletTransaction
from models.pricing_details import PricingDetail


logger = logging.getLogger(__name__)


def save_chat_message(
    db: Session,
    chat_id: int,
    sender_id: int,
    content: Optional[str] = None,
    message_type: str = "text",
    attachment: Optional[str] = None,
    message_metadata: Optional[dict] = None,
    reply_message_id: Optional[int] = None,
) -> ChatMessage:

    content = (content or "").strip()
    attachment = attachment or None

    if not content and not attachment:
        raise ValueError(
            "Message content or attachment is required"
        )

    allowed_types = {
        "text",
        "image",
        "video",
        "audio",
        "document",
        "gift",
        "voice_call",
        "video_call",
        "location",
        "sticker",
    }

    if message_type not in allowed_types:
        raise ValueError("Invalid message type")

    try:

        # =========================================
        # LOCK AND VALIDATE CHAT
        # =========================================

        chat = (
            db.query(Chat)
            .filter(
                Chat.id == chat_id,
                Chat.status.is_(True),
            )
            .with_for_update()
            .first()
        )

        if not chat:
            raise ValueError(
                "Chat not found or inactive"
            )

        if sender_id not in (
            chat.user_one_id,
            chat.user_two_id,
        ):
            raise ValueError(
                "Sender is not a participant in this chat"
            )

        # =========================================
        # IDENTIFY SENDER AND RECEIVER
        # =========================================

        receiver_id = (
            chat.user_two_id
            if sender_id == chat.user_one_id
            else chat.user_one_id
        )

        sender = (
            db.query(User)
            .filter(User.id == sender_id)
            .first()
        )

        if not sender:
            raise ValueError("Sender not found")

        receiver = (
            db.query(User)
            .filter(User.id == receiver_id)
            .first()
        )

        if not receiver:
            raise ValueError("Receiver not found")

        sender_role = (
            (sender.role or "")
            .strip()
            .lower()
        )

        receiver_role = (
            (receiver.role or "")
            .strip()
            .lower()
        )

        now = datetime.now(timezone.utc)

        logger.info(
            "Saving chat message: chat_id=%s "
            "sender_id=%s sender_role=%s "
            "receiver_id=%s receiver_role=%s",
            chat_id,
            sender_id,
            sender_role,
            receiver_id,
            receiver_role,
        )

        # =========================================
        # CUSTOMER -> CREATOR BILLING
        # =========================================

        if sender_role == "customer" and receiver_role == "creator":

            # IMPORTANT:
            # Pricing belongs to the CREATOR (receiver).
            # Never use sender_id for the pricing lookup.

            pricing = (
                db.query(PricingDetail)
                .filter(
                    PricingDetail.user_id == receiver_id
                )
                .first()
            )

            if not pricing:

                logger.error(
                    "Creator pricing not found: "
                    "creator_id=%s customer_id=%s",
                    receiver_id,
                    sender_id,
                )

                raise ValueError(
                    "Pricing details not found for this creator"
                )

            try:

                amount = Decimal(
                    str(pricing.chat_amount or 0)
                )

            except (
                InvalidOperation,
                TypeError,
                ValueError,
            ):

                raise ValueError(
                    "Invalid creator chat pricing"
                )

            if not amount.is_finite() or amount <= 0:
                raise ValueError(
                    "Creator chat price must be greater than zero"
                )

            if amount != amount.to_integral_value():
                raise ValueError(
                    "Chat price must be a whole number of coins"
                )

            coins_to_deduct = int(amount)

            # =====================================
            # LOCK CUSTOMER WALLET
            # =====================================

            wallet = (
                db.query(Wallet)
                .filter(
                    Wallet.user_id == sender_id
                )
                .with_for_update()
                .first()
            )

            if not wallet:
                raise ValueError(
                    "Customer wallet not found"
                )

            if wallet.status != "active":
                raise ValueError(
                    "Customer wallet is not active"
                )

            current_coins = int(wallet.coins or 0)

            logger.info(
                "Customer wallet before deduction: "
                "customer_id=%s wallet_id=%s "
                "coins=%s price=%s",
                sender_id,
                wallet.id,
                current_coins,
                coins_to_deduct,
            )

            if current_coins < coins_to_deduct:
                raise ValueError(
                    "Insufficient customer wallet coins"
                )

            # =====================================
            # DEDUCT CUSTOMER COINS
            # =====================================

            wallet.coins = (
                current_coins - coins_to_deduct
            )

            wallet.spending = (
                Decimal(str(wallet.spending or 0))
                + amount
            )

            wallet.last_transaction = now

            # =====================================
            # CREATE WALLET TRANSACTION
            # =====================================

            transaction = WalletTransaction(
                transaction_id=(
                    f"CHAT-{uuid.uuid4().hex[:20].upper()}"
                ),
                user_id=sender_id,
                wallet_id=wallet.id,
                type="chat",
                amount=amount,
                coins=coins_to_deduct,
                method="wallet",
                status="success",
                created_at=now,
                updated_at=now,
            )

            db.add(transaction)

            db.flush()

            logger.info(
                "Customer coin deduction prepared: "
                "customer_id=%s creator_id=%s "
                "transaction_id=%s deducted=%s remaining=%s",
                sender_id,
                receiver_id,
                transaction.transaction_id,
                coins_to_deduct,
                wallet.coins,
            )

        # =========================================
        # CREATOR -> CUSTOMER
        # NO WALLET DEDUCTION
        # =========================================

        elif sender_role == "creator" and receiver_role == "customer":

            logger.info(
                "Creator message: no wallet deduction. "
                "creator_id=%s customer_id=%s",
                sender_id,
                receiver_id,
            )

        else:

            raise ValueError(
                "Chat messages are only allowed between customers and creators"
            )

        # =========================================
        # VALIDATE REPLY MESSAGE
        # =========================================

        if reply_message_id is not None:

            reply = (
                db.query(ChatMessage)
                .filter(
                    ChatMessage.id == reply_message_id,
                    ChatMessage.chat_id == chat_id,
                    ChatMessage.is_deleted.is_(False),
                )
                .first()
            )

            if not reply:
                raise ValueError(
                    "Reply message not found in this chat"
                )

        # =========================================
        # CREATE CHAT MESSAGE
        # =========================================

        message = ChatMessage(
            chat_id=chat_id,
            sender_id=sender_id,
            receiver_id=receiver_id,
            message=content or None,
            attachment=attachment,
            message_type=message_type,
            message_metadata=message_metadata,
            reply_message_id=reply_message_id,
            is_read=False,
            is_delivered=False,
            is_deleted=False,
            created_at=now,
        )

        db.add(message)

        db.flush()

        # =========================================
        # UPDATE CHAT LAST MESSAGE
        # =========================================

        chat.last_message = (
            content or f"[{message_type}]"
        )

        chat.last_message_at = now
        chat.last_message_by = sender_id

        # =========================================
        # UPDATE UNREAD COUNT
        # =========================================

        if receiver_id == chat.user_one_id:

            chat.unread_count_user1 = (
                (chat.unread_count_user1 or 0) + 1
            )

        else:

            chat.unread_count_user2 = (
                (chat.unread_count_user2 or 0) + 1
            )

        # =========================================
        # COMMIT EVERYTHING TOGETHER
        # =========================================

        db.commit()

        db.refresh(message)

        logger.info(
            "CHAT TRANSACTION COMMITTED: "
            "message_id=%s chat_id=%s "
            "sender_id=%s receiver_id=%s",
            message.id,
            chat_id,
            sender_id,
            receiver_id,
        )

        return message

    except ValueError:

        db.rollback()

        logger.warning(
            "Chat message rejected: "
            "chat_id=%s sender_id=%s",
            chat_id,
            sender_id,
            exc_info=True,
        )

        raise

    except Exception:

        db.rollback()

        logger.exception(
            "Chat transaction failed and rolled back: "
            "chat_id=%s sender_id=%s",
            chat_id,
            sender_id,
        )

        raise
 