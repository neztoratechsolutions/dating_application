from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import SessionLocal
from models.support_center import SupportTicket, SupportTicketMessage
from models.users import User


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


# =========================================================
# ADMIN - SUPPORT TICKET DASHBOARD
# FILTER + SEARCH + COUNTS
# =========================================================

@router.get("/admin/tickets/dashboard")
def admin_get_support_ticket_dashboard(

    priority: str | None = Query(
        default=None,
        description="Filter by priority: Low, Medium, High, Critical"
    ),

    status_filter: str | None = Query(
        default=None,
        alias="status",
        description="Filter by status: Open, In Progress, Resolved, Closed"
    ),

    ticket_id: str | None = Query(
        default=None,
        description="Search by ticket ID"
    ),

    user_name: str | None = Query(
        default=None,
        description="Search by user name"
    ),

    db: Session = Depends(get_db)
):

    # =====================================================
    # ALLOWED VALUES
    # =====================================================

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

    # =====================================================
    # VALIDATE PRIORITY
    # =====================================================

    if priority is not None:

        if priority not in allowed_priorities:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid priority. Allowed values: {allowed_priorities}"
            )

    # =====================================================
    # VALIDATE STATUS
    # =====================================================

    if status_filter is not None:

        if status_filter not in allowed_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Allowed values: {allowed_statuses}"
            )

    # =====================================================
    # BASE QUERY
    # =====================================================

    query = (
        db.query(SupportTicket, User)
        .join(
            User,
            SupportTicket.user_id == User.id
        )
    )

    # =====================================================
    # PRIORITY FILTER
    # =====================================================

    if priority is not None:
        query = query.filter(
            SupportTicket.priority == priority
        )

    # =====================================================
    # STATUS FILTER
    # =====================================================

    if status_filter is not None:
        query = query.filter(
            SupportTicket.status == status_filter
        )

    # =====================================================
    # TICKET ID SEARCH
    # =====================================================

    if ticket_id is not None:
        query = query.filter(
            SupportTicket.ticket_id.ilike(
                f"%{ticket_id}%"
            )
        )

    # =====================================================
    # USER NAME SEARCH
    # =====================================================

    if user_name is not None:
        query = query.filter(
            User.display_name.ilike(
                f"%{user_name}%"
            )
        )

    # =====================================================
    # GET RESULTS
    # =====================================================

    tickets = (
        query
        .order_by(
            SupportTicket.id.desc()
        )
        .all()
    )

    if not tickets:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No support tickets found"
        )

    # =====================================================
    # COUNTS
    # =====================================================

    open_count = 0
    in_progress_count = 0
    resolved_count = 0
    high_priority_count = 0

    for ticket, user in tickets:

        if ticket.status == "Open":
            open_count += 1

        if ticket.status == "In Progress":
            in_progress_count += 1

        if ticket.status == "Resolved":
            resolved_count += 1

        if ticket.priority == "High":
            high_priority_count += 1

    # =====================================================
    # TICKET LIST
    # =====================================================

    ticket_list = []

    for ticket, user in tickets:

        ticket_list.append({
            "ticket_id": ticket.ticket_id,
            "user_id": ticket.user_id,
            "user_name": user.display_name,
            "user_role": user.role,
            "subject": ticket.subject,
            "priority": ticket.priority,
            "status": ticket.status,
            "created_at": ticket.created_at
        })

    # =====================================================
    # RESPONSE
    # =====================================================

    return {
        "status_code": 200,
        "message": "Support ticket dashboard retrieved successfully",

        "summary": {
            "open_tickets": open_count,
            "in_progress": in_progress_count,
            "resolved": resolved_count,
            "high_priority": high_priority_count
        },

        "filters": {
            "priority": priority if priority else "All",
            "status": status_filter if status_filter else "All",
            "ticket_id": ticket_id if ticket_id else None,
            "user_name": user_name if user_name else None
        },

        "tickets": ticket_list
    }