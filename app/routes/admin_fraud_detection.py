from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from collections import defaultdict

from database import get_db

from models.users import User
from models.state import State
from models.kyc_detail import KYCDetail, CreatorKYC
from models.Withdrawal import Withdrawal
from models.wallet import Wallet
from models.wallet_transaction import WalletTransaction

from models.fraud_alert import FraudAlert
from models.fraud_action_log import FraudActionLog

from schemas.fraud_detection import (
    CreateFraudAlert,
    UpdateFraudAlert,
    AdminActionRequest,
    SuspendRequest
)


router = APIRouter(
    prefix="/admin/fraud",
    tags=["Admin Fraud Detection"]
)


# ---------------------------------------------------------
# COMMON FUNCTIONS
# ---------------------------------------------------------

def validate_admin(db: Session, admin_id: int):
    """
    Development-only admin validation.

    This checks whether the supplied ID belongs to an admin.
    It is NOT secure authentication because a caller can
    submit another admin's ID.
    """

    admin = db.query(User).filter(
        User.id == admin_id,
        User.role == "admin"
    ).first()

    if not admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    return admin


def get_risk_level(score: int):
    if score >= 60:
        return "high"
    elif score >= 30:
        return "medium"
    return "low"


def generate_alert_code():
    return f"FR-{uuid4().hex[:8].upper()}"


def log_admin_action(
    db: Session,
    alert: FraudAlert,
    admin_id: int,
    action: str,
    remarks: str = None,
    suspend_until: datetime = None
):
    log = FraudActionLog(
        fraud_alert_id=alert.id,
        user_id=alert.user_id,
        admin_id=admin_id,
        action=action,
        remarks=remarks,
        suspend_until=suspend_until
    )

    db.add(log)


def decimal_to_float(value):
    if value is None:
        return 0.0

    return float(value)


def get_alert_or_404(db: Session, alert_id: int):
    alert = db.query(FraudAlert).filter(
        FraudAlert.id == alert_id
    ).first()

    if not alert:
        raise HTTPException(
            status_code=404,
            detail="Fraud alert not found"
        )

    return alert

def apply_fraud_decision(
    db: Session,
    alert: FraudAlert,
    admin_id: int,
    new_status: str,
    action: str,
    remarks: str = None,
    suspend_until: datetime = None
):
    user = db.query(User).filter(
        User.id == alert.user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    if user.role not in ["customer", "creator"]:
        raise HTTPException(
            status_code=400,
            detail="Only customer or creator accounts can be updated"
        )

    previous_status = alert.status

    # Ban or suspend: deactivate account
    if new_status in ["suspended", "banned"]:
        user.is_active = False

    # If changing from a restricted status to safe/investigating,
    # reactivate only when no other fraud alert restricts this user.
    elif previous_status in ["suspended", "banned"]:
        other_restriction = db.query(FraudAlert).filter(
            FraudAlert.user_id == user.id,
            FraudAlert.id != alert.id,
            FraudAlert.status.in_(["suspended", "banned"])
        ).first()

        if not other_restriction:
            user.is_active = True

    # Update alert status
    alert.status = new_status

    # Save action history
    action_log = FraudActionLog(
        fraud_alert_id=alert.id,
        user_id=user.id,
        admin_id=admin_id,
        action=action,
        previous_status=previous_status,
        new_status=new_status,
        remarks=remarks,
        suspend_until=suspend_until
    )

    db.add(action_log)

    try:
        db.commit()
        db.refresh(alert)
        db.refresh(user)
        db.refresh(action_log)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to update fraud decision"
        )

    return {
        "message": "Fraud decision updated successfully",
        "alert_id": alert.id,
        "alert_code": alert.alert_code,
        "user_id": user.id,
        "user_name": user.display_name,
        "previous_status": previous_status,
        "status": alert.status,
        "is_active": user.is_active,
        "action": action,
        "remarks": remarks,
        "suspend_until": suspend_until
    }


# ---------------------------------------------------------
# 1. FRAUD DASHBOARD
# GET /admin/fraud/dashboard
# ---------------------------------------------------------


