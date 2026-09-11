from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.database import Base


class CreatorAgreement(Base):
    __tablename__ = "creator_agreements"

    id = Column(Integer, primary_key=True, index=True)

    details = Column(Text, nullable=False)

    status = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )


class SafetyPolicy(Base):
    __tablename__ = "safety_policies"

    id = Column(Integer, primary_key=True, index=True)

    details = Column(Text, nullable=False)

    status = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )


class AboutUs(Base):
    __tablename__ = "about_us"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(150), nullable=False)

    details = Column(Text, nullable=False)

    status = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )


class FAQ(Base):
    __tablename__ = "faqs"

    id = Column(Integer, primary_key=True, index=True)

    question = Column(String(500), nullable=False)

    answer = Column(Text, nullable=False)

    created_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    status = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )