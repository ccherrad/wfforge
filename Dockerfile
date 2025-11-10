# WFForge - Lightweight Workflow Engine
# Multi-stage build for smaller image size

# Build stage
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    fastapi==0.104.1 \
    uvicorn==0.24.0 \
    celery==5.3.4 \
    pydantic==2.5.0 \
    pydantic-settings==2.1.0 \
    python-multipart==0.0.6 \
    structlog==23.2.0 \
    python-dotenv==1.0.0

# Production stage
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY README.md MIGRATION_GUIDE.md REDIS_REMOVAL_GUIDE.md ./

# Create directories for SQLite databases and Celery broker
RUN mkdir -p /app/data /app/celery_broker/out /app/celery_broker/processed

# Create non-root user for security
RUN useradd -m -u 1000 wfforge && \
    chown -R wfforge:wfforge /app

# Switch to non-root user
USER wfforge

# Expose API port
EXPOSE 8000

# Default command (can be overridden in docker-compose)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
