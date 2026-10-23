
from sqlalchemy import (
    Column,
    Integer,
    String,
    DECIMAL,
    DateTime,
    ForeignKey,
)
from sqlalchemy.sql import func

from database import Base


class Withdrawal(Base):
    __tablename__ = "withdrawals"

    id = Column(Integer, primary_key=True, index=True)

    # Unique withdrawal reference ID
    withdrawal_id = Column(String(30), unique=True, nullable=False, index=True)

    # Creator who requested withdrawal
    creator_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    amount = Column(DECIMAL(10, 2), nullable=False)

    # Bank details
    bank_name = Column(String(100), nullable=True)
    account_holder_name = Column(String(150), nullable=True)
    account_number = Column(String(50), nullable=True)
    ifsc_code = Column(String(20), nullable=True)

    # Pending, Approved, Rejected, Hold
    status = Column(String(20), nullable=False, default="Pending", index=True)

    rejection_reason = Column(String(500), nullable=True)

    requested_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    processed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
