from celery import Celery
from src.config import settings

celery_app = Celery(
    "wfforge",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "src.tasks.actions.input_file",
        "src.tasks.actions.call_agent",
        "src.tasks.actions.router",
        "src.tasks.actions.merge_results",
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="pickle",
    result_serializer="pickle",
    accept_content=["pickle", "json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_send_sent_event=True,
    # Filesystem broker configuration
    broker_transport_options={
        "data_folder_in": settings.celery_broker_folder,
        "data_folder_out": settings.celery_broker_folder + "/out",
        "data_folder_processed": settings.celery_broker_processed_folder,
    },
    # SQLite result backend configuration
    result_backend_transport_options={
        "echo": False,  # Don't echo SQL queries
    },
)

if __name__ == "__main__":
    celery_app.start()