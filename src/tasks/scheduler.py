from celery import Celery
from celery.schedules import crontab
from datetime import datetime
import structlog
import os

from src.config import settings
from src.database import db
from src.workflows import services

logger = structlog.get_logger(__name__)

# Ensure broker directories exist before Celery starts
os.makedirs(settings.celery_broker_folder, exist_ok=True)
os.makedirs(os.path.join(settings.celery_broker_folder, "out"), exist_ok=True)
os.makedirs(settings.celery_broker_processed_folder, exist_ok=True)

celery_app = Celery(
    "wfforge_scheduler",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Configure Celery Beat to use SQLite database for schedule persistence
celery_app.conf.update(
    beat_dburi=f"sqlite:///{db.db_path}",  # Use SQLite for beat schedule
    beat_schedule_filename=None,  # Don't use file-based schedule
    # Filesystem broker configuration
    broker_transport_options={
        "data_folder_in": settings.celery_broker_folder,
        "data_folder_out": os.path.join(settings.celery_broker_folder, "out"),
        "data_folder_processed": settings.celery_broker_processed_folder,
    },
    # SQLite result backend configuration
    result_backend_transport_options={
        "echo": False,  # Don't echo SQL queries
    },
    task_serializer="pickle",
    result_serializer="pickle",
    accept_content=["pickle", "json"],
    timezone="UTC",
    enable_utc=True,
)

# Configure Celery Beat scheduler
celery_app.conf.beat_schedule = {
    # Run scheduled workflows every minute
    "run-scheduled-workflows": {
        "task": "src.tasks.scheduler.run_scheduled_workflows",
        "schedule": crontab(minute="*"),  # Every minute
    },
}


@celery_app.task
def run_scheduled_workflows():
    """Task to execute scheduled workflows based on their crontab expressions"""
    logger.info("Checking for scheduled workflows to run")

    try:
        with db.get_connection() as conn:
            # Get all active workflows with crontab expressions
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM workflows
                WHERE status = 'ACTIVE'
                AND crontab_expression IS NOT NULL
                AND crontab_expression != ''
                """
            )
            rows = cursor.fetchall()

            workflows = [
                services.get_workflow_by_id(conn, row["id"]) for row in rows
            ]

            logger.info(f"Found {len(workflows)} scheduled workflows")

            for workflow in workflows:
                if workflow and workflow.pipeline:
                    try:
                        # Execute the workflow pipeline
                        logger.info(
                            f"Executing scheduled workflow: {workflow.name}",
                            workflow_id=workflow.id,
                        )

                        # Update last_run_at
                        services.update_workflow(
                            conn, workflow.id, last_run_at=datetime.now()
                        )

                        # Execute the pipeline
                        workflow.pipeline.apply_async()

                        logger.info(
                            f"Successfully triggered workflow: {workflow.name}",
                            workflow_id=workflow.id,
                        )
                    except Exception as e:
                        logger.error(
                            f"Error executing workflow: {workflow.name}",
                            workflow_id=workflow.id,
                            error=str(e),
                        )

    except Exception as e:
        logger.error(f"Error in run_scheduled_workflows: {str(e)}")


@celery_app.task
def schedule_workflow(workflow_id: int, crontab_expression: str):
    """
    Schedule a workflow to run on a crontab schedule.
    This creates or updates a periodic task in the SQLite database.
    """
    logger.info(
        f"Scheduling workflow {workflow_id} with crontab: {crontab_expression}"
    )

    try:
        with db.get_connection() as conn:
            workflow = services.get_workflow_by_id(conn, workflow_id)

            if not workflow:
                logger.error(f"Workflow {workflow_id} not found")
                return False

            # Update workflow with crontab expression
            services.update_workflow(
                conn, workflow_id, crontab_expression=crontab_expression
            )

            logger.info(f"Successfully scheduled workflow {workflow_id}")
            return True

    except Exception as e:
        logger.error(f"Error scheduling workflow: {str(e)}")
        return False


@celery_app.task
def unschedule_workflow(workflow_id: int):
    """
    Unschedule a workflow by removing its crontab expression.
    """
    logger.info(f"Unscheduling workflow {workflow_id}")

    try:
        with db.get_connection() as conn:
            # Remove crontab expression
            services.update_workflow(conn, workflow_id, crontab_expression=None)

            logger.info(f"Successfully unscheduled workflow {workflow_id}")
            return True

    except Exception as e:
        logger.error(f"Error unscheduling workflow: {str(e)}")
        return False
