from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models.cms_settings import PrivacyPolicy
from schemas.privacy_policy import (
    PrivacyPolicyCreate,
    PrivacyPolicyUpdate,
    PrivacyPolicyResponse
)

router = APIRouter(
    prefix="/privacy-policy",
    tags=["Privacy Policy"]
)


@router.post(
    "/",
    response_model=PrivacyPolicyResponse,
    status_code=status.HTTP_200_OK
)
def create_privacy_policy(
    data: PrivacyPolicyCreate,
    db: Session = Depends(get_db)
):
    privacy = PrivacyPolicy(
        details=data.details
    )

    db.add(privacy)
    db.commit()
    db.refresh(privacy)

    return privacy


@router.get(
    "/",
    response_model=list[PrivacyPolicyResponse],
    status_code=status.HTTP_200_OK
)
def get_privacy_policies(
    db: Session = Depends(get_db)
):
    policies = db.query(
        PrivacyPolicy
    ).all()

    if not policies:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data not found"
        )

    return policies


@router.get(
    "/{privacy_id}",
    response_model=PrivacyPolicyResponse,
    status_code=status.HTTP_200_OK
)
def get_privacy_policy(
    privacy_id: int,
    db: Session = Depends(get_db)
):
    privacy = db.query(
        PrivacyPolicy
    ).filter(
        PrivacyPolicy.id == privacy_id
    ).first()

    if not privacy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data not found"
        )

    return privacy


@router.put(
    "/{privacy_id}",
    response_model=PrivacyPolicyResponse,
    status_code=status.HTTP_200_OK
)
def update_privacy_policy(
    privacy_id: int,
    data: PrivacyPolicyUpdate,
    db: Session = Depends(get_db)
):
    privacy = db.query(
        PrivacyPolicy
    ).filter(
        PrivacyPolicy.id == privacy_id
    ).first()

    if not privacy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data not found"
        )

    if data.details is not None:
        privacy.details = data.details

    if data.status is not None:
        privacy.status = data.status

    db.commit()
    db.refresh(privacy)

    return privacy


@router.delete(
    "/{privacy_id}",
    status_code=status.HTTP_200_OK
)
def delete_privacy_policy(
    privacy_id: int,
    db: Session = Depends(get_db)
):
    privacy = db.query(
        PrivacyPolicy
    ).filter(
        PrivacyPolicy.id == privacy_id
    ).first()

    if not privacy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data not found"
        )

    db.delete(privacy)
    db.commit()

    return {
        "status": "success",
        "message": "Privacy Policy deleted successfully"
    }