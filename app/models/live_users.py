from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Boolean,
)

from sqlalchemy.sql import func

from database import Base


class LiveUserSession(Base):
    __tablename__ = "live_user_sessions"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    session_id = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    device = Column(
        String(100),
        nullable=True
    )

    login_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    last_activity_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )

    logout_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    is_online = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True
    )

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