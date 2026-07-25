from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid

from database import get_db
from models.support_center import SupportTicket
from models.users import User
from schemas.support_ticket import (SupportTicketCreate,SupportTicketUpdate,SupportTicketResponse)

router = APIRouter( prefix="/support_ticket", tags=["support_ticket"])

@router.post(
    "/",
    response_model=SupportTicketResponse,
    status_code=status.HTTP_201_CREATED
)
def create_ticket(
    data: SupportTicketCreate,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.id == data.user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    ticket = SupportTicket(
        ticket_id=f"TKT-{uuid.uuid4().hex[:6].upper()}",
        user_id=data.user_id,
        subject=data.subject,
        category=data.category,
        priority=data.priority
    )

    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    return ticket



@router.get(
    "/",
    response_model=list[SupportTicketResponse],
    status_code=status.HTTP_200_OK
)
def get_tickets(
    db: Session = Depends(get_db)
):
    tickets = db.query(
        SupportTicket
    ).all()

    if not tickets:
        raise HTTPException(
            status_code=404,
            detail="Data not found"
        )

    return tickets



@router.get(
    "/{ticket_id}",
    response_model=SupportTicketResponse,
    status_code=status.HTTP_200_OK
)
def get_ticket_by_id(
    ticket_id: int,
    db: Session = Depends(get_db)
):
    ticket = db.query(
        SupportTicket
    ).filter(
        SupportTicket.id == ticket_id
    ).first()

    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="Data not found"
        )

    user = db.query(User).filter(
        User.id == ticket.user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return ticket



@router.put(
    "/{ticket_id}",
    response_model=SupportTicketResponse,
    status_code=status.HTTP_200_OK
)
def update_ticket(
    ticket_id: int,
    data: SupportTicketUpdate,
    db: Session = Depends(get_db)
):
    ticket = db.query(
        SupportTicket
    ).filter(
        SupportTicket.id == ticket_id
    ).first()

    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="Data not found"
        )

    update_data = data.model_dump(
        exclude_unset=True
    )

    for key, value in update_data.items():
        setattr(ticket, key, value)

    db.commit()
    db.refresh(ticket)

    return ticket



@router.delete(
    "/{ticket_id}",
    status_code=status.HTTP_200_OK
)
def delete_ticket(
    ticket_id: int,
    db: Session = Depends(get_db)
):
    ticket = db.query(
        SupportTicket
    ).filter(
        SupportTicket.id == ticket_id
    ).first()

    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="Data not found"
        )

    db.delete(ticket)
    db.commit()

    return {
        "message": "Support ticket deleted successfully"
    }




@router.get(
    "/dashboard/counts",
    status_code=status.HTTP_200_OK
)
def support_dashboard_counts(
    db: Session = Depends(get_db)
):
    return {
        "open_tickets": db.query(
            SupportTicket
        ).filter(
            SupportTicket.status == "Open"
        ).count(),

        "in_progress": db.query(
            SupportTicket
        ).filter(
            SupportTicket.status == "In Progress"
        ).count(),

        "resolved": db.query(
            SupportTicket
        ).filter(
            SupportTicket.status == "Resolved"
        ).count(),

        "high_priority": db.query(
            SupportTicket
        ).filter(
            SupportTicket.priority.in_(
                ["High", "Urgent"]
            )
        ).count()
    }