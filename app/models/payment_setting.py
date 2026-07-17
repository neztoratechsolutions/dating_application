from sqlalchemy import Column, Integer, String, DECIMAL, DateTime
from sqlalchemy.sql import func

from app.database import Base


class PaymentSetting(Base):
    __tablename__ = "payment_settings"

    id = Column(Integer, primary_key=True, index=True)

    razorpay_key_id = Column(String(255), nullable=False)

    razorpay_secret = Column(String(255), nullable=False)

    coin_conversion_rate = Column(DECIMAL(10, 2), nullable=False)

    creator_commission = Column(DECIMAL(5, 2), nullable=False)

    platform_commission = Column(DECIMAL(5, 2), nullable=False)

    gst = Column(DECIMAL(5, 2), nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )