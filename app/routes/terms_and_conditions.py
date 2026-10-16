from fastapi import (APIRouter,Depends,HTTPException,status)
from sqlalchemy.orm import Session

from database import get_db
from models.cms_settings import TermsAndCondition
from schemas.terms_and_conditions import (TermsAndConditionCreate,TermsAndConditionUpdate,TermsAndConditionResponse)


router = APIRouter(prefix="/terms-and-conditions",tags=["Terms And Conditions"])


@router.post(
    "/",
    response_model=TermsAndConditionResponse,
    status_code=status.HTTP_201_CREATED
)
def create_terms_and_condition(
    data: TermsAndConditionCreate,
    db: Session = Depends(get_db)
):
    terms = TermsAndCondition(
        details=data.details,
        status=data.status
    )

    db.add(terms)
    db.commit()
    db.refresh(terms)

    return terms



@router.get(
    "/",
    response_model=list[TermsAndConditionResponse],
    status_code=status.HTTP_200_OK
)
def get_terms_and_conditions(
    db: Session = Depends(get_db)
):
    terms = db.query(
        TermsAndCondition
    ).all()

    if not terms:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No data found"
        )

    return terms



@router.get(
    "/{terms_id}",
    response_model=TermsAndConditionResponse,
    status_code=status.HTTP_200_OK
)
def get_terms_and_condition(
    terms_id: int,
    db: Session = Depends(get_db)
):
    terms = db.query(
        TermsAndCondition
    ).filter(
        TermsAndCondition.id == terms_id
    ).first()

    if not terms:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Terms and condition not found"
        )

    return terms




@router.put(
    "/{terms_id}",
    response_model=TermsAndConditionResponse,
    status_code=status.HTTP_200_OK
)
def update_terms_and_condition(
    terms_id: int,
    data: TermsAndConditionUpdate,
    db: Session = Depends(get_db)
):
    terms = db.query(
        TermsAndCondition
    ).filter(
        TermsAndCondition.id == terms_id
    ).first()

    if not terms:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Terms and condition not found"
        )

    update_data = data.model_dump(
        exclude_unset=True
    )

    for key, value in update_data.items():
        setattr(terms, key, value)

    db.commit()
    db.refresh(terms)

    return terms



@router.delete(
    "/{terms_id}",
    status_code=status.HTTP_200_OK
)
def delete_terms_and_condition(
    terms_id: int,
    db: Session = Depends(get_db)
):
    terms = db.query(
        TermsAndCondition
    ).filter(
        TermsAndCondition.id == terms_id
    ).first()

    if not terms:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Terms and condition not found"
        )

    db.delete(terms)
    db.commit()

    return {
        "status": "success",
        "message": "Terms and condition deleted successfully"
    }

