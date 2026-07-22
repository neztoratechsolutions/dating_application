from fastapi import (APIRouter,Depends,HTTPException,status)
from sqlalchemy.orm import Session

from database import get_db
from models.ad_setting import AdSetting
from schemas.ad_settings import (AdSettingCreate,AdSettingUpdate,AdSettingResponse)

router = APIRouter(prefix="/ad-settings",tags=["Ad Settings"])


# -------------------------------- CREATE --------------------------------


@router.post(
    "/",
    response_model=AdSettingResponse,
    status_code=status.HTTP_201_CREATED
)
def create_ad_setting(
    data: AdSettingCreate,
    db: Session = Depends(get_db)
):
    ad_setting = AdSetting(
        title=data.title,
        description=data.description,
        placement=data.placement,
        status=data.status
    )

    db.add(ad_setting)
    db.commit()
    db.refresh(ad_setting)

    return ad_setting


# -------------------------------- GET ALL --------------------------------


@router.get(
    "/",
    response_model=list[AdSettingResponse],
    status_code=status.HTTP_200_OK
)
def get_ad_settings(
    db: Session = Depends(get_db)
):
    ad_settings = db.query(
        AdSetting
    ).all()

    if not ad_settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No data found"
        )

    return ad_settings


# -------------------------------- GET BY ID --------------------------------


@router.get(
    "/{ad_setting_id}",
    response_model=AdSettingResponse,
    status_code=status.HTTP_200_OK
)
def get_ad_setting(
    ad_setting_id: int,
    db: Session = Depends(get_db)
):
    ad_setting = db.query(
        AdSetting
    ).filter(
        AdSetting.id == ad_setting_id
    ).first()

    if not ad_setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ad setting not found"
        )

    return ad_setting


# -------------------------------- UPDATE --------------------------------


@router.put(
    "/{ad_setting_id}",
    response_model=AdSettingResponse,
    status_code=status.HTTP_200_OK
)
def update_ad_setting(
    ad_setting_id: int,
    data: AdSettingUpdate,
    db: Session = Depends(get_db)
):
    ad_setting = db.query(
        AdSetting
    ).filter(
        AdSetting.id == ad_setting_id
    ).first()

    if not ad_setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ad setting not found"
        )

    update_data = data.model_dump(
        exclude_unset=True
    )

    for key, value in update_data.items():
        setattr(
            ad_setting,
            key,
            value
        )

    db.commit()
    db.refresh(ad_setting)

    return ad_setting


# -------------------------------- DELETE --------------------------------


@router.delete(
    "/{ad_setting_id}",
    status_code=status.HTTP_200_OK
)
def delete_ad_setting(
    ad_setting_id: int,
    db: Session = Depends(get_db)
):
    ad_setting = db.query(
        AdSetting
    ).filter(
        AdSetting.id == ad_setting_id
    ).first()

    if not ad_setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ad setting not found"
        )

    db.delete(ad_setting)
    db.commit()

    return {
        "status": "success",
        "message": "Ad setting deleted successfully"
    }