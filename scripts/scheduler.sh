#!/bin/bash

# Start the Celery Beat scheduler
celery -A src.tasks.scheduler.celery_app beat --loglevel=info