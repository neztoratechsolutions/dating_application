from fastapi import (APIRouter,Depends,HTTPException,status)
from sqlalchemy.orm import Session

from database import get_db
from models.cms_settings import RefundPolicy
from schemas.refund_policy import (RefundPolicyCreate,RefundPolicyUpdate,RefundPolicyResponse)

router = APIRouter(prefix="/refund-policies",tags=["Refund Policies"])

@router.post(
    "/",
    response_model=RefundPolicyResponse,
    status_code=status.HTTP_201_CREATED
)
def create_refund_policy(
    data: RefundPolicyCreate,
    db: Session = Depends(get_db)
):
    refund_policy = RefundPolicy(
        details=data.details,
        status=data.status
    )

    db.add(refund_policy)
    db.commit()
    db.refresh(refund_policy)

    return refund_policy



@router.get(
    "/",
    response_model=list[RefundPolicyResponse],
    status_code=status.HTTP_200_OK
)
def get_refund_policies(
    db: Session = Depends(get_db)
):
    refund_policies = db.query(
        RefundPolicy
    ).all()

    if not refund_policies:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No data found"
        )

    return refund_policies


@router.get(
    "/{refund_policy_id}",
    response_model=RefundPolicyResponse,
    status_code=status.HTTP_200_OK
)
def get_refund_policy(
    refund_policy_id: int,
    db: Session = Depends(get_db)
):
    refund_policy = db.query(
        RefundPolicy
    ).filter(
        RefundPolicy.id == refund_policy_id
    ).first()

    if not refund_policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund policy not found"
        )

    return refund_policy


@router.put(
    "/{refund_policy_id}",
    response_model=RefundPolicyResponse,
    status_code=status.HTTP_200_OK
)
def update_refund_policy(
    refund_policy_id: int,
    data: RefundPolicyUpdate,
    db: Session = Depends(get_db)
):
    refund_policy = db.query(
        RefundPolicy
    ).filter(
        RefundPolicy.id == refund_policy_id
    ).first()

    if not refund_policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund policy not found"
        )

    update_data = data.model_dump(
        exclude_unset=True
    )

    for key, value in update_data.items():
        setattr(
            refund_policy,
            key,
            value
        )

    db.commit()
    db.refresh(refund_policy)

    return refund_policy



@router.delete(
    "/{refund_policy_id}",
    status_code=status.HTTP_200_OK
)
def delete_refund_policy(
    refund_policy_id: int,
    db: Session = Depends(get_db)
):
    refund_policy = db.query(
        RefundPolicy
    ).filter(
        RefundPolicy.id == refund_policy_id
    ).first()

    if not refund_policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund policy not found"
        )

    db.delete(refund_policy)
    db.commit()

    return {
        "status_code": 200,
        "message": "Refund policy deleted successfully"
    }