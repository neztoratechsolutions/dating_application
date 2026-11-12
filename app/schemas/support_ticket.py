from enum import Enum
from datetime import datetime
from typing import Optional

from pydantic import BaseModel,Field


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
    subject: str = Field(..., min_length=1, max_length=255)
    category: str
    priority: str = "Medium"
    message: str = Field(..., min_length=1)
    attachment: Optional[str] = None
    user_id: int

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