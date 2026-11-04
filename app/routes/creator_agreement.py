from fastapi import (APIRouter,Depends,HTTPException,status)
from sqlalchemy.orm import Session

from database import get_db
from models.cms_models import CreatorAgreement
from schemas.creator_agreement import (CreatorAgreementCreate,CreatorAgreementUpdate,CreatorAgreementResponse)

router = APIRouter(prefix="/creator-agreements",tags=["Creator Agreements"])


@router.post(
    "/",
    response_model=CreatorAgreementResponse,
    status_code=status.HTTP_201_CREATED
)
def create_creator_agreement(
    data: CreatorAgreementCreate,
    db: Session = Depends(get_db)
):
    agreement = CreatorAgreement(
        details=data.details,
        status=data.status
    )

    db.add(agreement)
    db.commit()
    db.refresh(agreement)

    return agreement


@router.get(
    "/",
    response_model=list[CreatorAgreementResponse],
    status_code=status.HTTP_200_OK
)
def get_creator_agreements(
    db: Session = Depends(get_db)
):
    agreements = db.query(
        CreatorAgreement
    ).all()

    if not agreements:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No data found"
        )

    return agreements


@router.get(
    "/{agreement_id}",
    response_model=CreatorAgreementResponse,
    status_code=status.HTTP_200_OK
)
def get_creator_agreement(
    agreement_id: int,
    db: Session = Depends(get_db)
):
    agreement = db.query(
        CreatorAgreement
    ).filter(
        CreatorAgreement.id == agreement_id
    ).first()

    if not agreement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Creator agreement not found"
        )

    return agreement


@router.put(
    "/{agreement_id}",
    response_model=CreatorAgreementResponse,
    status_code=status.HTTP_200_OK
)
def update_creator_agreement(
    agreement_id: int,
    data: CreatorAgreementUpdate,
    db: Session = Depends(get_db)
):
    agreement = db.query(
        CreatorAgreement
    ).filter(
        CreatorAgreement.id == agreement_id
    ).first()

    if not agreement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Creator agreement not found"
        )

    update_data = data.model_dump(
        exclude_unset=True
    )

    for key, value in update_data.items():
        setattr(
            agreement,
            key,
            value
        )

    db.commit()
    db.refresh(agreement)

    return agreement



@router.delete(
    "/{agreement_id}",
    status_code=status.HTTP_200_OK
)
def delete_creator_agreement(
    agreement_id: int,
    db: Session = Depends(get_db)
):
    agreement = db.query(
        CreatorAgreement
    ).filter(
        CreatorAgreement.id == agreement_id
    ).first()

    if not agreement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Creator agreement not found"
        )

    db.delete(agreement)
    db.commit()

    return {
        "status_code": 200,
        "message": "Creator agreement deleted successfully"
    }