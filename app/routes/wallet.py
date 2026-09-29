from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status
)

from sqlalchemy.orm import Session

from database import get_db

from models.wallet import Wallet
from models.wallet_transaction import WalletTransaction
from models.users import User

from schemas.wallet import (
    WalletCreate,
    WalletResponse,
    WalletTransactionResponse
)


router = APIRouter(
    prefix="/wallets",
    tags=["Wallet"]
)


# ==========================================================
# INDIAN TIMEZONE
# ==========================================================

INDIAN_TIMEZONE = timezone(
    timedelta(hours=5, minutes=30)
)


# ==========================================================
# CONVERT TO INDIAN TIME
# ==========================================================

def indian_datetime(dt):

    if dt is None:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(
            tzinfo=timezone.utc
        )

    return dt.astimezone(
        INDIAN_TIMEZONE
    )


# ==========================================================
# GENERATE WALLET ID
# ==========================================================

def generate_wallet_id(
    db: Session,
    user_role: str
):

    if user_role == "customer":

        prefix = "WLT-C"

    elif user_role == "creator":

        prefix = "WLT-R"

    else:

        prefix = "WLT-U"

    # ------------------------------------------------------
    # Find last wallet with same prefix
    # ------------------------------------------------------

    last_wallet = (
        db.query(Wallet)
        .filter(
            Wallet.wallet_id.like(
                f"{prefix}%"
            )
        )
        .order_by(
            Wallet.id.desc()
        )
        .first()
    )

    if not last_wallet:

        next_number = 10000

    else:

        try:

            last_number = int(
                last_wallet.wallet_id.replace(
                    prefix,
                    ""
                )
            )

            next_number = last_number + 1

        except ValueError:

            next_number = 10000

    return f"{prefix}{next_number}"


# ==========================================================
# CREATE WALLET
# ==========================================================

@router.post(
    "/",
    response_model=WalletResponse,
    status_code=status.HTTP_201_CREATED
)
def create_wallet(
    data: WalletCreate,
    db: Session = Depends(get_db)
):

    # ------------------------------------------------------
    # CHECK USER
    # ------------------------------------------------------

    user = (
        db.query(User)
        .filter(
            User.id == data.user_id
        )
        .first()
    )

    if not user:

        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # ------------------------------------------------------
    # ONLY CUSTOMER / CREATOR
    # ------------------------------------------------------

    if user.role not in [
        "customer",
        "creator"
    ]:

        raise HTTPException(
            status_code=400,
            detail="Wallet can be created only for customer or creator"
        )

    # ------------------------------------------------------
    # CHECK EXISTING WALLET
    # ------------------------------------------------------

    existing_wallet = (
        db.query(Wallet)
        .filter(
            Wallet.user_id == data.user_id
        )
        .first()
    )

    if existing_wallet:

        raise HTTPException(
            status_code=400,
            detail="Wallet already exists for this user"
        )

    # ------------------------------------------------------
    # GENERATE WALLET ID
    # ------------------------------------------------------

    wallet_id = generate_wallet_id(
        db,
        user.role
    )

    # ------------------------------------------------------
    # CREATE WALLET
    # ------------------------------------------------------

    wallet = Wallet(
        user_id=data.user_id,
        wallet_id=wallet_id,
        balance=0.00,
        coins=0,
        deposits=0.00,
        spending=0.00,
        last_transaction=None,
        status="active"
    )

    db.add(wallet)

    db.commit()

    db.refresh(wallet)

    # ------------------------------------------------------
    # RESPONSE
    # ------------------------------------------------------

    return WalletResponse(
        id=wallet.id,
        user_id=wallet.user_id,
        user_name=user.display_name,
        phone=user.phone,
        wallet_id=wallet.wallet_id,
        balance=wallet.balance,
        coins=wallet.coins,
        deposits=wallet.deposits,
        spending=wallet.spending,
        last_transaction=wallet.last_transaction,
        status=wallet.status,
        created_at=wallet.created_at,
        updated_at=wallet.updated_at
    )


# ==========================================================
# GET ALL WALLETS
# ==========================================================

