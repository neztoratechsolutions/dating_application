from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from database import engine, Base

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
from models.cms_models import AboutUs
from models.cms_models import FAQ
from models.cms_settings import SEOSetting
from models.support_center import SupportTicket
from models.app_setting import AppSetting
from models.state import State
from models.gift_master import GiftMaster
from models.voice_call import VoiceCall
from models.chat_history import (
    Chat,
    ChatMessage,
    ChatCallLog,
    ChatReaction,
    ChatDeleteHistory,
)
from models.chat_report import (
    ChatReport,
    ChatModerationAction,
)
from models.video_call import VideoCall
from models.wallet import Wallet


from routes.users import router as user_router
from routes.pricing_details import router as pricing_router
from routes.auth import router as auth_router
from routes.user_status_create import router as user_status_router
from routes.gallery import router as gallery_router
from routes.review import router as review_router
from routes.settings import router as setting_router
from routes.gift_details import router as giftdetails_router

from routes.follow_detail import router as followers_router
from routes.ad_settings import router as adsettings_router
from routes.tags import router as tags_router
from routes.privacy_policy import router as privacy_router
from routes.terms_and_conditions import router as terms_and_conditions_router
from routes.community_guidelines import router as community_guidelines_router
from routes.refund_policy import router as refund_policy_router
from routes.creator_agreement import router as creator_agreement_router
from routes.safety_policy import router as safety_policy_router
from routes.about_us import router as about_us_router
from routes.faq import router as faq_router
from routes.seo_settings import router as seo_settings_router
from routes.app_setting import router as app_setting_router
from routes.state import router as state_router
from routes.gift_master import router as gift_router
from routes.voice_call import router as voice_call_router

from routes.video_call import router as video_call_router
from routes.customer import router as customer_router
from routes.quick_pack import router as quick_pack_router


Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Dating Application API",
    version="1.0.0"
)

origins = [
    "http://localhost:5173", # Vite default
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://localhost:8080",
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(state_router)
app.include_router(gift_router)



# Include routes


app.include_router(user_router)
app.include_router(pricing_router)
app.include_router(auth_router)
app.include_router(user_status_router)
app.include_router(gallery_router)
app.include_router(review_router)
app.include_router(setting_router)
app.include_router(giftdetails_router)

app.include_router(followers_router)

app.include_router(quick_pack_router)
if not os.path.exists("uploads"):
    os.makedirs("uploads")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(adsettings_router)
app.include_router(tags_router)
app.include_router(privacy_router)
app.include_router(terms_and_conditions_router)
app.include_router(community_guidelines_router)
app.include_router(refund_policy_router)
app.include_router(creator_agreement_router)
app.include_router(safety_policy_router)
app.include_router(about_us_router)
app.include_router(faq_router)
app.include_router(seo_settings_router)
app.include_router(app_setting_router)
app.include_router(voice_call_router)
app.include_router(video_call_router)
app.include_router(customer_router)