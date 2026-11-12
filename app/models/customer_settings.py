from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.sql import func

from database import Base


class CustomerSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    customer_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )

    push_notifications = Column(
        String(20),
        nullable=False,
        default="Active"
    )

    online_status = Column(
        String(20),
        nullable=False,
        default="Active"
    )

    show_in_search = Column(
        String(20),
        nullable=False,
        default="Active"
    )

    auto_recharge_coins = Column(
        String(20),
        nullable=False,
        default="Inactive"
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