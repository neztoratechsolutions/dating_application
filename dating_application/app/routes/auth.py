from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.users import User
from app.models.otp_verification import OTPVerification
from app.schemas.auth import LoginRequest,ForgotPasswordRequest,VerifyOTPRequest,ResetPasswordRequest
from app.security import verify_password,hash_password,generate_otp,send_otp_email


router = APIRouter(prefix="/auth",tags=["Authentication"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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

    return {
        "status_code": 200,
        "message": "Login successful",
        "user_id": user.id,
        "role": user.role,
        "email": user.email,
        "referral_code": user.referral_code
    }


# ----------------------------------------- Logout ----------------------------------------


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




