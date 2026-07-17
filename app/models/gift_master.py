from sqlalchemy import Column, Integer, String, Boolean, DECIMAL, DateTime
from sqlalchemy.sql import func

from database import Base


class GiftMaster(Base):
    __tablename__ = "gift_master"

    id = Column(Integer, primary_key=True, index=True)

    catalog_name = Column(String(100), nullable=False)

    icon = Column(String(255), nullable=True)

    coins = Column(Integer, nullable=False)

    creator_revenue = Column(DECIMAL(10, 2), nullable=False)

    platform_revenue = Column(DECIMAL(10, 2), nullable=False)

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