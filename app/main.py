import asyncio
from datetime import datetime, timezone
from typing import Awaitable, cast

from fastapi import FastAPI, Response, status
from kombu import Connection
from sqlalchemy import text

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.session import AsyncSessionLocal
from app.infra.redis import redis_client
from app.modules.auth.router import router as auth_router
from app.modules.notifications.router import router as notifications_router
from app.modules.organizations.router import router as organizations_router
from app.modules.projects.router import router as projects_router
from app.modules.tasks.router import router as tasks_router
from fastapi.middleware.cors import CORSMiddleware

setup_logging()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(organizations_router)
app.include_router(projects_router)
app.include_router(tasks_router)
app.include_router(notifications_router)


async def _check_db() -> tuple[bool, str | None]:
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True, None
    except Exception as exc:
        return False, str(exc)


async def _check_redis() -> tuple[bool, str | None]:
    try:
        ping_result = cast(Awaitable[bool], redis_client.ping())
        ok = bool(await ping_result)
        if not ok:
            return False, "Redis ping failed"
        return True, None
    except Exception as exc:
        return False, str(exc)


def _rabbitmq_check_sync() -> None:
    with Connection(settings.rabbitmq_url, connect_timeout=3) as conn:
        conn.connect()


async def _check_rabbitmq() -> tuple[bool, str | None]:
    try:
        await asyncio.to_thread(_rabbitmq_check_sync)
        return True, None
    except Exception as exc:
        return False, str(exc)


@app.get("/health")
async def health(response: Response) -> dict:
    db_res, redis_res, rabbitmq_res = await asyncio.gather(
        _check_db(),
        _check_redis(),
        _check_rabbitmq(),
    )
    checks = {
        "database": {"ok": db_res[0], "error": db_res[1]},
        "redis": {"ok": redis_res[0], "error": redis_res[1]},
        "rabbitmq": {"ok": rabbitmq_res[0], "error": rabbitmq_res[1]},
    }
    overall_ok = all(v["ok"] for v in checks.values())
    if not overall_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ok" if overall_ok else "degraded",
        "service": settings.app_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }
