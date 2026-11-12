from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DECIMAL,
    DateTime,
    ForeignKey
)
from sqlalchemy.sql import func

from database import Base


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    wallet_id = Column(
        String(30),
        unique=True,
        nullable=False,
        index=True
    )

    balance = Column(
        DECIMAL(10, 2),
        default=0.00,
        nullable=False
    )

    coins = Column(
        Integer,
        default=0,
        nullable=False
    )

    deposits = Column(
        DECIMAL(10, 2),
        default=0.00,
        nullable=False
    )

    spending = Column(
        DECIMAL(10, 2),
        default=0.00,
        nullable=False
    )

    last_transaction = Column(
        DateTime(timezone=True),
        nullable=True
    )

    # active / frozen / hold
    status = Column(
        String(20),
        default="active",
        nullable=False
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