from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from app.database import Base


class AppSetting(Base):
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, index=True)

    app_name = Column(String(150), nullable=False)

    logo = Column(String(255), nullable=True)

    favicon = Column(String(255), nullable=True)

    support_email = Column(String(150), nullable=True)

    support_number = Column(String(20), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )