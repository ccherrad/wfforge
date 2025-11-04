FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies including curl for health checks
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy application code
COPY . .

# Install dependencies from pyproject.toml
RUN uv pip install --system --no-cache \
    fastapi>=0.104.1 \
    uvicorn>=0.24.0 \
    celery>=5.3.4 \
    redis>=5.0.1 \
    sqlalchemy>=2.0.23 \
    pydantic>=2.5.0 \
    pydantic-settings>=2.1.0 \
    alembic>=1.12.1 \
    python-multipart>=0.0.6 \
    structlog>=23.2.0 \
    python-dotenv>=1.0.0

# Create directory for SQLite database
RUN mkdir -p /app/data

# Expose port
EXPOSE 8000

# Default command (can be overridden in docker-compose)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
