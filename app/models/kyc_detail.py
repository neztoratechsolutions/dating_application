from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func

from database import Base


class KYCDetail(Base):
    __tablename__ = "kyc_details"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    # ======================================================
    # KYC DOCUMENTS
    # ======================================================

    aadhar_photo = Column(
        String(255),
        nullable=False
    )

    pan_photo = Column(
        String(255),
        nullable=False
    )

    selfie_photo = Column(
        String(255),
        nullable=False
    )


    # ======================================================
    # DOCUMENT STATUS
    # ======================================================

    aadhar_status = Column(
        String(30),
        nullable=False,
        default="Pending"
    )

    pan_status = Column(
        String(30),
        nullable=False,
        default="Pending"
    )

    selfie_status = Column(
        String(30),
        nullable=False,
        default="Pending"
    )


    # ======================================================
    # OVERALL KYC STATUS
    # ======================================================

    status = Column(
        String(30),
        nullable=False,
        default="Pending"
    )

    # ======================================================
    # REJECTION REASON
    # ======================================================

    rejection_reason = Column(
        String(500),
        nullable=True
    )

    # ======================================================
    # TIMESTAMPS
    # ======================================================

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )




class CreatorKYC(Base):
    __tablename__ = "creator_kyc"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    # Bank document
    bank_photo = Column(
        String(255),
        nullable=False
    )

    bank_status = Column(
        String(30),
        nullable=False,
        default="Pending"
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )