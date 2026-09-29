from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import SessionLocal
from models.support_center import SupportTicket, SupportTicketMessage


router = APIRouter(
    prefix="/support",
    tags=["Support"]
)


# =========================================================
# DATABASE
# =========================================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =========================================================
# SCHEMAS
# =========================================================

class SupportTicketCreate(BaseModel):
    user_id: int
    subject: str
    category: str


class SupportTicketUpdate(BaseModel):
    subject: str | None = None
    category: str | None = None
    status: str | None = None


# =========================================================
# CREATE SUPPORT TICKET
# =========================================================

@router.post(
    "/tickets/",
    status_code=status.HTTP_201_CREATED
)
def create_support_ticket(
    data: SupportTicketCreate,
    db: Session = Depends(get_db)
):

    allowed_categories = [
        "Account",
        "Payment",
        "KYC",
        "Chat",
        "Call",
        "Withdrawal",
        "Report User",
        "Other"
    ]

    # -----------------------------------------------------
    # CATEGORY VALIDATION
    # -----------------------------------------------------

    if data.category not in allowed_categories:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category. Allowed values: {allowed_categories}"
        )

    # -----------------------------------------------------
    # GENERATE TICKET ID
    # -----------------------------------------------------

    today = datetime.now().strftime("%Y%m%d")

    last_ticket = (
        db.query(SupportTicket)
        .order_by(SupportTicket.id.desc())
        .first()
    )

    if last_ticket:
        sequence = last_ticket.id + 1
    else:
        sequence = 1

    ticket_id = f"TKT-{today}-{sequence:03d}"

    # -----------------------------------------------------
    # CREATE TICKET
    # -----------------------------------------------------

    ticket = SupportTicket(
        ticket_id=ticket_id,
        user_id=data.user_id,
        subject=data.subject,
        category=data.category,
        status="Open"
    )

    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    return {
        "status_code": 201,
        "message": "Support ticket created successfully",
        "data": {
            "id": ticket.id,
            "ticket_id": ticket.ticket_id,
            "user_id": ticket.user_id,
            "subject": ticket.subject,
            "category": ticket.category,
            "status": ticket.status,
            "created_at": ticket.created_at,
            "updated_at": ticket.updated_at
        }
    }


# =========================================================
# GET ALL TICKETS BY USER ID
# =========================================================

@router.get("/tickets/user/{user_id}")
def get_support_tickets_by_user(
    user_id: int,
    db: Session = Depends(get_db)
):

    tickets = (
        db.query(SupportTicket)
        .filter(SupportTicket.user_id == user_id)
        .order_by(SupportTicket.id.desc())
        .all()
    )

    if not tickets:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No support tickets found for this user"
        )

    return {
        "status_code": 200,
        "message": "Support tickets retrieved successfully",
        "user_id": user_id,
        "tickets": [
            {
                "id": ticket.id,
                "ticket_id": ticket.ticket_id,
                "user_id": ticket.user_id,
                "subject": ticket.subject,
                "category": ticket.category,
                "status": ticket.status,
                "created_at": ticket.created_at,
                "updated_at": ticket.updated_at
            }
            for ticket in tickets
        ]
    }


# =========================================================
# GET TICKET BY TICKET ID
# =========================================================

@router.get("/tickets/{ticket_id}")
def get_support_ticket_by_id(
    ticket_id: str,
    db: Session = Depends(get_db)
):

    ticket = (
        db.query(SupportTicket)
        .filter(SupportTicket.ticket_id == ticket_id)
        .first()
    )

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support ticket not found"
        )

    # -----------------------------------------------------
    # GET TICKET MESSAGES
    # -----------------------------------------------------

    messages = (
        db.query(SupportTicketMessage)
        .filter(
            SupportTicketMessage.ticket_id == ticket.id
        )
        .order_by(SupportTicketMessage.id.asc())
        .all()
    )

    return {
        "status_code": 200,
        "message": "Support ticket retrieved successfully",

        "ticket": {
            "id": ticket.id,
            "ticket_id": ticket.ticket_id,
            "user_id": ticket.user_id,
            "subject": ticket.subject,
            "category": ticket.category,
            "status": ticket.status,
            "created_at": ticket.created_at,
            "updated_at": ticket.updated_at
        },

        "messages": [
            {
                "id": msg.id,
                "ticket_id": msg.ticket_id,
                "sender_id": msg.sender_id,
                "message": msg.message,
                "attachment": msg.attachment,
                "is_admin": msg.is_admin,
                "created_at": msg.created_at
            }
            for msg in messages
        ]
    }


# =========================================================
# UPDATE SUPPORT TICKET BY TICKET ID
# =========================================================

@router.put("/tickets/{ticket_id}")
def update_support_ticket(
    ticket_id: str,
    data: SupportTicketUpdate,
    db: Session = Depends(get_db)
):

    ticket = (
        db.query(SupportTicket)
        .filter(SupportTicket.ticket_id == ticket_id)
        .first()
    )

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support ticket not found"
        )

    allowed_categories = [
        "Account",
        "Payment",
        "KYC",
        "Chat",
        "Call",
        "Withdrawal",
        "Report User",
        "Other"
    ]

    allowed_statuses = [
        "Open",
        "In Progress",
        "Resolved",
        "Closed"
    ]

    # -----------------------------------------------------
    # UPDATE SUBJECT
    # -----------------------------------------------------

    if data.subject is not None:
        ticket.subject = data.subject

    # -----------------------------------------------------
    # UPDATE CATEGORY
    # -----------------------------------------------------

    if data.category is not None:

        if data.category not in allowed_categories:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid category. Allowed values: {allowed_categories}"
            )

        ticket.category = data.category

    # -----------------------------------------------------
    # UPDATE STATUS
    # -----------------------------------------------------

    if data.status is not None:

        if data.status not in allowed_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Allowed values: {allowed_statuses}"
            )

        ticket.status = data.status

    db.commit()
    db.refresh(ticket)

    return {
        "status_code": 200,
        "message": "Support ticket updated successfully",
        "data": {
            "id": ticket.id,
            "ticket_id": ticket.ticket_id,
            "user_id": ticket.user_id,
            "subject": ticket.subject,
            "category": ticket.category,
            "status": ticket.status,
            "created_at": ticket.created_at,
            "updated_at": ticket.updated_at
        }
    }


# =========================================================
# DELETE SUPPORT TICKET BY TICKET ID
# =========================================================

@router.delete("/tickets/{ticket_id}")
def delete_support_ticket(
    ticket_id: str,
    db: Session = Depends(get_db)
):

    ticket = (
        db.query(SupportTicket)
        .filter(SupportTicket.ticket_id == ticket_id)
        .first()
    )

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support ticket not found"
        )

    db.delete(ticket)
    db.commit()

    return {
        "status_code": 200,
        "message": "Support ticket deleted successfully",
        "ticket_id": ticket_id
    }






