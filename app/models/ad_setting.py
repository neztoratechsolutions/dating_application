from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    Date,
    DateTime,
    Enum
)
from sqlalchemy.sql import func

from database import Base


class AdSetting(Base):
    __tablename__ = "ad_settings"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(150), nullable=False)

    description = Column(Text, nullable=True)

    banner_url = Column(String(500), nullable=False)

    redirect_url = Column(String(500), nullable=False)

    placement = Column(String(100), nullable=False)

    start_date = Column(Date, nullable=False)

    end_date = Column(Date, nullable=False)

    status = Column(
        Enum(
            "Active",
            "Scheduled",
            "Expired",
            name="ad_status_enum"
        ),
        default="Active"
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