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
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=2,
    task_reject_on_worker_lost=True,
)

if settings.LOYALTY_RECALC_DEBUG:
    loyalty_schedule = crontab(minute="*")
else:
    loyalty_schedule = crontab(minute="0", hour="0", day_of_month="1")

celery_app.conf.beat_schedule = {
    "monthly-loyalty-recalc": {
        "task": "update_loyalty_levels",
        "schedule": loyalty_schedule,
    },
}
