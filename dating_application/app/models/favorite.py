from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.sql import func

from app.database import Base

class Favorite(Base):
    __tablename__ = "favorites"

    id=Column(Integer,primary_key=True , index=True)

    customer_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    creator_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False
    )