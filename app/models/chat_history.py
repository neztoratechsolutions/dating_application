from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    Enum,
    DECIMAL
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from database import Base


# ==========================
# CHAT CONVERSATION
# ==========================

class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)

    user_one_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    user_two_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    last_message = Column(Text, nullable=True)

    last_message_at = Column(DateTime(timezone=True))

    last_message_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    unread_count_user1 = Column(Integer, default=0)

    unread_count_user2 = Column(Integer, default=0)

    status = Column(Boolean, default=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )


# ==========================
# CHAT MESSAGES
# ==========================

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)

    chat_id = Column(
        Integer,
        ForeignKey("chats.id", ondelete="CASCADE"),
        nullable=False
    )

    sender_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    receiver_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    message = Column(Text, nullable=True)

    attachment = Column(String(255), nullable=True)

    message_type = Column(
        Enum(
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
            name="message_type_enum"
        ),
        default="text"
    )

    metadata = Column(JSONB, nullable=True)

    is_read = Column(Boolean, default=False)

    is_delivered = Column(Boolean, default=False)

    is_deleted = Column(Boolean, default=False)

    reply_message_id = Column(
        Integer,
        ForeignKey("chat_messages.id"),
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )


# ==========================
# CALL HISTORY
# ==========================

class ChatCallLog(Base):
    __tablename__ = "chat_call_logs"

    id = Column(Integer, primary_key=True, index=True)

    chat_id = Column(
        Integer,
        ForeignKey("chats.id", ondelete="CASCADE"),
        nullable=False
    )

    caller_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    receiver_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    call_type = Column(
        Enum(
            "voice",
            "video",
            name="call_type_enum"
        ),
        nullable=False
    )

    duration = Column(Integer, default=0)

    amount = Column(DECIMAL(10, 2), default=0.00)

    status = Column(
        Enum(
            "missed",
            "completed",
            "rejected",
            "cancelled",
            name="call_status_enum"
        ),
        default="completed"
    )

    started_at = Column(DateTime(timezone=True))

    ended_at = Column(DateTime(timezone=True))

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )


# ==========================
# MESSAGE REACTIONS
# ==========================

class ChatReaction(Base):
    __tablename__ = "chat_reactions"

    id = Column(Integer, primary_key=True, index=True)

    message_id = Column(
        Integer,
        ForeignKey("chat_messages.id", ondelete="CASCADE"),
        nullable=False
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    reaction = Column(String(20), nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )


# ==========================
# MESSAGE DELETE HISTORY
# ==========================

class ChatDeleteHistory(Base):
    __tablename__ = "chat_delete_history"

    id = Column(Integer, primary_key=True, index=True)

    message_id = Column(
        Integer,
        ForeignKey("chat_messages.id", ondelete="CASCADE"),
        nullable=False
    )

    deleted_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    delete_type = Column(
        Enum(
            "me",
            "everyone",
            name="delete_type_enum"
        ),
        default="me"
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )