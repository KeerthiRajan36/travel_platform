import os

from celery import Celery
from celery.schedules import crontab

BROKER_URL = os.environ.get("CELERY_BROKER_URL", "memory://")
RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "cache+memory://")

celery_app = Celery(
    "travel_platform",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_always_eager=(BROKER_URL == "memory://"),
    task_eager_propagates=True,
    timezone="UTC",
    beat_schedule={
        "upcoming-tour-reminders-daily": {
            "task": "app.tasks.send_upcoming_tour_reminders",
            "schedule": crontab(hour=8, minute=0),  # every day at 08:00 UTC
            "args": (3,),  # remind travelers 3 days before their tour starts
        },
    },
)
