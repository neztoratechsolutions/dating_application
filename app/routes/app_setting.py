# import os

# from fastapi import (APIRouter,Depends,HTTPException,status,UploadFile,File,Form)
# from sqlalchemy.orm import Session

# from database import get_db
# from models.app_setting import AppSetting
# from schemas.app_setting import AppSettingResponse



# router = APIRouter(prefix="/app-settings",tags=["App Settings"])

# UPLOAD_DIR = "uploads/app_settings"

# os.makedirs(UPLOAD_DIR,exist_ok=True)


# @router.post(
#     "/",
#     response_model=AppSettingResponse,
#     status_code=status.HTTP_201_CREATED
# )
# def create_app_setting(
#     app_name: str = Form(...),
#     support_email: str | None = Form(None),
#     support_number: str | None = Form(None),
#     logo: UploadFile | None = File(None),
#     favicon: UploadFile | None = File(None),
#     db: Session = Depends(get_db)
# ):
#     existing = db.query(
#         AppSetting
#     ).first()

#     # if existing:
#     #     raise HTTPException(
#     #         status_code=status.HTTP_400_BAD_REQUEST,
#     #         detail="App setting already exists"
#     #     )

#     logo_path = None
#     favicon_path = None

#     if logo:

#         logo_path = os.path.join(
#             UPLOAD_DIR,
#             logo.filename
#         )

#         with open(logo_path, "wb") as buffer:
#             buffer.write(
#                 logo.file.read()
#             )

#     if favicon:

#         favicon_path = os.path.join(
#             UPLOAD_DIR,
#             favicon.filename
#         )

#         with open(favicon_path, "wb") as buffer:
#             buffer.write(
#                 favicon.file.read()
#             )

#     setting = AppSetting(
#         app_name=app_name,
#         logo=logo_path,
#         favicon=favicon_path,
#         support_email=support_email,
#         support_number=support_number
#     )

#     db.add(setting)
#     db.commit()
#     db.refresh(setting)

#     return setting



# @router.get(
#     "/",
#     response_model=AppSettingResponse,
#     status_code=status.HTTP_200_OK
# )
# def get_app_setting(
#     db: Session = Depends(get_db)
# ):
#     setting = db.query(
#         AppSetting
#     ).first()

#     if not setting:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="App setting not found"
#         )

#     return setting




# @router.put(
#     "/{setting_id}",
#     response_model=AppSettingResponse,
#     status_code=status.HTTP_200_OK
# )
# def update_app_setting(
#     setting_id: int,
#     app_name: str | None = Form(None),
#     support_email: str | None = Form(None),
#     support_number: str | None = Form(None),
#     db: Session = Depends(get_db)
# ):
#     setting = db.query(
#         AppSetting
#     ).filter(
#         AppSetting.id == setting_id
#     ).first()

#     if not setting:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="App setting not found"
#         )

#     # Update only provided fields

#     if app_name not in [None, ""]:
#         setting.app_name = app_name

#     if support_email not in [None, ""]:
#         setting.support_email = support_email

#     if support_number not in [None, ""]:
#         setting.support_number = support_number

#     db.commit()
#     db.refresh(setting)

#     return setting



# @router.get(
#     "/{setting_id}",
#     response_model=AppSettingResponse,
#     status_code=status.HTTP_200_OK
# )
# def get_app_setting_by_id(
#     setting_id: int,
#     db: Session = Depends(get_db)
# ):
#     setting = db.query(
#         AppSetting
#     ).filter(
#         AppSetting.id == setting_id
#     ).first()

#     if not setting:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="App setting not found"
#         )

#     return setting



# @router.delete(
#     "/{setting_id}",
#     status_code=status.HTTP_200_OK
# )
# def delete_app_setting(
#     setting_id: int,
#     db: Session = Depends(get_db)
# ):
#     setting = db.query(
#         AppSetting
#     ).filter(
#         AppSetting.id == setting_id
#     ).first()

#     if not setting:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="App setting not found"
#         )

#     db.delete(setting)
#     db.commit()

#     return {
#         "status_code": 200,
#         "message": "App setting deleted successfully"
#     }
import os
import uuid

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Form,
)
from sqlalchemy.orm import Session

from database import get_db
from models.app_setting import AppSetting
from schemas.app_setting import AppSettingResponse


router = APIRouter(prefix="/app-settings", tags=["App Settings"])

UPLOAD_DIR = "uploads/app_settings"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# -----------------------------------------------------------------
# File helpers
# -----------------------------------------------------------------
def _save_upload(file: UploadFile | None) -> str | None:
    """Persist an uploaded file under UPLOAD_DIR.

    Returns the relative path (e.g. "uploads/app_settings/<uuid>_logo.png")
    or None when no file was supplied. The filename is sanitized with
    os.path.basename (guards against "../" path traversal) and prefixed
    with a uuid so repeated uploads never collide and browsers always
    fetch the newest bytes (cache busting via URL change).
    """
    if not file or not file.filename:
        return None
    safe_name = f"{uuid.uuid4().hex}_{os.path.basename(file.filename)}"
    path = os.path.join(UPLOAD_DIR, safe_name)
    with open(path, "wb") as buffer:
        buffer.write(file.file.read())
    return path


def _remove_file(path: str | None) -> None:
    """Delete a previously stored file, ignoring missing/invalid paths."""
    if not path:
        return
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


# -----------------------------------------------------------------
# Create (singleton upsert)
# -----------------------------------------------------------------
@router.post(
    "/",
    response_model=AppSettingResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_app_setting(
    app_name: str = Form(...),
    support_email: str | None = Form(None),
    support_number: str | None = Form(None),
    logo: UploadFile | None = File(None),
    favicon: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    """Create the app setting, or update it if one already exists.

    App settings are a singleton: there is only ever one row. The old
    "already exists" guard is replaced with an upsert so callers can POST
    safely without first checking GET / — this also protects against
    duplicate rows if the frontend's GET-first check races or fails.
    """
    setting = db.query(AppSetting).first()

    if setting:
        setting.app_name = app_name
        if support_email is not None:
            setting.support_email = support_email
        if support_number is not None:
            setting.support_number = support_number

        logo_path = _save_upload(logo)
        if logo_path:
            _remove_file(setting.logo)
            setting.logo = logo_path

        favicon_path = _save_upload(favicon)
        if favicon_path:
            _remove_file(setting.favicon)
            setting.favicon = favicon_path

        db.commit()
        db.refresh(setting)
        return setting

    setting = AppSetting(
        app_name=app_name,
        logo=_save_upload(logo),
        favicon=_save_upload(favicon),
        support_email=support_email,
        support_number=support_number,
    )
    db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting


# -----------------------------------------------------------------
# Read
# -----------------------------------------------------------------
@router.get(
    "/",
    response_model=AppSettingResponse,
    status_code=status.HTTP_200_OK,
)
def get_app_setting(db: Session = Depends(get_db)):
    setting = db.query(AppSetting).first()
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App setting not found",
        )
    return setting


@router.get(
    "/{setting_id}",
    response_model=AppSettingResponse,
    status_code=status.HTTP_200_OK,
)
def get_app_setting_by_id(setting_id: int, db: Session = Depends(get_db)):
    setting = (
        db.query(AppSetting)
        .filter(AppSetting.id == setting_id)
        .first()
    )
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App setting not found",
        )
    return setting


# -----------------------------------------------------------------
# Update (now supports logo + favicon replacement)
# -----------------------------------------------------------------
@router.put(
    "/{setting_id}",
    response_model=AppSettingResponse,
    status_code=status.HTTP_200_OK,
)
def update_app_setting(
    setting_id: int,
    app_name: str | None = Form(None),
    support_email: str | None = Form(None),
    support_number: str | None = Form(None),
    logo: UploadFile | None = File(None),
    favicon: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    setting = (
        db.query(AppSetting)
        .filter(AppSetting.id == setting_id)
        .first()
    )
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App setting not found",
        )

    # Update only provided text fields
    if app_name not in [None, ""]:
        setting.app_name = app_name
    if support_email not in [None, ""]:
        setting.support_email = support_email
    if support_number not in [None, ""]:
        setting.support_number = support_number

    # Replace images only when a new file is supplied; clean up the old one
    logo_path = _save_upload(logo)
    if logo_path:
        _remove_file(setting.logo)
        setting.logo = logo_path

    favicon_path = _save_upload(favicon)
    if favicon_path:
        _remove_file(setting.favicon)
        setting.favicon = favicon_path

    db.commit()
    db.refresh(setting)
    return setting


# -----------------------------------------------------------------
# Delete (also removes stored files)
# -----------------------------------------------------------------
@router.delete(
    "/{setting_id}",
    status_code=status.HTTP_200_OK,
)
def delete_app_setting(setting_id: int, db: Session = Depends(get_db)):
    setting = (
        db.query(AppSetting)
        .filter(AppSetting.id == setting_id)
        .first()
    )
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App setting not found",
        )
    _remove_file(setting.logo)
    _remove_file(setting.favicon)
    db.delete(setting)
    db.commit()
    return {
        "status_code": 200,
        "message": "App setting deleted successfully",
    }
