
import csv
import io
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from database import SessionLocal
from models.users import User
from models.state import State
from models.earnings import Earning
from models.withdrawals import Withdrawal


router = APIRouter(
    prefix="/withdrawals",
    tags=["Withdrawals"]
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

class WithdrawalCreate(BaseModel):
    creator_id: int
    amount: Decimal = Field(gt=0)
    bank_name: Optional[str] = None
    account_holder_name: Optional[str] = None
    account_number: Optional[str] = None
    ifsc_code: Optional[str] = None


class WithdrawalUpdate(BaseModel):
    amount: Optional[Decimal] = Field(default=None, gt=0)
    bank_name: Optional[str] = None
    account_holder_name: Optional[str] = None
    account_number: Optional[str] = None
    ifsc_code: Optional[str] = None


class WithdrawalDecision(BaseModel):
    rejection_reason: Optional[str] = None


# =========================================================
# HELPERS
# =========================================================

def generate_withdrawal_id(db: Session) -> str:
    today = date.today()
    prefix = f"WD-{today.strftime('%d-%m-%Y')}-"

    existing_ids = (
        db.query(Withdrawal.withdrawal_id)
        .filter(Withdrawal.withdrawal_id.like(f"{prefix}%"))
        .all()
    )

    numbers = []
    for row in existing_ids:
        try:
            numbers.append(int(row[0].split("-")[-1]))
        except (ValueError, IndexError):
            continue

    next_number = max(numbers, default=0) + 1
    return f"{prefix}{next_number:02d}"


def mask_account_number(account_number):
    if not account_number:
        return None

    account_number = str(account_number)
    if len(account_number) <= 4:
        return "*" * len(account_number)

    return ("X" * (len(account_number) - 4)) + account_number[-4:]


def get_withdrawal_response(item, creator, state_name):
    return {
        "withdrawal_id": item.withdrawal_id,
        "creator_id": item.creator_id,
        "creator_name": creator.display_name if creator else None,
        "creator_email": creator.email if creator else None,
        "creator_state": state_name,
        "bank_name": item.bank_name,
        "account_holder_name": item.account_holder_name,
        "account_number": mask_account_number(item.account_number),
        "ifsc_code": item.ifsc_code,
        "amount": float(item.amount or 0),
        "date": (
            item.requested_at.isoformat()
            if item.requested_at else None
        ),
        "status": item.status,
        "rejection_reason": item.rejection_reason,
        "processed_at": (
            item.processed_at.isoformat()
            if item.processed_at else None
        ),
    }


def base_withdrawal_query(db: Session):
    return (
        db.query(Withdrawal, User, State.state_name)
        .join(User, User.id == Withdrawal.creator_id)
        .outerjoin(State, State.id == User.state_id)
    )


def apply_filters(
    query,
    status_filter=None,
    bank_name=None,
    start_date=None,
    end_date=None,
    search=None,
):
    if status_filter and status_filter.lower() != "all":
        query = query.filter(
            func.lower(Withdrawal.status) == status_filter.lower()
        )

    if bank_name:
        query = query.filter(
            Withdrawal.bank_name.ilike(f"%{bank_name.strip()}%")
        )

    if start_date:
        start_datetime = datetime.combine(start_date, time.min)
        query = query.filter(
            Withdrawal.requested_at >= start_datetime
        )

    if end_date:
        end_datetime = datetime.combine(
            end_date + timedelta(days=1),
            time.min
        )
        query = query.filter(
            Withdrawal.requested_at < end_datetime
        )

    if search:
        search_value = search.strip()
        conditions = [
            User.display_name.ilike(f"%{search_value}%"),
            User.email.ilike(f"%{search_value}%"),
            Withdrawal.withdrawal_id.ilike(f"%{search_value}%"),
            Withdrawal.bank_name.ilike(f"%{search_value}%"),
            Withdrawal.account_holder_name.ilike(f"%{search_value}%"),
        ]

        # Search creator ID when the search text is numeric.
        if search_value.isdigit():
            conditions.append(
                Withdrawal.creator_id == int(search_value)
            )

        query = query.filter(or_(*conditions))

    return query


def get_summary(db: Session):
    today = date.today()
    today_start = datetime.combine(today, time.min)
    tomorrow_start = today_start + timedelta(days=1)

    total_withdrawals = db.query(
        func.count(Withdrawal.id)
    ).scalar() or 0

    pending_count = db.query(
        func.count(Withdrawal.id)
    ).filter(
        func.lower(Withdrawal.status) == "pending"
    ).scalar() or 0

    approved_count = db.query(
        func.count(Withdrawal.id)
    ).filter(
        func.lower(Withdrawal.status) == "approved"
    ).scalar() or 0

    rejected_count = db.query(
        func.count(Withdrawal.id)
    ).filter(
        func.lower(Withdrawal.status) == "rejected"
    ).scalar() or 0

    hold_count = db.query(
        func.count(Withdrawal.id)
    ).filter(
        func.lower(Withdrawal.status) == "hold"
    ).scalar() or 0

    total_payout = db.query(
        func.coalesce(func.sum(Withdrawal.amount), 0)
    ).filter(
        func.lower(Withdrawal.status) == "approved"
    ).scalar() or 0

    today_withdrawals = db.query(
        func.count(Withdrawal.id)
    ).filter(
        Withdrawal.requested_at >= today_start,
        Withdrawal.requested_at < tomorrow_start,
    ).scalar() or 0

    today_withdrawal_amount = db.query(
        func.coalesce(func.sum(Withdrawal.amount), 0)
    ).filter(
        Withdrawal.requested_at >= today_start,
        Withdrawal.requested_at < tomorrow_start,
    ).scalar() or 0

    return {
        "total_withdrawals": total_withdrawals,
        "pending_count": pending_count,
        "approved_count": approved_count,
        "rejected_count": rejected_count,
        "hold_count": hold_count,
        "total_payout": float(total_payout),
        "today_withdrawals": today_withdrawals,
        "today_withdrawal_amount": float(today_withdrawal_amount),
    }


# =========================================================
# GET ALL WITHDRAWALS + SUMMARY + FILTERS + CSV DOWNLOAD
# =========================================================

@router.get("/")
def get_all_withdrawals(
    status_filter: str = Query(
        default="All",
        alias="status"
    ),
    bank_name: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    search: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=500),
    download: Optional[str] = None,
    db: Session = Depends(get_db),
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date cannot be later than end_date"
        )

    # Summary always covers ALL withdrawal records.
    summary = get_summary(db)

    # Filters apply to the records returned in data.
    query = base_withdrawal_query(db)
    query = apply_filters(
        query=query,
        status_filter=status_filter,
        bank_name=bank_name,
        start_date=start_date,
        end_date=end_date,
        search=search,
    )

    query = query.order_by(Withdrawal.requested_at.desc())

    # CSV download: export every matching record, not only current page.
    if download and download.lower() == "csv":
        rows = query.all()

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "Withdrawal ID",
            "Creator ID",
            "Creator Name",
            "Creator Email",
            "Creator State",
            "Bank Name",
            "Account Holder Name",
            "Account Number",
            "IFSC Code",
            "Amount",
            "Date",
            "Status",
            "Rejection Reason",
        ])

        for item, creator, state_name in rows:
            writer.writerow([
                item.withdrawal_id,
                item.creator_id,
                creator.display_name if creator else "",
                creator.email if creator else "",
                state_name or "",
                item.bank_name or "",
                item.account_holder_name or "",
                mask_account_number(item.account_number) or "",
                item.ifsc_code or "",
                item.amount,
                item.requested_at.isoformat()
                if item.requested_at else "",
                item.status,
                item.rejection_reason or "",
            ])

        output.seek(0)

        filename = f"withdrawals_{date.today().isoformat()}.csv"

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{filename}"'
                )
            },
        )

    total_records = query.count()

    rows = (
        query
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    data = [
        get_withdrawal_response(item, creator, state_name)
        for item, creator, state_name in rows
    ]

    return {
        "summary": summary,
        "filters": {
            "status": status_filter,
            "bank_name": bank_name,
            "start_date": (
                start_date.isoformat() if start_date else None
            ),
            "end_date": (
                end_date.isoformat() if end_date else None
            ),
            "search": search,
        },
        "pagination": {
            "page": page,
            "limit": limit,
            "total_records": total_records,
            "total_pages": (
                (total_records + limit - 1) // limit
            ),
        },
        "download": {
            "csv_available": True,
            "download_url": "/withdrawals/?download=csv",
        },
        "data": data,
    }


# =========================================================
# GET WITHDRAWAL BY ID
# =========================================================

@router.get("/{withdrawal_id}")
def get_withdrawal_by_id(
    withdrawal_id: str,
    db: Session = Depends(get_db),
):
    result = (
        base_withdrawal_query(db)
        .filter(Withdrawal.withdrawal_id == withdrawal_id)
        .first()
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Withdrawal not found"
        )

    item, creator, state_name = result

    return {
        "data": get_withdrawal_response(
            item, creator, state_name
        )
    }


# =========================================================
# CREATE WITHDRAWAL
# =========================================================

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_withdrawal(
    payload: WithdrawalCreate,
    db: Session = Depends(get_db),
):
    creator = db.query(User).filter(
        User.id == payload.creator_id
    ).first()

    if not creator:
        raise HTTPException(
            status_code=404,
            detail="Creator not found"
        )

    if str(creator.role).lower() != "creator":
        raise HTTPException(
            status_code=400,
            detail="User is not a creator"
        )

    earning = db.query(Earning).filter(
        Earning.user_id == payload.creator_id
    ).first()

    if not earning:
        raise HTTPException(
            status_code=400,
            detail="Creator wallet/earning record not found"
        )

    if Decimal(str(earning.balance or 0)) < payload.amount:
        raise HTTPException(
            status_code=400,
            detail="Insufficient available balance"
        )

    item = Withdrawal(
        withdrawal_id=generate_withdrawal_id(db),
        creator_id=payload.creator_id,
        amount=payload.amount,
        bank_name=payload.bank_name,
        account_holder_name=payload.account_holder_name,
        account_number=payload.account_number,
        ifsc_code=payload.ifsc_code,
        status="Pending",
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    return {
        "message": "Withdrawal request created successfully",
        "withdrawal_id": item.withdrawal_id,
        "status": item.status,
    }


# =========================================================
# UPDATE PENDING WITHDRAWAL
# =========================================================

@router.put("/{withdrawal_id}")
def update_withdrawal(
    withdrawal_id: str,
    payload: WithdrawalUpdate,
    db: Session = Depends(get_db),
):
    item = db.query(Withdrawal).filter(
        Withdrawal.withdrawal_id == withdrawal_id
    ).first()

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Withdrawal not found"
        )

    if item.status.lower() != "pending":
        raise HTTPException(
            status_code=400,
            detail="Only pending withdrawals can be updated"
        )

    update_data = payload.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)

    return {
        "message": "Withdrawal updated successfully",
        "withdrawal_id": item.withdrawal_id,
        "status": item.status,
    }


