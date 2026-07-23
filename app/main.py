from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os

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
from routes.follow_detail import router as followers_router

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


if not os.path.exists("uploads"):
    os.makedirs("uploads")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")