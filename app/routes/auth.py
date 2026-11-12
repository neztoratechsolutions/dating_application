import logging
import uuid

from datetime import datetime, timedelta

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Request
)

from sqlalchemy.orm import Session

from jose import jwt

from database import SessionLocal

from models.users import User
from models.otp_verification import OTPVerification
from models.live_users import LiveUserSession

from schemas.auth import (
    LoginRequest,
    ForgotPasswordRequest,
    VerifyOTPRequest,
    ResetPasswordRequest
)

from security import (
    verify_password,
    hash_password,
    generate_otp,
    send_otp_email
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


logger = logging.getLogger(__name__)


SECRET_KEY = "velora-super-secret-key-change-this"
ALGORITHM = "HS256"


def get_db():
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


# =========================================================
# CREATE ACCESS TOKEN
# =========================================================

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


# =========================================================
# LOGIN
# =========================================================

@router.post(
    "/login",
    status_code=status.HTTP_200_OK
)
def login(
    data: LoginRequest,
    request: Request,
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

    # -----------------------------------------------------
    # Generate unique session ID
    # -----------------------------------------------------

    session_id = str(uuid.uuid4())

    # -----------------------------------------------------
    # Detect device from User-Agent
    # -----------------------------------------------------

    user_agent = request.headers.get(
        "user-agent",
        "Unknown"
    )

    device = detect_device(user_agent)

    # -----------------------------------------------------
    # Create live session
    # -----------------------------------------------------

    live_session = LiveUserSession(
        session_id=session_id,
        user_id=user.id,
        device=device,
        is_online=True
    )

    db.add(live_session)

    db.commit()

    db.refresh(live_session)

    # -----------------------------------------------------
    # Create JWT
    # -----------------------------------------------------

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role,
            "session_id": session_id
        }
    )

    return {

        "status_code": 200,

        "message": "Login successful",

        "access_token": access_token,

        "token_type": "bearer",

        "user_id": user.id,

        "role": user.role,

        "email": user.email,

        "referral_code": user.referral_code,

        "session_id": session_id,

        "device": device
    }


# =========================================================
# DEVICE DETECTION
# =========================================================

def detect_device(user_agent: str) -> str:

    ua = user_agent.lower()

    if "android" in ua:
        return "Android"

    if "iphone" in ua:
        return "iPhone"

    if "ipad" in ua:
        return "iPad"

    if "windows" in ua:
        return "Windows"

    if "macintosh" in ua:
        return "Mac"

    if "linux" in ua:
        return "Linux"

    return "Unknown"


# =========================================================
# LOGOUT
# =========================================================

from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials
)

from jose import JWTError


bearer_scheme = HTTPBearer(
    auto_error=False
)


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK
)
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(
        bearer_scheme
    ),
    db: Session = Depends(get_db)
):

    if credentials is None:

        raise HTTPException(
            status_code=401,
            detail="Bearer token is missing"
        )

    token = credentials.credentials

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        session_id = payload.get("session_id")

        if not session_id:

            raise HTTPException(
                status_code=400,
                detail="Session ID not found in token"
            )

    except JWTError:

        raise HTTPException(
            status_code=401,
            detail="Invalid or expired authentication token"
        )

    session = db.query(
        LiveUserSession
    ).filter(
        LiveUserSession.session_id == session_id
    ).first()

    if session:

        session.is_online = False

        session.logout_at = datetime.utcnow()

        session.last_activity_at = datetime.utcnow()

        db.commit()

    return {

        "status_code": 200,

        "message": "Logout successful"
    }


# =========================================================
# HEARTBEAT
# =========================================================

@router.post(
    "/heartbeat",
    status_code=status.HTTP_200_OK
)
def heartbeat(
    credentials: HTTPAuthorizationCredentials = Depends(
        bearer_scheme
    ),
    db: Session = Depends(get_db)
):

    if credentials is None:

        raise HTTPException(
            status_code=401,
            detail="Bearer token is missing"
        )

    try:

        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        session_id = payload.get("session_id")

        if not session_id:

            raise HTTPException(
                status_code=401,
                detail="Session ID not found in token"
            )

    except JWTError:

        raise HTTPException(
            status_code=401,
            detail="Invalid or expired authentication token"
        )

    session = db.query(
        LiveUserSession
    ).filter(
        LiveUserSession.session_id == session_id
    ).first()

    if not session:

        raise HTTPException(
            status_code=404,
            detail="Live session not found"
        )

    session.is_online = True

    session.last_activity_at = datetime.utcnow()

    session.logout_at = None

    db.commit()

    return {

        "status_code": 200,

        "message": "Session activity updated successfully"
    }


# =========================================================
# FORGOT PASSWORD
# =========================================================

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


# =========================================================
# VERIFY OTP
# =========================================================

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

    otp_record = db.query(
        OTPVerification
    ).filter(
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


# =========================================================
# RESET PASSWORD
# =========================================================

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

    otp_record = db.query(
        OTPVerification
    ).filter(
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