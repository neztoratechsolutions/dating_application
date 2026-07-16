from fastapi import FastAPI
from database import engine
app = FastAPI(
    title="Dating Application API",
    version="1.0.0"
)


@app.get("/health_check")
def root():
    return {"message": "Dating Application API is Running 🚀"}