@router.get(
    "/",
    response_model=list[WalletResponse]
)
def get_all_wallets(

    user_type: Optional[str] = Query(
        default=None,
        description="customer or creator"
    ),

    user_id: Optional[int] = None,

    status_filter: str = Query(
        default="all",
        description="all, active, frozen, hold"
    ),

    db: Session = Depends(get_db)
):

    # ------------------------------------------------------
    # BASE QUERY
    # ------------------------------------------------------

    query = (
        db.query(
            Wallet,
            User.display_name.label("user_name"),
            User.phone.label("phone")
        )
        .join(
            User,
            Wallet.user_id == User.id
        )
    )

    # ------------------------------------------------------
    # USER ID
    # ------------------------------------------------------

    if user_id is not None:

        query = query.filter(
            Wallet.user_id == user_id
        )

    # ------------------------------------------------------
    # USER TYPE
    # ------------------------------------------------------

    if user_type:

        user_type = user_type.lower()

        if user_type not in [
            "customer",
            "creator"
        ]:

            raise HTTPException(
                status_code=400,
                detail="user_type must be customer or creator"
            )

        query = query.filter(
            User.role == user_type
        )

    # ------------------------------------------------------
    # STATUS
    # ------------------------------------------------------

    status_filter = status_filter.lower()

    valid_statuses = [
        "all",
        "active",
        "frozen",
        "hold"
    ]

    if status_filter not in valid_statuses:

        raise HTTPException(
            status_code=400,
            detail="status_filter must be all, active, frozen or hold"
        )

    if status_filter != "all":

        query = query.filter(
            Wallet.status == status_filter
        )

    # ------------------------------------------------------
    # GET DATA
    # ------------------------------------------------------

    wallets = (
        query
        .order_by(
            Wallet.id.desc()
        )
        .all()
    )

    if not wallets:

        raise HTTPException(
            status_code=404,
            detail="No wallet data found"
        )

    # ------------------------------------------------------
    # RESPONSE
    # ------------------------------------------------------

    result = []

    for wallet, user_name, phone in wallets:

        result.append(
            WalletResponse(
                id=wallet.id,
                user_id=wallet.user_id,
                user_name=user_name,
                phone=phone,
                wallet_id=wallet.wallet_id,
                balance=wallet.balance,
                coins=wallet.coins,
                deposits=wallet.deposits,
                spending=wallet.spending,
                last_transaction=wallet.last_transaction,
                status=wallet.status,
                created_at=wallet.created_at,
                updated_at=wallet.updated_at
            )
        )

    return result


# ==========================================================
# GET WALLET BY USER ID
# ==========================================================

@router.get(
    "/user/{user_id}",
    response_model=WalletResponse
)
def get_user_wallet(
    user_id: int,
    db: Session = Depends(get_db)
):

    result = (
        db.query(
            Wallet,
            User.display_name.label("user_name"),
            User.phone.label("phone")
        )
        .join(
            User,
            Wallet.user_id == User.id
        )
        .filter(
            Wallet.user_id == user_id
        )
        .first()
    )

    if not result:

        raise HTTPException(
            status_code=404,
            detail="Wallet not found"
        )

    wallet, user_name, phone = result

    return WalletResponse(
        id=wallet.id,
        user_id=wallet.user_id,
        user_name=user_name,
        phone=phone,
        wallet_id=wallet.wallet_id,
        balance=wallet.balance,
        coins=wallet.coins,
        deposits=wallet.deposits,
        spending=wallet.spending,
        last_transaction=wallet.last_transaction,
        status=wallet.status,
        created_at=wallet.created_at,
        updated_at=wallet.updated_at
    )


# ==========================================================
# GET TRANSACTION HISTORY
# ==========================================================

@router.get(
    "/transactions",
    response_model=list[WalletTransactionResponse]
)
def get_wallet_transactions(

    status_filter: str = Query(
        default="all",
        description="all, success, refund, failed, pending"
    ),

    transaction_type: Optional[str] = Query(
        default=None,
        description="deposit, spend, gift, refund, chat"
    ),

    user_type: Optional[str] = Query(
        default=None,
        description="customer or creator"
    ),

    user_id: Optional[int] = None,

    start_date: Optional[str] = Query(
        default=None,
        description="DD-MM-YYYY"
    ),

    end_date: Optional[str] = Query(
        default=None,
        description="DD-MM-YYYY"
    ),

    db: Session = Depends(get_db)
):

    # ------------------------------------------------------
    # BASE QUERY
    # ------------------------------------------------------

    query = (
        db.query(
            WalletTransaction,
            User.display_name.label("user_name")
        )
        .join(
            User,
            WalletTransaction.user_id == User.id
        )
    )

    # ------------------------------------------------------
    # USER ID
    # ------------------------------------------------------

    if user_id is not None:

        query = query.filter(
            WalletTransaction.user_id == user_id
        )

    # ------------------------------------------------------
    # USER TYPE
    # ------------------------------------------------------

    if user_type:

        user_type = user_type.lower()

        if user_type not in [
            "customer",
            "creator"
        ]:

            raise HTTPException(
                status_code=400,
                detail="user_type must be customer or creator"
            )

        query = query.filter(
            User.role == user_type
        )

    # ------------------------------------------------------
    # STATUS
    # ------------------------------------------------------

    valid_statuses = [
        "all",
        "success",
        "refund",
        "failed",
        "pending"
    ]

    status_filter = status_filter.lower()

    if status_filter not in valid_statuses:

        raise HTTPException(
            status_code=400,
            detail=(
                "status_filter must be "
                "all, success, refund, failed or pending"
            )
        )

    if status_filter != "all":

        query = query.filter(
            WalletTransaction.status == status_filter
        )

    # ------------------------------------------------------
    # TRANSACTION TYPE
    # ------------------------------------------------------

    valid_types = [
        "deposit",
        "spend",
        "gift",
        "refund",
        "chat"
    ]

    if transaction_type:

        transaction_type = transaction_type.lower()

        if transaction_type not in valid_types:

            raise HTTPException(
                status_code=400,
                detail=(
                    "transaction_type must be "
                    "deposit, spend, gift, refund or chat"
                )
            )

        query = query.filter(
            WalletTransaction.type == transaction_type
        )

    # ------------------------------------------------------
    # START DATE
    # ------------------------------------------------------

    if start_date:

        try:

            start = datetime.strptime(
                start_date,
                "%d-%m-%Y"
            )

        except ValueError:

            raise HTTPException(
                status_code=400,
                detail="start_date must be in DD-MM-YYYY format"
            )

        start = start.replace(
            tzinfo=INDIAN_TIMEZONE
        )

        start_utc = start.astimezone(
            timezone.utc
        )

        query = query.filter(
            WalletTransaction.created_at >= start_utc
        )

    # ------------------------------------------------------
    # END DATE
    # ------------------------------------------------------

    if end_date:

        try:

            end = datetime.strptime(
                end_date,
                "%d-%m-%Y"
            )

        except ValueError:

            raise HTTPException(
                status_code=400,
                detail="end_date must be in DD-MM-YYYY format"
            )

        end = end + timedelta(
            days=1
        )

        end = end.replace(
            tzinfo=INDIAN_TIMEZONE
        )

        end_utc = end.astimezone(
            timezone.utc
        )

        query = query.filter(
            WalletTransaction.created_at < end_utc
        )

    # ------------------------------------------------------
    # GET TRANSACTIONS
    # ------------------------------------------------------

    transactions = (
        query
        .order_by(
            WalletTransaction.id.desc()
        )
        .all()
    )

    if not transactions:

        raise HTTPException(
            status_code=404,
            detail="No transaction data found"
        )

    # ------------------------------------------------------
    # RESPONSE
    # ------------------------------------------------------

    result = []

    for transaction, user_name in transactions:

        indian_time = indian_datetime(
            transaction.created_at
        )

        result.append(
            WalletTransactionResponse(
                id=transaction.id,
                transaction_id=transaction.transaction_id,
                user_id=transaction.user_id,
                user_name=user_name,
                wallet_id=transaction.wallet_id,
                type=transaction.type,
                amount=transaction.amount,
                coins=transaction.coins,
                method=transaction.method,
                status=transaction.status,
                created_at=transaction.created_at,
                updated_at=transaction.updated_at,
                indian_date=(
                    indian_time.strftime("%d-%m-%Y")
                    if indian_time
                    else None
                ),
                indian_time=(
                    indian_time.strftime("%I:%M:%S %p")
                    if indian_time
                    else None
                )
            )
        )

    return result