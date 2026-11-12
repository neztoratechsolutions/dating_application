from fastapi import (APIRouter,Depends,HTTPException,status)
from sqlalchemy.orm import Session

from database import get_db
from models.cms_settings import CommunityGuideline
from schemas.community_guidelines import (CommunityGuidelineCreate,CommunityGuidelineUpdate,CommunityGuidelineResponse)

router = APIRouter(prefix="/community-guidelines",tags=["Community Guidelines"])


@router.post(
    "/",
    response_model=CommunityGuidelineResponse,
    status_code=status.HTTP_201_CREATED
)
def create_community_guideline(
    data: CommunityGuidelineCreate,
    db: Session = Depends(get_db)
):
    guideline = CommunityGuideline(
        details=data.details,
        status=data.status
    )

    db.add(guideline)
    db.commit()
    db.refresh(guideline)

    return guideline



@router.get(
    "/",
    response_model=list[CommunityGuidelineResponse],
    status_code=status.HTTP_200_OK
)
def get_community_guidelines(
    db: Session = Depends(get_db)
):
    guidelines = db.query(
        CommunityGuideline
    ).all()

    if not guidelines:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No data found"
        )

    return guidelines


@router.get(
    "/{guideline_id}",
    response_model=CommunityGuidelineResponse,
    status_code=status.HTTP_200_OK
)
def get_community_guideline(
    guideline_id: int,
    db: Session = Depends(get_db)
):
    guideline = db.query(
        CommunityGuideline
    ).filter(
        CommunityGuideline.id == guideline_id
    ).first()

    if not guideline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Community guideline not found"
        )

    return guideline



@router.put(
    "/{guideline_id}",
    response_model=CommunityGuidelineResponse,
    status_code=status.HTTP_200_OK
)
def update_community_guideline(
    guideline_id: int,
    data: CommunityGuidelineUpdate,
    db: Session = Depends(get_db)
):
    guideline = db.query(
        CommunityGuideline
    ).filter(
        CommunityGuideline.id == guideline_id
    ).first()

    if not guideline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Community guideline not found"
        )

    update_data = data.model_dump(
        exclude_unset=True
    )

    for key, value in update_data.items():
        setattr(
            guideline,
            key,
            value
        )

    db.commit()
    db.refresh(guideline)

    return guideline



@router.delete(
    "/{guideline_id}",
    status_code=status.HTTP_200_OK
)
def delete_community_guideline(
    guideline_id: int,
    db: Session = Depends(get_db)
):
    guideline = db.query(
        CommunityGuideline
    ).filter(
        CommunityGuideline.id == guideline_id
    ).first()

    if not guideline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Community guideline not found"
        )

    db.delete(guideline)
    db.commit()

    return {
        "status_code": 200,
        "message": "Community guideline deleted successfully"
    }