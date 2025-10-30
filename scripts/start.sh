#!/bin/bash

# Start the FastAPI server
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload