from fastapi import ( APIRouter, Depends, HTTPException, status)
from sqlalchemy.orm import Session

from database import get_db
from models.cms_models import SafetyPolicy
from schemas.safety_policy import ( SafetyPolicyCreate, SafetyPolicyUpdate, SafetyPolicyResponse)

router = APIRouter( prefix="/safety-policies", tags=["Safety Policies"])


@router.post(
    "/",
    response_model=SafetyPolicyResponse,
    status_code=status.HTTP_201_CREATED
)
def create_safety_policy(
    data: SafetyPolicyCreate,
    db: Session = Depends(get_db)
):
    safety_policy = SafetyPolicy(
        details=data.details,
        status=data.status
    )

    db.add(safety_policy)
    db.commit()
    db.refresh(safety_policy)

    return safety_policy


@router.get(
    "/",
    response_model=list[SafetyPolicyResponse],
    status_code=status.HTTP_200_OK
)
def get_safety_policies(
    db: Session = Depends(get_db)
):
    policies = db.query(
        SafetyPolicy
    ).all()

    if not policies:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No data found"
        )

    return policies


@router.get(
    "/{policy_id}",
    response_model=SafetyPolicyResponse,
    status_code=status.HTTP_200_OK
)
def get_safety_policy(
    policy_id: int,
    db: Session = Depends(get_db)
):
    policy = db.query(
        SafetyPolicy
    ).filter(
        SafetyPolicy.id == policy_id
    ).first()

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Safety policy not found"
        )

    return policy



@router.put(
    "/{policy_id}",
    response_model=SafetyPolicyResponse,
    status_code=status.HTTP_200_OK
)
def update_safety_policy(
    policy_id: int,
    data: SafetyPolicyUpdate,
    db: Session = Depends(get_db)
):
    policy = db.query(
        SafetyPolicy
    ).filter(
        SafetyPolicy.id == policy_id
    ).first()

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Safety policy not found"
        )

    update_data = data.model_dump(
        exclude_unset=True
    )

    for key, value in update_data.items():
        setattr(policy, key, value)

    db.commit()
    db.refresh(policy)

    return policy



@router.delete(
    "/{policy_id}",
    status_code=status.HTTP_200_OK
)
def delete_safety_policy(
    policy_id: int,
    db: Session = Depends(get_db)
):
    policy = db.query(
        SafetyPolicy
    ).filter(
        SafetyPolicy.id == policy_id
    ).first()

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Safety policy not found"
        )

    db.delete(policy)
    db.commit()

    return {
        "status_code": 200,
        "message": "Safety policy deleted successfully"
    }