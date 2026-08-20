from sqlalchemy import (
    Column,
    Integer,
    String,
    DECIMAL,
    DateTime,
    ForeignKey
)
from sqlalchemy.sql import func

from database import Base


class VoiceCall(Base):
    __tablename__ = "voice_calls"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    call_id = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )

    customer_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    creator_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    start_time = Column(
        DateTime(timezone=True),
        nullable=True
    )

    end_time = Column(
        DateTime(timezone=True),
        nullable=True
    )

    duration = Column(
        Integer,
        default=0
    )

    coins = Column(
        Integer,
        default=0
    )

    revenue = Column(
        DECIMAL(10, 2),
        default=0.00
    )

    status = Column(
        String(20),
        nullable=False,
        default="ongoing"
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )