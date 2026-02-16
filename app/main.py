from fastapi import FastAPI

from app.core.config import settings
from app.core.logging import setup_logging
from app.modules.auth.router import router as auth_router

setup_logging()

app = FastAPI(title=settings.app_name)

app.include_router(auth_router)

@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.app_name}
