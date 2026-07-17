from sqlalchemy import Column, Integer, DECIMAL, DateTime, ForeignKey
from sqlalchemy.sql import func

from database import Base


class Earning(Base):
    __tablename__ = "earnings"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    total_earned = Column(DECIMAL(10, 2), default=0.00)

    withdrawal_amount = Column(DECIMAL(10, 2), default=0.00)

    balance = Column(DECIMAL(10, 2), default=0.00)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )