
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from models.chat_history import Chat, ChatMessage

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
    """
    Save a chat message and update the conversation's last-message details.

    The caller must pass a valid SQLAlchemy Session.
    This function commits the transaction before returning the message.
    """

    content = (content or "").strip()
    attachment = attachment or None

    if not content and not attachment:
        raise ValueError("Message content or attachment is required")

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
        # Lock the conversation while validating and updating it.
        chat = (
            db.query(Chat)
            .filter(
                Chat.id == chat_id,
                Chat.status.is_(True),
            )
            .with_for_update()
            .first()
        )

        if chat is None:
            raise ValueError("Chat not found or inactive")

        if sender_id not in (chat.user_one_id, chat.user_two_id):
            raise ValueError("Sender is not a participant in this chat")

        receiver_id = (
            chat.user_two_id
            if sender_id == chat.user_one_id
            else chat.user_one_id
        )

        if reply_message_id is not None:
            reply_message = (
                db.query(ChatMessage)
                .filter(
                    ChatMessage.id == reply_message_id,
                    ChatMessage.chat_id == chat_id,
                    ChatMessage.is_deleted.is_(False),
                )
                .first()
            )

            if reply_message is None:
                raise ValueError("Reply message not found in this chat")

        now = datetime.now(timezone.utc)

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

        chat.last_message = content or f"[{message_type}]"
        chat.last_message_at = now
        chat.last_message_by = sender_id

        # Maintain unread counts for the receiving participant.
        if receiver_id == chat.user_one_id:
            chat.unread_count_user1 = (
                (chat.unread_count_user1 or 0) + 1
            )
        else:
            chat.unread_count_user2 = (
                (chat.unread_count_user2 or 0) + 1
            )

        db.commit()
        db.refresh(message)

        logger.info(
            "Chat message saved successfully: "
            "message_id=%s chat_id=%s sender_id=%s receiver_id=%s",
            message.id,
            chat_id,
            sender_id,
            receiver_id,
        )

        return message

    except ValueError:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        logger.exception(
            "Database error saving chat message: chat_id=%s sender_id=%s",
            chat_id,
            sender_id,
        )
        raise