@router.get("/dashboard")
def fraud_dashboard(db: Session = Depends(get_db)):

    # 1. Total Fraud Alerts
    total_alerts = db.query(
        FraudAlert
    ).count()

    # 2. Suspicious Accounts
    suspicious_accounts = db.query(
        func.count(func.distinct(FraudAlert.user_id))
    ).filter(
        FraudAlert.risk_score >= 30
    ).scalar() or 0

    # 3. Duplicate KYC
    duplicate_kyc = db.query(
        FraudAlert
    ).filter(
        or_(
            FraudAlert.risk_type.ilike("%kyc%"),
            FraudAlert.risk_type.ilike("%aadhaar%"),
            FraudAlert.risk_type.ilike("%aadhar%")
        )
    ).count()

    # 4. Suspicious Withdrawals
    suspicious_withdrawals = db.query(
        FraudAlert
    ).filter(
        FraudAlert.risk_type.ilike("%withdraw%")
    ).count()

    # 5. High Risk Users
    high_risk_users = db.query(
        func.count(func.distinct(FraudAlert.user_id))
    ).filter(
        func.lower(FraudAlert.risk_level) == "high"
    ).scalar() or 0

    # 6. Blocked Accounts
    blocked_accounts = db.query(
        func.count(func.distinct(User.id))
    ).join(
        FraudActionLog,
        FraudActionLog.user_id == User.id
    ).filter(
        User.is_active.is_(False),
        FraudActionLog.action.in_(["suspend", "ban"])
    ).scalar() or 0

    return {
        "fraud_alerts": total_alerts,
        "suspicious_accounts": suspicious_accounts,
        "duplicate_kyc": duplicate_kyc,
        "suspicious_withdrawals": suspicious_withdrawals,
        "high_risk_users": high_risk_users,
        "blocked_accounts": blocked_accounts
    }


# ---------------------------------------------------------
# 2. FRAUD TRENDS
# GET /admin/fraud/trends?days=7
# ---------------------------------------------------------


@router.get("/trends")
def get_fraud_trends(
    days: int = Query(default=7, ge=1, le=90),
    db: Session = Depends(get_db)
):
    # Today's date
    today = datetime.now(timezone.utc).date()

    # Calculate starting date
    start_date = today - timedelta(days=days - 1)

    start_datetime = datetime.combine(
        start_date,
        datetime.min.time(),
        tzinfo=timezone.utc
    )

    # Get daily fraud alert counts
    results = db.query(
        func.date(FraudAlert.created_at).label("alert_date"),
        func.count(FraudAlert.id).label("total")
    ).filter(
        FraudAlert.created_at >= start_datetime
    ).group_by(
        func.date(FraudAlert.created_at)
    ).order_by(
        func.date(FraudAlert.created_at)
    ).all()

    # Store database results
    trend_map = {
        str(row.alert_date): row.total
        for row in results
    }

    # Include dates with zero alerts
    data = []

    for i in range(days):
        current_date = start_date + timedelta(days=i)

        data.append({
            "date": str(current_date),
            "day": current_date.strftime("%a"),
            "total_alerts": trend_map.get(
                str(current_date), 0
            )
        })

    return {
        "period": f"Last {days} days",
        "total_alerts": sum(
            item["total_alerts"] for item in data
        ),
        "data": data
    }


# ---------------------------------------------------------
# 3. STATE ANALYTICS
# GET /admin/fraud/state-analytics
# ---------------------------------------------------------


@router.get("/state-analytics")
def get_state_analytics(
    db: Session = Depends(get_db)
):
    results = db.query(
        State.id.label("state_id"),
        State.state_name.label("state_name"),
        func.count(FraudAlert.id).label("total_alerts")
    ).outerjoin(
        FraudAlert,
        FraudAlert.state_id == State.id
    ).group_by(
        State.id,
        State.state_name
    ).order_by(
        func.count(FraudAlert.id).desc(),
        State.state_name.asc()
    ).all()

    data = [
        {
            "state_id": row.state_id,
            "state_name": row.state_name,
            "total_alerts": row.total_alerts
        }
        for row in results
    ]

    total_alerts = sum(
        item["total_alerts"] for item in data
    )

    return {
        "total_states": len(data),
        "total_alerts": total_alerts,
        "data": data
    }



# ---------------------------------------------------------
# 4. CREATE FRAUD ALERT
# POST /admin/fraud/alerts
# ---------------------------------------------------------


