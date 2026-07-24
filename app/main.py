from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles


from database import engine, Base

from models.state import State
from models.gift_master import GiftMaster
from models.users import User
from models.pricing_details import PricingDetail
from models.user_status import UserStatus
from models.gallery import Gallery
from models.review import Review
from models.settings import Setting
from models.gift_details import GiftDetail
from models.ad_setting import AdSetting
from models.tags import Tag
from models.cms_settings import PrivacyPolicy
from models.cms_settings import CommunityGuideline
from models.cms_settings import RefundPolicy
from models.cms_models import CreatorAgreement
from models.cms_models import SafetyPolicy


from routes.state import router as state_router
from routes.gift_master import router as gift_router
from routes.users import router as user_router
from routes.pricing_details import router as pricing_router
from routes.auth import router as auth_router
from routes.user_status_create import router as user_status_router
from routes.gallery import router as gallery_router
from routes.review import router as review_router
from routes.settings import router as setting_router
from routes.gift_details import router as giftdetails_router
from routes.ad_settings import router as adsettings_router
from routes.tags import router as tags_router
from routes.privacy_policy import router as privacy_router
from routes.terms_and_conditions import router as terms_and_conditions_router
from routes.community_guidelines import router as community_guidelines_router
from routes.refund_policy import router as refund_policy_router
from routes.creator_agreement import router as creator_agreement_router
from routes.safety_policy import router as safety_policy_router


# Create FastAPI app first
app = FastAPI(
    title="Dating Application API",
    version="1.0.0"
)


app.mount("/uploads",StaticFiles(directory="uploads"),name="uploads")


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Create tables
Base.metadata.create_all(bind=engine)


# Include routes
app.include_router(state_router)
app.include_router(gift_router)
app.include_router(user_router)
app.include_router(pricing_router)
app.include_router(auth_router)
app.include_router(user_status_router)
app.include_router(gallery_router)
app.include_router(review_router)
app.include_router(setting_router)
app.include_router(giftdetails_router)
app.include_router(adsettings_router)
app.include_router(tags_router)
app.include_router(privacy_router)
app.include_router(terms_and_conditions_router)
app.include_router(community_guidelines_router)
app.include_router(refund_policy_router)
app.include_router(creator_agreement_router)
app.include_router(safety_policy_router)