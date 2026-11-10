from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.sql import func

from database import Base


class Referral(Base):
    __tablename__ = "referrals"

    id = Column(Integer, primary_key=True, index=True)

    referrer_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    referred_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    reward_coins = Column(
        Integer,
        nullable=False,
        default=500
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )