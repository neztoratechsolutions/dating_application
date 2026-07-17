from sqlalchemy import Column, Integer, DECIMAL, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.database import Base


class GiftDetail(Base):
    __tablename__ = "gift_details"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    sender_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    gift_id = Column(
        Integer,
        ForeignKey("gift_master.id", ondelete="CASCADE"),
        nullable=False
    )

    earnings = Column(DECIMAL(10, 2), default=0.00)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )