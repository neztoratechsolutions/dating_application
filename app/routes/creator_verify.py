
import os
import uuid
from io import BytesIO

import soundfile as sf

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from database import get_db
from models.users import User
from models.creator_verify import CreatorVerification


router = APIRouter(
    prefix="/creator-verification",
    tags=["Creator Verification"]
)

VOICE_UPLOAD_DIR = "uploads/creator_verification/voice"
SELFIE_UPLOAD_DIR = "uploads/creator_verification/selfie"

os.makedirs(VOICE_UPLOAD_DIR, exist_ok=True)
os.makedirs(SELFIE_UPLOAD_DIR, exist_ok=True)

MAX_VOICE_SIZE = 10 * 1024 * 1024
MAX_SELFIE_SIZE = 5 * 1024 * 1024

MIN_VOICE_DURATION = 5.0
MAX_VOICE_DURATION = 6.0


def get_creator(db: Session, creator_id: int):

    creator = db.query(User).filter(
        User.id == creator_id,
        User.role == "creator"
    ).first()

    if not creator:
        raise HTTPException(
            status_code=404,
            detail="Creator not found"
        )

    return creator


def get_or_create_verification(db: Session, creator_id: int):

    verification = db.query(CreatorVerification).filter(
        CreatorVerification.creator_id == creator_id
    ).first()

    if not verification:
        verification = CreatorVerification(
            creator_id=creator_id,
            voice_status="pending",
            selfie_status="pending"
        )

        db.add(verification)
        db.commit()
        db.refresh(verification)

    return verification


def verification_response(verification):

    completed_steps = 0

    if verification.voice_status in ["submitted", "approved"]:
        completed_steps += 1

    if verification.selfie_status in ["submitted", "approved"]:
        completed_steps += 1

    return {
        "creator_id": verification.creator_id,
        "voice_file": verification.voice_file,
        "voice_duration": verification.voice_duration,
        "voice_status": verification.voice_status,
        "selfie_image": verification.selfie_image,
        "selfie_status": verification.selfie_status,
        "completed_steps": completed_steps,
        "total_steps": 3,
        "created_at": verification.created_at,
        "updated_at": verification.updated_at
    }


@router.post("/voice")
async def upload_voice(
    creator_id: int = Form(...),
    voice_file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    get_creator(db, creator_id)

    if voice_file.content_type not in [
        "audio/wav",
        "audio/x-wav",
        "audio/wave"
    ]:
        raise HTTPException(
            status_code=400,
            detail="Please upload a WAV audio file"
        )

    audio_data = await voice_file.read()

    if not audio_data:
        raise HTTPException(
            status_code=400,
            detail="Audio file is empty"
        )

    if len(audio_data) > MAX_VOICE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="Voice file size must be below 10 MB"
        )

    try:
        audio_info = sf.info(BytesIO(audio_data))

        audio_duration = float(audio_info.duration)

        if audio_info.format != "WAV":
            raise HTTPException(
                status_code=400,
                detail="Invalid WAV audio file"
            )

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid or unsupported audio file"
        )

    # Allow only recordings between 5 and 6 seconds
    if not MIN_VOICE_DURATION <= audio_duration <= MAX_VOICE_DURATION:
        raise HTTPException(
            status_code=400,
            detail="Voice recording must be between 5 and 6 seconds"
        )

    verification = get_or_create_verification(db, creator_id)

    filename = f"{uuid.uuid4()}.wav"
    file_path = os.path.join(VOICE_UPLOAD_DIR, filename)

    with open(file_path, "wb") as f:
        f.write(audio_data)

    old_file = verification.voice_file

    try:
        verification.voice_file = file_path.replace("\\", "/")
        verification.voice_duration = audio_duration
        verification.voice_status = "submitted"

        db.commit()
        db.refresh(verification)

    except Exception:
        db.rollback()

        if os.path.exists(file_path):
            os.remove(file_path)

        raise HTTPException(
            status_code=500,
            detail="Failed to upload voice recording"
        )

    if old_file and os.path.exists(old_file):
        os.remove(old_file)

    return {
        "message": "Voice recording uploaded successfully",
        "data": verification_response(verification)
    }


@router.post("/selfie")
async def upload_selfie(
    creator_id: int = Form(...),
    selfie_image: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    get_creator(db, creator_id)

    if selfie_image.content_type not in [
        "image/jpeg",
        "image/png"
    ]:
        raise HTTPException(
            status_code=400,
            detail="Only JPG and PNG images are allowed"
        )

    image_data = await selfie_image.read()

    if not image_data:
        raise HTTPException(
            status_code=400,
            detail="Selfie image is empty"
        )

    if len(image_data) > MAX_SELFIE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="Selfie image size must be below 5 MB"
        )

    if image_data.startswith(b"\xff\xd8\xff"):
        extension = ".jpg"

    elif image_data.startswith(b"\x89PNG\r\n\x1a\n"):
        extension = ".png"

    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid image file"
        )

    verification = get_or_create_verification(db, creator_id)

    filename = f"{uuid.uuid4()}{extension}"
    file_path = os.path.join(SELFIE_UPLOAD_DIR, filename)

    with open(file_path, "wb") as f:
        f.write(image_data)

    old_file = verification.selfie_image

    try:
        verification.selfie_image = file_path.replace("\\", "/")
        verification.selfie_status = "submitted"

        db.commit()
        db.refresh(verification)

    except Exception:
        db.rollback()

        if os.path.exists(file_path):
            os.remove(file_path)

        raise HTTPException(
            status_code=500,
            detail="Failed to upload selfie"
        )

    if old_file and os.path.exists(old_file):
        os.remove(old_file)

    return {
        "message": "Selfie uploaded successfully",
        "data": verification_response(verification)
    }


@router.get("/{creator_id}")
def get_creator_verification(
    creator_id: int,
    db: Session = Depends(get_db)
):

    get_creator(db, creator_id)

    verification = db.query(CreatorVerification).filter(
        CreatorVerification.creator_id == creator_id
    ).first()

    if not verification:
        return {
            "creator_id": creator_id,
            "voice_file": None,
            "voice_duration": None,
            "voice_status": "pending",
            "selfie_image": None,
            "selfie_status": "pending",
            "completed_steps": 0,
            "total_steps": 3
        }

    return verification_response(verification)
