from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.sql import func

from app.database import Base


class TermsAndCondition(Base):
    __tablename__ = "terms_and_conditions"

    id = Column(Integer, primary_key=True, index=True)

    details = Column(Text, nullable=False)

    status = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )


class RefundPolicy(Base):
    __tablename__ = "refund_policies"

    id = Column(Integer, primary_key=True, index=True)

    details = Column(Text, nullable=False)

    status = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )


class CommunityGuideline(Base):
    __tablename__ = "community_guidelines"

    id = Column(Integer, primary_key=True, index=True)

    details = Column(Text, nullable=False)

    status = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )


class PrivacyPolicy(Base):
    __tablename__ = "privacy_policies"

    id = Column(Integer, primary_key=True, index=True)

    details = Column(Text, nullable=False)

    status = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )


class SEOSetting(Base):
    __tablename__ = "seo_settings"

    id = Column(Integer, primary_key=True, index=True)

    meta_title = Column(String(255), nullable=False)

    meta_keywords = Column(Text, nullable=True)

    meta_description = Column(Text, nullable=True)

    canonical_url = Column(String(255), nullable=True)

    robots = Column(String(100), default="index,follow")

    og_title = Column(String(255), nullable=True)

    og_description = Column(Text, nullable=True)

    og_image = Column(String(255), nullable=True)

    status = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )