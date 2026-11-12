
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    UniqueConstraint
)
from sqlalchemy.sql import func

from database import Base


class CreatorAgreementAcceptance(Base):
    __tablename__ = "creator_agreement_acceptances"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    creator_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    agreement_id = Column(
        Integer,
        ForeignKey("creator_agreements.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    status = Column(
        String(30),
        nullable=False,
        default="Pending"
    )

    ip_address = Column(
        String(50),
        nullable=True
    )

    accepted_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    agreement_pdf = Column(
        String(255),
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "creator_id",
            "agreement_id",
            name="uq_creator_agreement_acceptance"
        ),
    )