@router.post("/alerts")
def create_fraud_alert(
    data: CreateFraudAlert,
    db: Session = Depends(get_db)
):
    # Validate admin
    validate_admin(db, data.admin_id)

    # Find selected user
    user = db.query(User).filter(
        User.id == data.user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # Only customer or creator accounts can be flagged
    if user.role not in ["customer", "creator"]:
        raise HTTPException(
            status_code=400,
            detail="Only customer or creator accounts can be flagged"
        )

    # Use selected state, or user's registered state
    selected_state_id = (
        data.state_id
        if data.state_id is not None
        else user.state_id
    )

    if selected_state_id is not None:
        state = db.query(State).filter(
            State.id == selected_state_id
        ).first()

        if not state:
            raise HTTPException(
                status_code=404,
                detail="State not found"
            )

    # Default score based on admin-selected risk level
    default_scores = {
        "low": 20,
        "medium": 45,
        "high": 80
    }

    score = (
        data.risk_score
        if data.risk_score is not None
        else default_scores[data.risk_level]
    )

    # Create fraud alert
    alert = FraudAlert(
        alert_code=generate_alert_code(),
        user_id=user.id,
        risk_score=score,
        risk_level=data.risk_level,
        risk_type=data.risk_type,
        description=data.description,
        state_id=selected_state_id,
        status="open"
    )

    db.add(alert)
    db.commit()
    db.refresh(alert)

    return {
        "message": "Fraud alert created successfully",
        "data": {
            "id": alert.id,
            "alert_code": alert.alert_code,
            "user_id": alert.user_id,
            "user_name": user.display_name,
            "state_id": alert.state_id,
            "risk_score": alert.risk_score,
            "risk_level": alert.risk_level,
            "risk_type": alert.risk_type,
            "description": alert.description,
            "status": alert.status,
            "created_at": alert.created_at
        }
    }


# ---------------------------------------------------------
# 5. GET ALL FRAUD ALERTS
# GET /admin/fraud/alerts
# ---------------------------------------------------------

@router.get("/alerts")
def get_fraud_alerts(
    search: str = None,
    status: str = None,
    risk_level: str = None,
    risk_type: str = None,
    state_id: int = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = (
        db.query(
            FraudAlert,
            User.display_name,
            User.email,
            User.role,
            State.state_name
        )
        .join(User, User.id == FraudAlert.user_id)
        .outerjoin(State, State.id == FraudAlert.state_id)
    )

    # Search by user name, email, or alert code
    if search:
        search_value = f"%{search.strip()}%"
        query = query.filter(
            (User.display_name.ilike(search_value)) |
            (User.email.ilike(search_value)) |
            (FraudAlert.alert_code.ilike(search_value))
        )

    # Filter by alert status
    if status:
        query = query.filter(
            FraudAlert.status.ilike(status.strip())
        )

    # Filter by risk level
    if risk_level:
        query = query.filter(
            FraudAlert.risk_level.ilike(risk_level.strip())
        )

    # Filter by risk type
    if risk_type:
        query = query.filter(
            FraudAlert.risk_type.ilike(f"%{risk_type.strip()}%")
        )

    # Filter by state
    if state_id is not None:
        query = query.filter(
            FraudAlert.state_id == state_id
        )

    # Count filtered records before pagination
    total = query.count()

    # Pagination
    offset = (page - 1) * limit

    results = (
        query
        .order_by(FraudAlert.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    data = []

    for alert, user_name, email, role, state_name in results:
        data.append({
            "id": alert.id,
            "alert_code": alert.alert_code,
            "user_id": alert.user_id,
            "user_name": user_name,
            "email": email,
            "role": role,
            "state_id": alert.state_id,
            "state": state_name,
            "risk_score": alert.risk_score,
            "risk_level": alert.risk_level,
            "risk_type": alert.risk_type,
            "description": alert.description,
            "status": alert.status,
            "created_at": alert.created_at,
            "updated_at": alert.updated_at
        })

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit,
        "data": data
    }


# ---------------------------------------------------------
# 7. ALERT DETAILS POPUP
# GET /admin/fraud/alerts/{alert_id}/details
# ---------------------------------------------------------

@router.get("/alerts/{alert_id}/details")
def get_fraud_alert_details(
    alert_id: int,
    db: Session = Depends(get_db)
):

    alert = get_alert_or_404(db, alert_id)

    user = db.query(User).filter(
        User.id == alert.user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Alert user not found"
        )

    state = None

    if user.state_id:
        state = db.query(State).filter(
            State.id == user.state_id
        ).first()

    # Customer KYC
    kyc = db.query(KYCDetail).filter(
        KYCDetail.user_id == user.id
    ).first()

    # Creator bank KYC
    creator_kyc = db.query(CreatorKYC).filter(
        CreatorKYC.user_id == user.id
    ).first()

    # Wallet
    wallet = db.query(Wallet).filter(
        Wallet.user_id == user.id
    ).first()

    # Withdrawals
    withdrawals = db.query(Withdrawal).filter(
        Withdrawal.creator_id == user.id
    ).order_by(
        Withdrawal.requested_at.desc()
    ).all()

    withdrawal_data = []

    for withdrawal in withdrawals:
        account_number = withdrawal.account_number or ""

        masked_account = (
            "*" * max(0, len(account_number) - 4)
            + account_number[-4:]
            if account_number else None
        )

        withdrawal_data.append({
            "withdrawal_id": withdrawal.withdrawal_id,
            "amount": decimal_to_float(withdrawal.amount),
            "status": withdrawal.status,
            "bank_name": withdrawal.bank_name,
            "account_holder_name": withdrawal.account_holder_name,
            "masked_account_number": masked_account,
            "ifsc_code": withdrawal.ifsc_code,
            "requested_at": withdrawal.requested_at,
            "processed_at": withdrawal.processed_at,
            "rejection_reason": withdrawal.rejection_reason
        })

    # Wallet transaction history
    transactions = []

    if wallet:
        wallet_transactions = db.query(
            WalletTransaction
        ).filter(
            WalletTransaction.wallet_id == wallet.id
        ).order_by(
            WalletTransaction.created_at.desc()
        ).limit(20).all()

        for transaction in wallet_transactions:
            transactions.append({
                "transaction_id": transaction.transaction_id,
                "type": transaction.type,
                "amount": decimal_to_float(transaction.amount),
                "coins": transaction.coins,
                "method": transaction.method,
                "status": transaction.status,
                "created_at": transaction.created_at
            })

    # Withdrawal totals
    total_withdrawals = sum(
        decimal_to_float(item.amount)
        for item in withdrawals
        if (item.status or "").lower() == "approved"
    )

    pending_withdrawals = sum(
        decimal_to_float(item.amount)
        for item in withdrawals
        if (item.status or "").lower() in ["pending", "hold"]
    )

    kyc_documents = []

    if kyc:
        kyc_documents = [
            {
                "document_type": "Aadhaar",
                "photo": kyc.aadhar_photo,
                "status": kyc.aadhar_status
            },
            {
                "document_type": "PAN",
                "photo": kyc.pan_photo,
                "status": kyc.pan_status
            },
            {
                "document_type": "Selfie",
                "photo": kyc.selfie_photo,
                "status": kyc.selfie_status
            }
        ]

    if creator_kyc:
        kyc_documents.append({
            "document_type": "Bank Document",
            "photo": creator_kyc.bank_photo,
            "status": creator_kyc.bank_status
        })

    return {
        "alert": {
            "id": alert.id,
            "alert_code": alert.alert_code,
            "risk_score": alert.risk_score,
            "risk_level": alert.risk_level,
            "risk_type": alert.risk_type,
            "description": alert.description,
            "status": alert.status,
            "created_at": alert.created_at
        },

        "user": {
            "user_id": user.id,
            "name": user.display_name,
            "email": user.email,
            "phone": user.phone,
            "profile_photo": user.profile_photo,
            "role": user.role,
            "state": state.state_name if state else None,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "joined_at": user.created_at
        },

        "kyc_documents": kyc_documents,

        "wallet_activity": {
            "wallet_id": wallet.wallet_id if wallet else None,
            "balance": decimal_to_float(wallet.balance) if wallet else 0,
            "coins": wallet.coins if wallet else 0,
            "deposits": decimal_to_float(wallet.deposits) if wallet else 0,
            "spending": decimal_to_float(wallet.spending) if wallet else 0,
            "approved_withdrawals": total_withdrawals,
            "pending_withdrawals": pending_withdrawals
        },

        "wallet_transactions": transactions,
        "withdrawal_history": withdrawal_data
    }


# ---------------------------------------------------------
# 8. UPDATE FRAUD ALERT
# PUT /admin/fraud/alerts/{alert_id}
# ---------------------------------------------------------


@router.get("/alerts/{alert_id}")
def get_fraud_alert_details(
    alert_id: int,
    db: Session = Depends(get_db)
):
    # 1. Find fraud alert and user details
    result = (
        db.query(
            FraudAlert,
            User.display_name,
            User.email,
            User.phone,
            User.role,
            State.state_name
        )
        .join(User, User.id == FraudAlert.user_id)
        .outerjoin(State, State.id == FraudAlert.state_id)
        .filter(FraudAlert.id == alert_id)
        .first()
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Fraud alert not found"
        )

    alert, user_name, email, phone, role, state_name = result

    user_id = alert.user_id

    # 2. Wallet details
    wallet = db.query(Wallet).filter(
        Wallet.user_id == user_id
    ).first()

    deposits = float(wallet.deposits or 0) if wallet else 0

    # 3. Total approved withdrawals
    total_withdrawals = (
        db.query(func.coalesce(func.sum(Withdrawal.amount), 0))
        .filter(
            Withdrawal.creator_id == user_id,
            Withdrawal.status.ilike("Approved")
        )
        .scalar()
    )

    # 4. Pending withdrawals
    pending_amount = (
        db.query(func.coalesce(func.sum(Withdrawal.amount), 0))
        .filter(
            Withdrawal.creator_id == user_id,
            Withdrawal.status.in_(["Pending", "Hold"])
        )
        .scalar()
    )

    # 5. KYC documents
    kyc = db.query(KYCDetail).filter(
        KYCDetail.user_id == user_id
    ).first()

    kyc_documents = {
        "aadhaar": kyc.aadhar_status if kyc else "Not Submitted",
        "pan": kyc.pan_status if kyc else "Not Submitted",
        "selfie": kyc.selfie_status if kyc else "Not Submitted"
    }

    # 6. Withdrawal history - latest 5 records
    withdrawal_records = (
        db.query(Withdrawal)
        .filter(Withdrawal.creator_id == user_id)
        .order_by(Withdrawal.requested_at.desc())
        .limit(5)
        .all()
    )

    withdrawal_history = []

    for withdrawal in withdrawal_records:
        withdrawal_history.append({
            "withdrawal_id": withdrawal.withdrawal_id,
            "date": withdrawal.requested_at,
            "amount": float(withdrawal.amount or 0),
            "status": withdrawal.status
        })

    # 7. Admin action history
    action_logs = (
        db.query(
            FraudActionLog,
            User.display_name
        )
        .join(
            User,
            User.id == FraudActionLog.admin_id
        )
        .filter(
            FraudActionLog.fraud_alert_id == alert_id
        )
        .order_by(FraudActionLog.created_at.desc())
        .all()
    )

    action_history = []

    for log, admin_name in action_logs:
        action_history.append({
            "id": log.id,
            "admin_id": log.admin_id,
            "admin_name": admin_name,
            "action": log.action,
            "remarks": log.remarks,
            "suspend_until": log.suspend_until,
            "previous_status": log.previous_status,
            "new_status": log.new_status,
            "created_at": log.created_at
        })

    # 8. Final response
    return {
        "alert": {
            "id": alert.id,
            "alert_code": alert.alert_code,
            "user_id": user_id,
            "user_name": user_name,
            "email": email,
            "phone": phone,
            "role": role,
            "state_id": alert.state_id,
            "state": state_name,
            "risk_score": alert.risk_score,
            "risk_level": alert.risk_level,
            "risk_type": alert.risk_type,
            "description": alert.description,
            "status": alert.status,
            "created_at": alert.created_at,
            "updated_at": alert.updated_at
        },

        "wallet_activity": {
            "deposits": deposits,
            "withdrawals": float(total_withdrawals or 0),
            "pending": float(pending_amount or 0)
        },

        "kyc_documents": kyc_documents,

        "withdrawal_history": withdrawal_history,

        "action_history": action_history
    }



# ---------------------------------------------------------
# 9. MARK ALERT AS SAFE
# POST /admin/fraud/alerts/{alert_id}/mark-safe
# ---------------------------------------------------------


@router.post("/alerts/{alert_id}/mark-safe")
def mark_fraud_alert_safe(
    alert_id: int,
    data: AdminActionRequest,
    db: Session = Depends(get_db)
):
    validate_admin(db, data.admin_id)

    alert = get_alert_or_404(db, alert_id)

    return apply_fraud_decision(
        db=db,
        alert=alert,
        admin_id=data.admin_id,
        new_status="safe",
        action="mark_safe",
        remarks=data.remarks
    )
# ---------------------------------------------------------
# 10. MARK ALERT AS INVESTIGATING
# POST /admin/fraud/alerts/{alert_id}/investigate
# ---------------------------------------------------------


@router.post("/alerts/{alert_id}/investigate")
def investigate_fraud_alert(
    alert_id: int,
    data: AdminActionRequest,
    db: Session = Depends(get_db)
):
    validate_admin(db, data.admin_id)

    alert = get_alert_or_404(db, alert_id)

    return apply_fraud_decision(
        db=db,
        alert=alert,
        admin_id=data.admin_id,
        new_status="investigating",
        action="investigate",
        remarks=data.remarks
    )


# ---------------------------------------------------------
# 11. SUSPEND USER
# POST /admin/fraud/alerts/{alert_id}/suspend
# ---------------------------------------------------------

@router.post("/alerts/{alert_id}/suspend")
def suspend_fraud_account(
    alert_id: int,
    data: SuspendRequest,
    db: Session = Depends(get_db)
):
    validate_admin(db, data.admin_id)

    alert = get_alert_or_404(db, alert_id)

    return apply_fraud_decision(
        db=db,
        alert=alert,
        admin_id=data.admin_id,
        new_status="suspended",
        action="suspend",
        remarks=data.remarks,
        suspend_until=data.suspend_until
    )

# ---------------------------------------------------------
# 12. BAN USER
# POST /admin/fraud/alerts/{alert_id}/ban
# ---------------------------------------------------------

@router.post("/alerts/{alert_id}/ban")
def ban_fraud_account(
    alert_id: int,
    data: AdminActionRequest,
    db: Session = Depends(get_db)
):
    validate_admin(db, data.admin_id)

    alert = get_alert_or_404(db, alert_id)

    return apply_fraud_decision(
        db=db,
        alert=alert,
        admin_id=data.admin_id,
        new_status="banned",
        action="ban",
        remarks=data.remarks
    )


# ---------------------------------------------------------
# 13. ALERT ACTION HISTORY
# GET /admin/fraud/alerts/{alert_id}/action-history
# ---------------------------------------------------------

@router.get("/alerts/{alert_id}/action-history")
def get_alert_action_history(
    alert_id: int,
    db: Session = Depends(get_db)
):

    get_alert_or_404(db, alert_id)

    rows = db.query(
        FraudActionLog,
        User.display_name
    ).join(
        User,
        User.id == FraudActionLog.admin_id
    ).filter(
        FraudActionLog.fraud_alert_id == alert_id
    ).order_by(
        FraudActionLog.created_at.desc()
    ).all()

    return {
        "alert_id": alert_id,
        "data": [
            {
                "action_id": log.id,
                "admin_id": log.admin_id,
                "admin_name": admin_name,
                "action": log.action,
                "remarks": log.remarks,
                "suspend_until": log.suspend_until,
                "previous_status": log.previous_status,
                "new_status": log.new_status,
                "created_at": log.created_at
            }
            for log, admin_name in rows
        ]
    }


# ---------------------------------------------------------
# 14. USER FRAUD HISTORY
# GET /admin/fraud/users/{user_id}/history
# ---------------------------------------------------------

@router.get("/users/{user_id}/history")
def get_user_fraud_history(
    user_id: int,
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    alerts = db.query(FraudAlert).filter(
        FraudAlert.user_id == user_id
    ).order_by(
        FraudAlert.created_at.desc()
    ).all()

    actions = db.query(FraudActionLog).filter(
        FraudActionLog.user_id == user_id
    ).order_by(
        FraudActionLog.created_at.desc()
    ).all()

    return {
        "user_id": user.id,
        "user_name": user.display_name,
        "total_alerts": len(alerts),
        "alerts": [
            {
                "id": alert.id,
                "alert_code": alert.alert_code,
                "risk_type": alert.risk_type,
                "risk_score": alert.risk_score,
                "risk_level": alert.risk_level,
                "status": alert.status,
                "created_at": alert.created_at
            }
            for alert in alerts
        ],
        "actions": [
            {
                "id": action.id,
                "alert_id": action.fraud_alert_id,
                "admin_id": action.admin_id,
                "action": action.action,
                "remarks": action.remarks,
                "previous_status": action.previous_status,
                "new_status": action.new_status,
                "created_at": action.created_at
            }
            for action in actions
        ]
    }


# ---------------------------------------------------------
# 15. USER RISK PROFILE
# GET /admin/fraud/users/{user_id}/risk-profile
# ---------------------------------------------------------

@router.get("/users/{user_id}/risk-profile")
def get_user_risk_profile(
    user_id: int,
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    alerts = db.query(FraudAlert).filter(
        FraudAlert.user_id == user_id
    ).all()

    total_alerts = len(alerts)

    highest_score = max(
        [alert.risk_score for alert in alerts],
        default=0
    )

    high_risk_alerts = sum(
        1 for alert in alerts
        if alert.risk_level == "high"
    )

    medium_risk_alerts = sum(
        1 for alert in alerts
        if alert.risk_level == "medium"
    )

    open_alerts = sum(
        1 for alert in alerts
        if alert.status == "open"
    )

    return {
        "user_id": user.id,
        "user_name": user.display_name,
        "role": user.role,
        "is_active": user.is_active,
        "total_alerts": total_alerts,
        "highest_risk_score": highest_score,
        "high_risk_alerts": high_risk_alerts,
        "medium_risk_alerts": medium_risk_alerts,
        "open_alerts": open_alerts,
        "overall_risk_level": get_risk_level(highest_score)
    }



# ---------------------------------------------------------
# SEARCH USERS FOR FLAG ACCOUNT POPUP
# GET /admin/fraud/users/search
# ---------------------------------------------------------

@router.get("/users/search")
def search_fraud_users(
    search: str = Query(..., min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    rows = db.query(
        User,
        State.state_name
    ).outerjoin(
        State,
        State.id == User.state_id
    ).filter(
        User.role.in_(["customer", "creator"]),
        User.display_name.ilike(f"%{search}%")
    ).order_by(
        User.display_name.asc()
    ).limit(limit).all()

    return {
        "total": len(rows),
        "data": [
            {
                "user_id": user.id,
                "user_name": user.display_name,
                "email": user.email,
                "role": user.role,
                "state_id": user.state_id,
                "state": state_name
            }
            for user, state_name in rows
        ]
    }

# ---------------------------------------------------------
# Action History
# ---------------------------------------------------------



@router.get("/action-history")
def get_fraud_action_history(
    search: str = None,
    action: str = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = (
        db.query(
            FraudActionLog,
            User.display_name,
            FraudAlert.alert_code
        )
        .join(User, User.id == FraudActionLog.user_id)
        .join(
            FraudAlert,
            FraudAlert.id == FraudActionLog.fraud_alert_id
        )
    )

    # Search by user name or alert code
    if search:
        search_value = f"%{search.strip()}%"
        query = query.filter(
            (User.display_name.ilike(search_value)) |
            (FraudAlert.alert_code.ilike(search_value))
        )

    # Filter by action
    if action:
        query = query.filter(
            FraudActionLog.action.ilike(action.strip())
        )

    total = query.count()

    offset = (page - 1) * limit

    results = (
        query
        .order_by(FraudActionLog.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    data = []

    for log, user_name, alert_code in results:
        admin = db.query(User).filter(
            User.id == log.admin_id
        ).first()

        data.append({
            "id": log.id,
            "alert_id": log.fraud_alert_id,
            "alert_code": alert_code,
            "user_id": log.user_id,
            "user_name": user_name,
            "admin_id": log.admin_id,
            "admin_name": admin.display_name if admin else None,
            "action": log.action,
            "remarks": log.remarks,
            "suspend_until": log.suspend_until,
            "created_at": log.created_at
        })

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit,
        "data": data
    }
