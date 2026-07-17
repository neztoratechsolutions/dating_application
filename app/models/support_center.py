from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Enum,
    Boolean
)
from sqlalchemy.sql import func

from database import Base


# ==========================================
# SUPPORT TICKET
# ==========================================

class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(Integer, primary_key=True, index=True)

    ticket_id = Column(String(30), unique=True, nullable=False)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    subject = Column(String(255), nullable=False)

    category = Column(
        Enum(
            "Account",
            "Payment",
            "KYC",
            "Chat",
            "Call",
            "Withdrawal",
            "Report User",
            "Other",
            name="support_category_enum"
        ),
        nullable=False
    )

    priority = Column(
        Enum(
            "Low",
            "Medium",
            "High",
            "Urgent",
            name="support_priority_enum"
        ),
        default="Medium"
    )

    status = Column(
        Enum(
            "Open",
            "In Progress",
            "Resolved",
            "Closed",
            name="support_status_enum"
        ),
        default="Open"
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


# ==========================================
# SUPPORT TICKET MESSAGES
# ==========================================

class SupportTicketMessage(Base):
    __tablename__ = "support_ticket_messages"

    id = Column(Integer, primary_key=True, index=True)

    ticket_id = Column(
        Integer,
        ForeignKey("support_tickets.id", ondelete="CASCADE"),
        nullable=False
    )

    sender_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    message = Column(Text, nullable=False)

    attachment = Column(String(255), nullable=True)

    is_admin = Column(Boolean, default=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )