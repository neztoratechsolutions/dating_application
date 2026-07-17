from fastapi import FastAPI

from app.database import engine, Base
from app.models.state import State
from app.routes.state import router as state_router


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Dating Application API",
    version="1.0.0"
)

app.include_router(state_router)