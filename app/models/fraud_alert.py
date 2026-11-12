from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func

from database import Base


class FraudAlert(Base):
    __tablename__ = "fraud_alerts"

    id = Column(Integer, primary_key=True, index=True)
    alert_code = Column(String(30), unique=True, nullable=False, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    risk_score = Column(Integer, nullable=False, default=0)
    risk_level = Column(String(20), nullable=False, default="low")
    risk_type = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    state_id = Column(
        Integer,
        ForeignKey("states.id"),
        nullable=True
    )

    status = Column(String(30), nullable=False, default="open")

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )