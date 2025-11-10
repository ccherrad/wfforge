#!/bin/bash
# Start the Celery worker
# No Redis required - uses filesystem broker!
celery -A src.tasks.worker worker --loglevel=info
