from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric
from sqlalchemy.sql import func

from database import Base


class VideoCall(Base):
    __tablename__ = "video_calls"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    video_call_id = Column(
        String(20),
        unique=True,
        nullable=False,
        index=True
    )

    customer_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    creator_id = Column(
        Integer,
        ForeignKey("users.id"),
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
        nullable=True
    )

    coins = Column(
        Integer,
        default=0,
        nullable=False
    )

    revenue = Column(
        Numeric(10, 2),
        default=0,
        nullable=False
    )

    status = Column(
        String(20),
        default="pending",
        nullable=False
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )