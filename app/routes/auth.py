from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import SessionLocal
from models.users import User
from models.otp_verification import OTPVerification
from schemas.auth import LoginRequest,ForgotPasswordRequest,VerifyOTPRequest,ResetPasswordRequest
from security import verify_password,hash_password,generate_otp,send_otp_email
from datetime import datetime, timedelta
from jose import jwt

router = APIRouter(prefix="/auth",tags=["Authentication"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

SECRET_KEY = "velora-super-secret-key-change-this"
ALGORITHM = "HS256"

def create_access_token(
    data: dict,
    expires_delta: timedelta | None = None
):
    to_encode = data.copy()

    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=60)
    )

    to_encode.update({
        "exp": expire
    })

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

@router.post(
    "/login",
    status_code=status.HTTP_200_OK
)
def login(
    data: LoginRequest,
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(
        User.email == data.email
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if not verify_password(
        data.password,
        user.password
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid password"
        )

    # Create JWT token
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role
        }
    )

    return {
        "status_code": 200,
        "message": "Login successful",

        # JWT authentication
        "access_token": access_token,
        "token_type": "bearer",

        # Existing response fields
        "user_id": user.id,
        "role": user.role,
        "email": user.email,
        "referral_code": user.referral_code
    }

# ----------------------------------------- Logout ----------------------------------------


import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from database import get_db
from models.users import User

logger = logging.getLogger(__name__)

SECRET_KEY = "velora-super-secret-key-change-this"
ALGORITHM = "HS256"

bearer_scheme = HTTPBearer(auto_error=False)


def get_user_id_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> int:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token is missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )
        subject = payload.get("sub")

        if subject is None:
            raise HTTPException(
                status_code=401,
                detail="Token does not contain a user ID",
            )

        user_id = int(subject)

    except HTTPException:
        raise
    except (JWTError, ValueError, TypeError) as exc:
        logger.warning(
            "Chat JWT validation failed: %s: %s",
            type(exc).__name__,
            str(exc),
        )
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User associated with token was not found",
        )

    return user_id


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK
)
def logout():

    return {
        "status_code": 200,
        "message": "Logout successful"
    }




@router.post("/forgot-password")
async def forgot_password(
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.email == data.email
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    otp = generate_otp()

    existing_otp = db.query(
        OTPVerification
    ).filter(
        OTPVerification.user_id == user.id
    ).first()

    if existing_otp:
        existing_otp.otp = otp
        existing_otp.is_verified = False
    else:
        db.add(
            OTPVerification(
                user_id=user.id,
                otp=otp,
                is_verified=False
            )
        )

    db.commit()

    await send_otp_email(
        user.email,
        otp
    )

    return {
        "message": "OTP sent successfully"
    }




@router.post("/verify-otp")
def verify_otp(
    data: VerifyOTPRequest,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.email == data.email
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    otp_record = db.query(OTPVerification).filter(
        OTPVerification.user_id == user.id,
        OTPVerification.otp == data.otp
    ).first()

    if not otp_record:
        raise HTTPException(
            status_code=400,
            detail="Invalid OTP"
        )

    otp_record.is_verified = True

    db.commit()

    return {
        "message": "OTP verified successfully"
    }




@router.post("/reset-password")
def reset_password(
    data: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.email == data.email
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    otp_record = db.query(OTPVerification).filter(
        OTPVerification.user_id == user.id,
        OTPVerification.otp == data.otp,
        OTPVerification.is_verified == True
    ).first()

    if not otp_record:
        raise HTTPException(
            status_code=400,
            detail="OTP verification required"
        )

    user.password = hash_password(
        data.new_password
    )

    db.delete(otp_record)

    db.commit()

    return {
        "message": "Password reset successful"
    }




