#!/bin/bash

# Start the Celery worker
celery -A src.tasks.worker.celery_app worker --loglevel=info