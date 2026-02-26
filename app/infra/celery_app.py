from celery import Celery
from datetime import timedelta

from app.core.config import settings


celery_app = Celery(
    "taskflow",
    broker=settings.rabbitmq_url,
    backend=settings.redis_url,
    include=[
        "app.modules.notifications.celery_tasks"
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "dispatch-notification-outbox": {
            "task": "taskflow.dispatch_notifications_outbox",
            "schedule": timedelta(seconds=15),
            "kwargs": {"limit": 100},
        }
    },
)

@celery_app.task(name="taskflow.ping")
def ping() -> str:
    return "pong"
