from sqlalchemy import Column, Integer, DECIMAL, DateTime
from sqlalchemy.sql import func

from database import Base


class GiftRevenue(Base):
    __tablename__ = "gift_revenue"

    id = Column(Integer, primary_key=True, index=True)

    creator_revenue = Column(
        DECIMAL(10, 2),
        nullable=False
    )

    platform_revenue = Column(
        DECIMAL(10, 2),
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