from celery import Celery
from celery.schedules import crontab

from src.config import settings

celery_app = Celery(
    "wfforge_scheduler",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Configure Celery Beat scheduler
celery_app.conf.beat_schedule = {
    # Example: Run every minute
    "run-scheduled-workflows": {
        "task": "src.tasks.scheduler.run_scheduled_workflows",
        "schedule": crontab(minute="*"),  # Every minute
    },
}


@celery_app.task
def run_scheduled_workflows():
    """Task to execute scheduled workflows"""
    # This would query the database for workflows with active cron expressions
    # and execute them
    pass