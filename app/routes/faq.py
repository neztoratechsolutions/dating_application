from fastapi import (APIRouter,Depends,HTTPException,status)
from sqlalchemy.orm import Session

from database import get_db
from models.cms_models import FAQ
from models.users import User

from schemas.faq import ( FAQCreate,FAQUpdate,FAQResponse)

router = APIRouter(prefix="/faqs",tags=["FAQs"])



@router.post(
    "/",
    response_model=FAQResponse,
    status_code=status.HTTP_201_CREATED
)
def create_faq(
    data: FAQCreate,
    db: Session = Depends(get_db)
):
    if data.created_by is not None:

        user = db.query(User).filter(
            User.id == data.created_by
        ).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

    faq = FAQ(
        question=data.question,
        answer=data.answer,
        created_by=data.created_by,
        status=data.status
    )

    db.add(faq)
    db.commit()
    db.refresh(faq)

    return faq



@router.get(
    "/",
    response_model=list[FAQResponse],
    status_code=status.HTTP_200_OK
)
def get_faqs(
    db: Session = Depends(get_db)
):
    faqs = db.query(
        FAQ
    ).all()

    if not faqs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No data found"
        )

    return faqs


@router.get(
    "/{faq_id}",
    response_model=FAQResponse,
    status_code=status.HTTP_200_OK
)
def get_faq(
    faq_id: int,
    db: Session = Depends(get_db)
):
    faq = db.query(
        FAQ
    ).filter(
        FAQ.id == faq_id
    ).first()

    if not faq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="FAQ not found"
        )

    return faq


@router.put(
    "/{faq_id}",
    response_model=FAQResponse,
    status_code=status.HTTP_200_OK
)
def update_faq(
    faq_id: int,
    data: FAQUpdate,
    db: Session = Depends(get_db)
):
    faq = db.query(
        FAQ
    ).filter(
        FAQ.id == faq_id
    ).first()

    if not faq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="FAQ not found"
        )

    if data.created_by is not None:

        user = db.query(User).filter(
            User.id == data.created_by
        ).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

    update_data = data.model_dump(
        exclude_unset=True
    )

    for key, value in update_data.items():
        setattr(
            faq,
            key,
            value
        )

    db.commit()
    db.refresh(faq)

    return faq


@router.delete(
    "/{faq_id}",
    status_code=status.HTTP_200_OK
)
def delete_faq(
    faq_id: int,
    db: Session = Depends(get_db)
):
    faq = db.query(
        FAQ
    ).filter(
        FAQ.id == faq_id
    ).first()

    if not faq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="FAQ not found"
        )

    db.delete(faq)
    db.commit()

    return {
        "status_code": 200,
        "message": "FAQ deleted successfully"
    }