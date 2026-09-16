from sqlalchemy import Column, Integer, Boolean, DateTime
from sqlalchemy.sql import func

from app.database import Base


class QuickPack(Base):
    __tablename__ = "quick_packs"

    id = Column(Integer, primary_key=True, index=True)

    coins = Column(Integer, nullable=False)

    bonus = Column(Integer, nullable=False, default=0)

    mrp = Column(Integer, nullable=False)

    is_active = Column(
        Boolean,
        nullable=False,
        default=True
    )

    display_order = Column(
        Integer,
        nullable=False,
        default=0
    )

    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False
    )

    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )