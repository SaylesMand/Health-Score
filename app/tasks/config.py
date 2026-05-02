from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "health_tasks",
    broker=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0",
    backend=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0",
)

import app.tasks.worker  # noqa: E402, F401

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Moscow",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=2,
)

celery_app.conf.beat_schedule = {
    "every-minute-loyalty-update": {
        "task": "update_loyalty_levels",
        "schedule": crontab(minute="*"),
    },
}
