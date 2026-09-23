from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base

from app.models.state import State
from app.models.gift_master import GiftMaster
from app.models.users import User
from app.models.pricing_details import PricingDetail

from app.models.user_status import UserStatus
from app.models.gallery import Gallery
from app.models.review import Review
from app.models.settings import Setting
from app.models.gift_details import GiftDetail
from app.models.help_support import HelpSupport
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os

from app.routes.state import router as state_router
from app.routes.gift_master import router as gift_router
from app.routes.users import router as user_router
from app.routes.pricing_details import router as pricing_router
from app.routes.auth import router as auth_router
from app.routes.user_status_create import router as user_status_router
from app.routes.gallery import router as gallery_router
from app.routes.review import router as review_router
from app.routes.settings import router as setting_router
from app.routes.gift_details import router as giftdetails_router
from app.routes.follow_detail import router as followers_router
from app.routes.gift_receive import router as giftreceive_router
from app.routes.count import router as count_router
from app.routes.favorite import router as favorite_router
from app.routes.quick_pack import router as quick_pack_router
from app.routes.help_support import router as help_support
# from app.routes.admin_dashboard import router as admin_dashboard_router

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
app.include_router(user_router)
app.include_router(pricing_router)
app.include_router(auth_router)
app.include_router(user_status_router)
app.include_router(gallery_router)
app.include_router(review_router)
app.include_router(setting_router)
app.include_router(giftdetails_router)
app.include_router(followers_router)
app.include_router(giftreceive_router)
app.include_router(count_router)
app.include_router(favorite_router)
app.include_router(quick_pack_router)
app.include_router(help_support)
# app.include_router(admin_dashboard_router)


if not os.path.exists("uploads"):
    os.makedirs("uploads")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")