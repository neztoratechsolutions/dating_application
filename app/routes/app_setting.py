import os

from fastapi import (APIRouter,Depends,HTTPException,status,UploadFile,File,Form)
from sqlalchemy.orm import Session

from database import get_db
from models.app_setting import AppSetting
from schemas.app_setting import AppSettingResponse



router = APIRouter(prefix="/app-settings",tags=["App Settings"])

UPLOAD_DIR = "uploads/app_settings"

os.makedirs(UPLOAD_DIR,exist_ok=True)


@router.post(
    "/",
    response_model=AppSettingResponse,
    status_code=status.HTTP_201_CREATED
)
def create_app_setting(
    app_name: str = Form(...),
    support_email: str | None = Form(None),
    support_number: str | None = Form(None),
    logo: UploadFile | None = File(None),
    favicon: UploadFile | None = File(None),
    db: Session = Depends(get_db)
):
    existing = db.query(
        AppSetting
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="App setting already exists"
        )

    logo_path = None
    favicon_path = None

    if logo:

        logo_path = os.path.join(
            UPLOAD_DIR,
            logo.filename
        )

        with open(logo_path, "wb") as buffer:
            buffer.write(
                logo.file.read()
            )

    if favicon:

        favicon_path = os.path.join(
            UPLOAD_DIR,
            favicon.filename
        )

        with open(favicon_path, "wb") as buffer:
            buffer.write(
                favicon.file.read()
            )

    setting = AppSetting(
        app_name=app_name,
        logo=logo_path,
        favicon=favicon_path,
        support_email=support_email,
        support_number=support_number
    )

    db.add(setting)
    db.commit()
    db.refresh(setting)

    return setting



@router.get(
    "/",
    response_model=AppSettingResponse,
    status_code=status.HTTP_200_OK
)
def get_app_setting(
    db: Session = Depends(get_db)
):
    setting = db.query(
        AppSetting
    ).first()

    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App setting not found"
        )

    return setting




@router.put(
    "/{setting_id}",
    response_model=AppSettingResponse,
    status_code=status.HTTP_200_OK
)
def update_app_setting(
    setting_id: int,
    app_name: str | None = Form(None),
    support_email: str | None = Form(None),
    support_number: str | None = Form(None),
    db: Session = Depends(get_db)
):
    setting = db.query(
        AppSetting
    ).filter(
        AppSetting.id == setting_id
    ).first()

    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App setting not found"
        )

    # Update only provided fields

    if app_name not in [None, ""]:
        setting.app_name = app_name

    if support_email not in [None, ""]:
        setting.support_email = support_email

    if support_number not in [None, ""]:
        setting.support_number = support_number

    db.commit()
    db.refresh(setting)

    return setting



@router.get(
    "/{setting_id}",
    response_model=AppSettingResponse,
    status_code=status.HTTP_200_OK
)
def get_app_setting_by_id(
    setting_id: int,
    db: Session = Depends(get_db)
):
    setting = db.query(
        AppSetting
    ).filter(
        AppSetting.id == setting_id
    ).first()

    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App setting not found"
        )

    return setting



@router.delete(
    "/{setting_id}",
    status_code=status.HTTP_200_OK
)
def delete_app_setting(
    setting_id: int,
    db: Session = Depends(get_db)
):
    setting = db.query(
        AppSetting
    ).filter(
        AppSetting.id == setting_id
    ).first()

    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App setting not found"
        )

    db.delete(setting)
    db.commit()

    return {
        "status_code": 200,
        "message": "App setting deleted successfully"
    }