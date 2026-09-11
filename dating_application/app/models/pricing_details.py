from sqlalchemy import Column, Integer, DECIMAL, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.database import Base


class PricingDetail(Base):
    __tablename__ = "pricing_details"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    chat_amount = Column(DECIMAL(10, 2), nullable=False, default=0.00)

    voice_call_amount = Column(DECIMAL(10, 2), nullable=False, default=0.00)

    video_call_amount = Column(DECIMAL(10, 2), nullable=False, default=0.00)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )