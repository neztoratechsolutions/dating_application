from sqlalchemy import Column, Integer, Boolean, DECIMAL, DateTime
from sqlalchemy.sql import func

from database import Base


class CallSetting(Base):
    __tablename__ = "call_settings"

    id = Column(Integer, primary_key=True, index=True)

    minimum_call_duration = Column(Integer, nullable=False)

    voice_call_pricing = Column(DECIMAL(10, 2), nullable=False)

    video_call_pricing = Column(DECIMAL(10, 2), nullable=False)

    auto_disconnect = Column(Boolean, default=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )