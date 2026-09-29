from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import SessionLocal
from models.support_center import SupportTicket, SupportTicketMessage


router = APIRouter(
    prefix="/support",
    tags=["Support Admin"]
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

class AdminSupportTicketUpdate(BaseModel):
    priority: str | None = None
    status: str | None = None




# =========================================================
# ADMIN - UPDATE PRIORITY / STATUS
# =========================================================

@router.put("/admin/tickets/{ticket_id}")
def admin_update_support_ticket(
    ticket_id: str,
    data: AdminSupportTicketUpdate,
    db: Session = Depends(get_db)
):

    ticket = (
        db.query(SupportTicket)
        .filter(
            SupportTicket.ticket_id == ticket_id
        )
        .first()
    )

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support ticket not found"
        )

    allowed_priorities = [
        "Low",
        "Medium",
        "High",
        "Critical"
    ]

    allowed_statuses = [
        "Open",
        "In Progress",
        "Resolved",
        "Closed"
    ]

    # -----------------------------------------
    # UPDATE PRIORITY
    # -----------------------------------------

    if data.priority is not None:

        if data.priority not in allowed_priorities:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid priority. Allowed values: {allowed_priorities}"
            )

        ticket.priority = data.priority

    # -----------------------------------------
    # UPDATE STATUS
    # -----------------------------------------

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
            "priority": ticket.priority,
            "status": ticket.status,
            "created_at": ticket.created_at,
            "updated_at": ticket.updated_at
        }
    }


# =========================================================
# ADMIN - GET ALL SUPPORT TICKETS
# =========================================================

@router.get("/admin/tickets")
def admin_get_all_support_tickets(
    db: Session = Depends(get_db)
):

    tickets = (
        db.query(SupportTicket)
        .order_by(SupportTicket.id.desc())
        .all()
    )

    if not tickets:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No support tickets found"
        )

    return {
        "status_code": 200,
        "message": "Support tickets retrieved successfully",
        "data": [
            {
                "id": ticket.id,
                "ticket_id": ticket.ticket_id,
                "user_id": ticket.user_id,
                "subject": ticket.subject,
                "category": ticket.category,
                "priority": ticket.priority,
                "status": ticket.status,
                "created_at": ticket.created_at,
                "updated_at": ticket.updated_at
            }
            for ticket in tickets
        ]
    }