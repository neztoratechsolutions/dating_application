from sqlalchemy import Column, Integer, String, Boolean, DECIMAL, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.database import Base


class GameSetting(Base):
    __tablename__ = "game_settings"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(100), nullable=False)

    entry_fees = Column(DECIMAL(10, 2), nullable=False, default=0.00)

    rewards = Column(DECIMAL(10, 2), nullable=False, default=0.00)

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


class GamePaymentDetail(Base):
    __tablename__ = "game_payment_details"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    game_id = Column(
        Integer,
        ForeignKey("game_settings.id", ondelete="CASCADE"),
        nullable=False
    )

    paid = Column(DECIMAL(10, 2), nullable=False, default=0.00)

    paid_date = Column(DateTime(timezone=True), server_default=func.now())

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