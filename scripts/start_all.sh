#!/bin/bash
# Start all WFForge services
# No external services (Redis, PostgreSQL) required!

echo "Starting WFForge - Lightweight Workflow Engine"
echo "=============================================="
echo ""
echo "This will start:"
echo "  1. FastAPI server (port 8000)"
echo "  2. Celery worker (filesystem broker)"
echo "  3. Celery Beat scheduler (SQLite persistence)"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Stopping all services..."
    kill $(jobs -p) 2>/dev/null
    exit
}

trap cleanup SIGINT SIGTERM

# Start FastAPI server
echo "[1/3] Starting FastAPI server..."
uvicorn src.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

# Wait a bit for the API to start
sleep 2

# Start Celery worker
echo "[2/3] Starting Celery worker..."
celery -A src.tasks.worker worker --loglevel=info &
WORKER_PID=$!

# Wait a bit for the worker to start
sleep 2

# Start Celery Beat scheduler
echo "[3/3] Starting Celery Beat scheduler..."
celery -A src.tasks.scheduler beat --loglevel=info &
BEAT_PID=$!

echo ""
echo "✓ All services started!"
echo ""
echo "  API:       http://localhost:8000"
echo "  API Docs:  http://localhost:8000/docs"
echo "  Health:    http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for all background processes
wait
