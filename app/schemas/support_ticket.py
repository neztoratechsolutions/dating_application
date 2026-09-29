from enum import Enum
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# =========================
# ENUMS
# =========================

class SupportCategory(str, Enum):
    ACCOUNT = "Account"
    PAYMENT = "Payment"
    KYC = "KYC"
    CHAT = "Chat"
    CALL = "Call"
    WITHDRAWAL = "Withdrawal"
    REPORT_USER = "Report User"
    OTHER = "Other"


class SupportPriority(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    URGENT = "Urgent"


class SupportStatus(str, Enum):
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"
    CLOSED = "Closed"


# =========================
# CREATE
# =========================

class SupportTicketCreate(BaseModel):
    user_id: int
    subject: str
    category: SupportCategory
    priority: SupportPriority = SupportPriority.MEDIUM


# =========================
# UPDATE
# =========================

class SupportTicketUpdate(BaseModel):
    subject: Optional[str] = None
    category: Optional[SupportCategory] = None
    priority: Optional[SupportPriority] = None
    status: Optional[SupportStatus] = None


# =========================
# RESPONSE
# =========================

class SupportTicketResponse(BaseModel):
    id: int
    ticket_id: str
    user_id: int
    subject: str
    category: str
    priority: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True