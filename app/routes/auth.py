from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import SessionLocal
from models.users import User
from schemas.auth import LoginRequest
from security import verify_password

router = APIRouter(prefix="/auth",tags=["Authentication"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/login")
def login(
    data: LoginRequest,
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(
        User.email == data.email
    ).first()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    if not verify_password(
        data.password,
        user.password
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    return {
        "message": "Login successful",
        "user_id": user.id,
        "role": user.role,
        "email": user.email
    }