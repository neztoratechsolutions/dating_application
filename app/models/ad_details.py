from sqlalchemy import Column, Integer, DECIMAL, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.database import Base


class AdDetail(Base):
    __tablename__ = "ad_details"

    id = Column(Integer, primary_key=True, index=True)

    ad_id = Column(
        Integer,
        ForeignKey("ad_settings.id", ondelete="CASCADE"),
        nullable=False
    )

    clicks = Column(Integer, default=0)

    impressions = Column(Integer, default=0)

    ctr = Column(DECIMAL(5, 2), default=0.00)

    revenue = Column(DECIMAL(10, 2), default=0.00)

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