# =========================================================
# APPROVE WITHDRAWAL
# =========================================================

@router.patch("/{withdrawal_id}/approve")
def approve_withdrawal(
    withdrawal_id: str,
    db: Session = Depends(get_db),
):
    item = (
        db.query(Withdrawal)
        .filter(Withdrawal.withdrawal_id == withdrawal_id)
        .with_for_update()
        .first()
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Withdrawal not found"
        )

    if item.status.lower() != "pending":
        raise HTTPException(
            status_code=400,
            detail="Only pending withdrawals can be approved"
        )

    earning = (
        db.query(Earning)
        .filter(Earning.user_id == item.creator_id)
        .with_for_update()
        .first()
    )

    if not earning:
        raise HTTPException(
            status_code=404,
            detail="Creator earning record not found"
        )

    amount = Decimal(str(item.amount))
    balance = Decimal(str(earning.balance or 0))

    if balance < amount:
        raise HTTPException(
            status_code=400,
            detail="Insufficient available balance"
        )

    # This updates the internal balance only.
    # It does not perform an actual bank transfer.
    earning.balance = balance - amount
    earning.withdrawal_amount = (
        Decimal(str(earning.withdrawal_amount or 0)) + amount
    )

    item.status = "Approved"
    item.processed_at = datetime.now()

    db.commit()
    db.refresh(item)

    return {
        "message": "Withdrawal approved successfully",
        "withdrawal_id": item.withdrawal_id,
        "status": item.status,
    }


