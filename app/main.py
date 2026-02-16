from fastapi import FastAPI

from app.core.config import settings
from app.core.logging import setup_logging


setup_logging()

app = FastAPI(title=settings.app_name)

@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.app_name}
