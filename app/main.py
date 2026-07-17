from fastapi import FastAPI

from app.database import engine, Base
from app.models.state import State
from app.models.gift_master import GiftMaster
from app.models.users import User
from app.models.pricing_details import PricingDetail



from app.routes.state import router as state_router
from app.routes.gift_master import router as gift_router
from app.routes.users import router as user_router
from app.routes.pricing_details import router as pricing_router
from routes.auth import router as auth_router


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