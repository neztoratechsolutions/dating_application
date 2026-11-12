from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func

from database import Base


class FraudActionLog(Base):
    __tablename__ = "fraud_action_logs"

    id = Column(Integer, primary_key=True, index=True)

    fraud_alert_id = Column(
        Integer,
        ForeignKey("fraud_alerts.id"),
        nullable=False,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    admin_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    action = Column(String(30), nullable=False)
    remarks = Column(Text, nullable=True)

    suspend_until = Column(DateTime(timezone=True), nullable=True)

    previous_status = Column(String(30), nullable=True)
    new_status = Column(String(30), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )