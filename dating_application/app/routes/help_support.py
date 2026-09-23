from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.help_support import HelpSupport
from app.schemas.help_support import (
    HelpSupportCreate,
    HelpSupportUpdate,
    HelpSupportResponse
)

router = APIRouter(
    prefix = "/help-support",
    tags= ["Help & Support"]
)

def get_db():
    db = SessionLocal()

    try :
        yield db
    finally:
        db.close()

# -------------------------------------------------
# ADMIN - CREATE QUESTION & ANSWER
# -------------------------------------------------

@router.post(
    "/",
    response_model=HelpSupportResponse
)
def create_help_support(
    data : HelpSupportCreate,
    db : Session = Depends(get_db)
):
    help_support = HelpSupport(
        question=data.question,
        answer=data.answer,
        is_active=data.is_active
    )

    db.add(help_support)
    db.commit()
    db.refresh(help_support)

    return help_support


# -------------------------------------------------
# CREATOR - GET ALL ACTIVE QUESTIONS
# -------------------------------------------------

@router.get(
    "/",
    response_model=list[HelpSupportResponse]
)
def get_help_support(
    db: Session = Depends(get_db)
):
    return(
        db.query(HelpSupport).filter(
            HelpSupport.is_active ==True
        ).order_by(HelpSupport.id.asc())
    ).all()

# -------------------------------------------------
# ADMIN - GET ONE QUESTION
# -------------------------------------------------

@router.get(
    "/{help_support_id}",
    response_model=HelpSupportResponse
)
def get_help_support_by_id(
    help_support_id : int,
    db: Session = Depends(get_db)
):
    help_support = db .query(HelpSupport).filter(
        HelpSupport.id == help_support_id
    ).first()

    if not help_support:
        raise HTTPException(
            status_code=404,
            detail="Help & Support entry not found"
        )

    return help_support

# -------------------------------------------------
# ADMIN - UPDATE QUESTION / ANSWER
# -------------------------------------------------

@router.put(
    "/{help_support_id}",
    response_model=HelpSupportResponse
)
def update_help_support(
    help_support_id: int,
    data: HelpSupportUpdate,
    db: Session = Depends(get_db)
):
    help_support = db.query(HelpSupport).filter(
        HelpSupport.id == help_support_id
    ).first()

    if not help_support:
            raise HTTPException(
                status_code=404,
                detail="Help & Support entry not found"
            )

    if data.question is not None:
        help_support.question = data.question

    if data.answer is not None :
        help_support.answer = data.answer

    if data.is_active is not None :
        help_support.is_active = data.is_active

    db.commit()
    db.refresh(help_support)

    return help_support


# -------------------------------------------------
# ADMIN - DELETE
# -------------------------------------------------

@router.delete("/{help_support_id}")
def delete_help_support(
    help_support_id: int,
    db: Session = Depends(get_db)
):
    help_support = (
        db.query(HelpSupport)
        .filter(HelpSupport.id == help_support_id)
        .first()
    )

    if not help_support:
        raise HTTPException(
            status_code=404,
            detail="Help & Support entry not found"
        )

    db.delete(help_support)
    db.commit()

    return {
        "message": "Help & Support entry deleted successfully"
    }
