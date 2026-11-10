from sqlalchemy import (
    Column,
    Integer,
    DECIMAL,
    DateTime,
    ForeignKey,
    String
)
from sqlalchemy.sql import func

from database import Base


class WithdrawalRequest(Base):
    __tablename__ = "withdrawal_requests"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    amount = Column(
        DECIMAL(10, 2),
        nullable=False
    )

    status = Column(
        String(20),
        nullable=False,
        default="pending"
    )

    requested_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    approved_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    rejected_at = Column(
        DateTime(timezone=True),
        nullable=True
    )
