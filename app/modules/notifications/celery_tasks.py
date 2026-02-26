from celery import shared_task

from app.modules.notifications.service import NotificationService


notification_service = NotificationService()


@shared_task(name="taskflow.task_assigned")
def task_assigned(event: dict) -> None:
    """
    event example:
    {
      "org_id": "...",
      "project_id": "...",
      "task_id": "...",
      "assigned_to": "...",
      "assigned_by": "...",
      "title": "Fix bug",
      "ts": "2026-02-16T..."
    }
    """

    notification_service.create_task_assigned(event)


@shared_task(name="taskflow.dispatch_notifications_outbox")
def dispatch_notifications_outbox(limit: int = 100) -> int:
    return notification_service.dispatch_outbox(limit=limit)
