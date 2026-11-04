from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ==========================================================
# CREATE WALLET
# ==========================================================

class WalletCreate(BaseModel):
    user_id: int


# ==========================================================
# WALLET RESPONSE
# ==========================================================

class WalletResponse(BaseModel):

    id: int

    user_id: int

    user_name: Optional[str] = None

    phone: Optional[str] = None

    wallet_id: str

    balance: Decimal

    coins: int

    deposits: Decimal

    spending: Decimal

    last_transaction: Optional[datetime] = None

    status: str

    created_at: Optional[datetime] = None

    updated_at: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True
    )


# ==========================================================
# WALLET TRANSACTION RESPONSE
# ==========================================================

class WalletTransactionResponse(BaseModel):

    id: int

    transaction_id: str

    user_id: int

    user_name: Optional[str] = None

    wallet_id: int

    type: str

    amount: Decimal

    coins: int

    method: str

    status: str

    created_at: Optional[datetime] = None

    updated_at: Optional[datetime] = None

    indian_date: Optional[str] = None

    indian_time: Optional[str] = None

    model_config = ConfigDict(
        from_attributes=True
    )