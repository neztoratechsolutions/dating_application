from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.sql import func

from database import Base


class CreatorVerification(Base):
    __tablename__ = "creator_verifications"

    id = Column(Integer, primary_key=True, index=True)

    creator_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )

    voice_file = Column(String(255), nullable=True)
    voice_duration = Column(Float, nullable=True)
    voice_status = Column(String(30), default="pending", nullable=False)

    selfie_image = Column(String(255), nullable=True)
    selfie_status = Column(String(30), default="pending", nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )