from sqlalchemy import Column, Integer, String, Boolean, DECIMAL, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.database import Base


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    wallet_id = Column(String(30), unique=True, nullable=False)

    balance = Column(DECIMAL(10, 2), default=0.00)

    coins = Column(Integer, default=0)

    deposits = Column(DECIMAL(10, 2), default=0.00)

    spending = Column(DECIMAL(10, 2), default=0.00)

    last_transaction = Column(DateTime(timezone=True), nullable=True)

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