# =========================================================
# REJECT WITHDRAWAL
# =========================================================

@router.patch("/{withdrawal_id}/reject")
def reject_withdrawal(
    withdrawal_id: str,
    payload: WithdrawalDecision,
    db: Session = Depends(get_db),
):
    item = db.query(Withdrawal).filter(
        Withdrawal.withdrawal_id == withdrawal_id
    ).first()

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Withdrawal not found"
        )

    if item.status.lower() != "pending":
        raise HTTPException(
            status_code=400,
            detail="Only pending withdrawals can be rejected"
        )

    item.status = "Rejected"
    item.rejection_reason = payload.rejection_reason
    item.processed_at = datetime.now()

    db.commit()

    return {
        "message": "Withdrawal rejected successfully",
        "withdrawal_id": item.withdrawal_id,
        "status": item.status,
    }


# =========================================================
# HOLD WITHDRAWAL
# =========================================================

@router.patch("/{withdrawal_id}/hold")
def hold_withdrawal(
    withdrawal_id: str,
    db: Session = Depends(get_db),
):
    item = db.query(Withdrawal).filter(
        Withdrawal.withdrawal_id == withdrawal_id
    ).first()

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Withdrawal not found"
        )

    if item.status.lower() != "pending":
        raise HTTPException(
            status_code=400,
            detail="Only pending withdrawals can be put on hold"
        )

    item.status = "Hold"
    item.processed_at = datetime.now()

    db.commit()

    return {
        "message": "Withdrawal put on hold successfully",
        "withdrawal_id": item.withdrawal_id,
        "status": item.status,
    }


# =========================================================
# DELETE PENDING WITHDRAWAL
# =========================================================

@router.delete("/{withdrawal_id}")
def delete_withdrawal(
    withdrawal_id: str,
    db: Session = Depends(get_db),
):
    item = db.query(Withdrawal).filter(
        Withdrawal.withdrawal_id == withdrawal_id
    ).first()

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Withdrawal not found"
        )

    if item.status.lower() != "pending":
        raise HTTPException(
            status_code=400,
            detail="Only pending withdrawals can be deleted"
        )

    db.delete(item)
    db.commit()

    return {
        "message": "Withdrawal deleted successfully"
    }
