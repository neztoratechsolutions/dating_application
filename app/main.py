from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine, Base

from models.state import State
from models.gift_master import GiftMaster
from models.users import User
from models.pricing_details import PricingDetail


from routes.state import router as state_router
from routes.gift_master import router as gift_router
from routes.users import router as user_router
from routes.pricing_details import router as pricing_router


# Create FastAPI app first
app = FastAPI(
    title="Dating Application API",
    version="1.0.0"
)


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