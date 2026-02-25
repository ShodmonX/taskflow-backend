from fastapi import FastAPI

from app.core.config import settings
from app.core.logging import setup_logging
from app.modules.auth.router import router as auth_router
from app.modules.organizations.router import router as organizations_router
from app.modules.projects.router import router as projects_router
from app.modules.tasks.router import router as tasks_router
from fastapi.middleware.cors import CORSMiddleware

setup_logging()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust as needed for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(organizations_router)
app.include_router(projects_router)
app.include_router(tasks_router)

@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.app_name}
