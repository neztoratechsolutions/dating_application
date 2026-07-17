import uuid

from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Text,Enum
)
from sqlalchemy import (Column,String,Boolean,DateTime,Text,Integer,ForeignKey)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    # Authentication
    email = Column(String(150), unique=True, nullable=False, index=True)
    phone = Column(String(20), unique=True, nullable=True)
    password = Column(String(255), nullable=False)

    # Profile
    display_name = Column(String(100), nullable=False)
    bio = Column(Text, nullable=True)
    description = Column(Text, nullable=True)

    # Referral
    referral_code = Column(String(20), unique=True, nullable=False)
    state_id = Column(Integer, ForeignKey("states.id"))
    # Primary profile photo
    profile_photo = Column(String(255), nullable=True)

    # Account Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    gender = Column(
    Enum("Male", "Female", "Other", name="gender_enum"),
    nullable=False
)
    role = Column(
    Enum("admin", "creator", "customer", name="role_enum"),
    nullable=False,
    default="customer"
)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())