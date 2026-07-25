from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models.cms_settings import SEOSetting
from schemas.seo_settings import (
    SEOSettingCreate,
    SEOSettingUpdate,
    SEOSettingResponse
)

router = APIRouter( prefix="/seo_settings", tags=["seo_settings"])


@router.post(
    "/",
    response_model=SEOSettingResponse,
    status_code=status.HTTP_201_CREATED
)
def create_seo_setting(
    data: SEOSettingCreate,
    db: Session = Depends(get_db)
):
    seo = SEOSetting(
        meta_title=data.meta_title,
        meta_description=data.meta_description,
        status=data.status
    )

    db.add(seo)
    db.commit()
    db.refresh(seo)

    return seo



@router.get(
    "/{seo_id}",
    response_model=SEOSettingResponse,
    status_code=status.HTTP_200_OK
)
def get_seo_setting_by_id(
    seo_id: int,
    db: Session = Depends(get_db)
):
    seo = db.query(
        SEOSetting
    ).filter(
        SEOSetting.id == seo_id
    ).first()

    if not seo:
        raise HTTPException(
            status_code=404,
            detail="SEO setting not found"
        )

    return seo



@router.get(
    "/",
    response_model=list[SEOSettingResponse],
    status_code=status.HTTP_200_OK
)
def get_seo_settings(
    db: Session = Depends(get_db)
):
    seo_settings = db.query(
        SEOSetting
    ).all()

    if not seo_settings:
        raise HTTPException(
            status_code=404,
            detail="No data found"
        )

    return seo_settings


@router.put(
    "/{seo_id}",
    response_model=SEOSettingResponse
)
def update_seo_setting(
    seo_id: int,
    data: SEOSettingUpdate,
    db: Session = Depends(get_db)
):
    seo = db.query(
        SEOSetting
    ).filter(
        SEOSetting.id == seo_id
    ).first()

    if not seo:
        raise HTTPException(
            status_code=404,
            detail="SEO setting not found"
        )

    update_data = data.model_dump(
        exclude_unset=True
    )

    for key, value in update_data.items():
        setattr(seo, key, value)

    db.commit()
    db.refresh(seo)

    return seo


@router.delete(
    "/{seo_id}",
    status_code=status.HTTP_200_OK
)
def delete_seo_setting(
    seo_id: int,
    db: Session = Depends(get_db)
):
    seo = db.query(
        SEOSetting
    ).filter(
        SEOSetting.id == seo_id
    ).first()

    if not seo:
        raise HTTPException(
            status_code=404,
            detail="SEO setting not found"
        )

    db.delete(seo)
    db.commit()

    return {
        "message": "SEO setting deleted successfully"
    }