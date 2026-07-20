from fastapi import FastAPI

from database import engine, Base
from models.state import State
from models.gift_master import GiftMaster
from models.users import User
from models.pricing_details import PricingDetail
from models.user_status import UserStatus
from models.gallery import Gallery


from routes.state import router as state_router
from routes.gift_master import router as gift_router
from routes.users import router as user_router
from routes.pricing_details import router as pricing_router
from routes.auth import router as auth_router
from routes.user_status_create import router as user_status_router
from routes.gallery import router as gallery_router



Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Dating Application API",
    version="1.0.0"
)

app.include_router(state_router)
app.include_router(gift_router)
app.include_router(user_router)
app.include_router(pricing_router)
app.include_router(auth_router)
app.include_router(user_status_router)
app.include_router(gallery_router)