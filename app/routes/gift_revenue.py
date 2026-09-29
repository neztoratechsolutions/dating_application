from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.gift_revenue import GiftRevenue


router = APIRouter(
    prefix="/gift-revenue",
    tags=["Gift Revenue"]
)


# =========================================================
# SCHEMAS
# =========================================================

class GiftRevenueCreate(BaseModel):
    creator_revenue: Decimal = Field(..., ge=0)
    platform_revenue: Decimal = Field(..., ge=0)


class GiftRevenueUpdate(BaseModel):
    creator_revenue: Decimal | None = Field(None, ge=0)
    platform_revenue: Decimal | None = Field(None, ge=0)


# =========================================================
# CREATE GIFT REVENUE
# =========================================================

@router.post("")
def create_gift_revenue(
    request: GiftRevenueCreate,
    db: Session = Depends(get_db)
):
    total = (
        request.creator_revenue
        + request.platform_revenue
    )

    if total != Decimal("100.00"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Creator revenue and platform revenue must total 100"
        )

    existing = db.query(GiftRevenue).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gift revenue configuration already exists"
        )

    revenue = GiftRevenue(
        creator_revenue=request.creator_revenue,
        platform_revenue=request.platform_revenue
    )

    db.add(revenue)
    db.commit()
    db.refresh(revenue)

    return {
        "status_code": 201,
        "message": "Gift revenue created successfully",
        "data": {
            "id": revenue.id,
            "creator_revenue": float(revenue.creator_revenue),
            "platform_revenue": float(revenue.platform_revenue),
            "created_at": revenue.created_at,
            "updated_at": revenue.updated_at
        }
    }


# =========================================================
# GET ALL GIFT REVENUE
# =========================================================

@router.get("")
def get_all_gift_revenue(
    db: Session = Depends(get_db)
):
    revenues = (
        db.query(GiftRevenue)
        .order_by(GiftRevenue.id.desc())
        .all()
    )

    if not revenues:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gift revenue data not found"
        )

    return {
        "status_code": 200,
        "message": "Gift revenue fetched successfully",
        "data": [
            {
                "id": revenue.id,
                "creator_revenue": float(
                    revenue.creator_revenue
                ),
                "platform_revenue": float(
                    revenue.platform_revenue
                ),
                "created_at": revenue.created_at,
                "updated_at": revenue.updated_at
            }
            for revenue in revenues
        ]
    }


# =========================================================
# GET GIFT REVENUE BY ID
# =========================================================

@router.get("/{revenue_id}")
def get_gift_revenue(
    revenue_id: int,
    db: Session = Depends(get_db)
):
    revenue = (
        db.query(GiftRevenue)
        .filter(GiftRevenue.id == revenue_id)
        .first()
    )

    if not revenue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gift revenue data not found"
        )

    return {
        "status_code": 200,
        "message": "Gift revenue fetched successfully",
        "data": {
            "id": revenue.id,
            "creator_revenue": float(
                revenue.creator_revenue
            ),
            "platform_revenue": float(
                revenue.platform_revenue
            ),
            "created_at": revenue.created_at,
            "updated_at": revenue.updated_at
        }
    }


# =========================================================
# UPDATE GIFT REVENUE
# =========================================================

@router.put("/{revenue_id}")
def update_gift_revenue(
    revenue_id: int,
    request: GiftRevenueUpdate,
    db: Session = Depends(get_db)
):
    revenue = (
        db.query(GiftRevenue)
        .filter(GiftRevenue.id == revenue_id)
        .first()
    )

    if not revenue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gift revenue data not found"
        )

    # -----------------------------------------------------
    # CHECK AT LEAST ONE FIELD IS PROVIDED
    # -----------------------------------------------------

    if (
        request.creator_revenue is None
        and request.platform_revenue is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field is required to update"
        )

    # -----------------------------------------------------
    # KEEP EXISTING VALUE IF FIELD IS NOT PROVIDED
    # -----------------------------------------------------

    creator_revenue = (
        request.creator_revenue
        if request.creator_revenue is not None
        else Decimal(str(revenue.creator_revenue))
    )

    platform_revenue = (
        request.platform_revenue
        if request.platform_revenue is not None
        else Decimal(str(revenue.platform_revenue))
    )

    # -----------------------------------------------------
    # TOTAL MUST BE 100
    # -----------------------------------------------------

    total = creator_revenue + platform_revenue

    if total != Decimal("100.00"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Creator revenue and platform revenue must total 100"
        )

    # -----------------------------------------------------
    # UPDATE
    # -----------------------------------------------------

    revenue.creator_revenue = creator_revenue
    revenue.platform_revenue = platform_revenue

    db.commit()
    db.refresh(revenue)

    return {
        "status_code": 200,
        "message": "Gift revenue updated successfully",
        "data": {
            "id": revenue.id,
            "creator_revenue": float(
                revenue.creator_revenue
            ),
            "platform_revenue": float(
                revenue.platform_revenue
            ),
            "created_at": revenue.created_at,
            "updated_at": revenue.updated_at
        }
    }


# =========================================================
# DELETE GIFT REVENUE
# =========================================================

@router.delete("/{revenue_id}")
def delete_gift_revenue(
    revenue_id: int,
    db: Session = Depends(get_db)
):
    revenue = (
        db.query(GiftRevenue)
        .filter(GiftRevenue.id == revenue_id)
        .first()
    )

    if not revenue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gift revenue data not found"
        )

    db.delete(revenue)
    db.commit()

    return {
        "status_code": 200,
        "message": "Gift revenue deleted successfully"
    }