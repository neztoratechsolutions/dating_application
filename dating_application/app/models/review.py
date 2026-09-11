from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.database import Base


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    star_details = Column(Integer, nullable=False)

    description = Column(Text, nullable=True)

    submitted_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )