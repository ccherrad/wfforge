#!/bin/bash
# Start the Celery Beat scheduler
# Uses SQLite for schedule persistence
celery -A src.tasks.scheduler beat --loglevel=info
