#!/bin/bash
# Start the FastAPI server
# Database auto-initializes on startup
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
