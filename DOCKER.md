# Docker Deployment Guide

This guide explains how to run WFForge using Docker and Docker Compose.

## Prerequisites

- Docker Engine 20.10+ ([Install Docker](https://docs.docker.com/get-docker/))
- Docker Compose 2.0+ (usually bundled with Docker)

## Quick Start

### 1. Build and Start All Services

```bash
# Build images and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

That's it! The application is now running:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### 2. Stop Services

```bash
# Stop all services (keeps data)
docker-compose down

# Stop and remove all data
docker-compose down -v
```

## Architecture

The Docker setup runs 3 services from a single image:

```
┌─────────────────────────────────────────────────┐
│  Docker Compose - WFForge Stack                 │
├─────────────────────────────────────────────────┤
│                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌────────┐│
│  │  API         │  │  Worker      │  │ Beat   ││
│  │  (FastAPI)   │  │  (Celery)    │  │(Sched.)││
│  │  Port: 8000  │  │              │  │        ││
│  └──────┬───────┘  └──────┬───────┘  └────┬───┘│
│         │                 │                │    │
│         └─────────────────┴────────────────┘    │
│                           │                     │
│  ┌─────────────────────────────────────────┐   │
│  │  Shared Volumes                         │   │
│  ├─────────────────────────────────────────┤   │
│  │  wfforge-data:   SQLite databases       │   │
│  │  wfforge-broker: Filesystem broker      │   │
│  └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

### Services

1. **api** (wfforge-api)
   - FastAPI web server
   - Exposed on port 8000
   - Auto-initializes database on startup
   - Health check enabled

2. **worker** (wfforge-worker)
   - Celery worker for task processing
   - Uses filesystem broker (no Redis!)
   - Processes workflow tasks

3. **scheduler** (wfforge-scheduler)
   - Celery Beat for scheduled tasks
   - SQLite-based schedule persistence
   - Runs cron-based workflows

### Volumes

- **wfforge-data**: Persistent storage for SQLite databases
  - `/app/data/workflows.db` - Workflow definitions
  - `/app/data/celery_results.db` - Task results

- **wfforge-broker**: Celery filesystem broker
  - `/app/celery_broker/` - Message queue
  - `/app/celery_broker/out/` - Outgoing messages
  - `/app/celery_broker/processed/` - Processed messages

## Docker Commands

### Build

```bash
# Build the image
docker-compose build

# Build with no cache (clean build)
docker-compose build --no-cache

# Build specific service
docker-compose build api
```

### Run

```bash
# Start all services in background
docker-compose up -d

# Start with build
docker-compose up -d --build

# Start and view logs
docker-compose up

# Start specific service
docker-compose up -d api
```

### Logs

```bash
# View all logs
docker-compose logs

# Follow logs (real-time)
docker-compose logs -f

# Logs for specific service
docker-compose logs -f worker

# Last 100 lines
docker-compose logs --tail=100
```

### Status & Inspect

```bash
# Check running services
docker-compose ps

# View resource usage
docker stats

# Execute command in container
docker-compose exec api bash

# View API container details
docker inspect wfforge-api
```

### Stop & Clean

```bash
# Stop services (keeps data)
docker-compose stop

# Stop and remove containers (keeps data)
docker-compose down

# Remove containers and volumes (deletes all data!)
docker-compose down -v

# Remove containers, volumes, and images
docker-compose down -v --rmi all
```

## Configuration

### Environment Variables

The docker-compose.yml includes default environment variables. To customize:

1. **Option 1**: Edit docker-compose.yml directly
2. **Option 2**: Create .env file

```bash
# Copy example
cp .env.docker .env

# Edit configuration
nano .env
```

### Custom Configuration

```yaml
# docker-compose.override.yml (optional)
version: '3.8'

services:
  api:
    ports:
      - "8080:8000"  # Custom port
    environment:
      - DEBUG=true    # Enable debug mode
```

## Data Persistence

### Backup Data

```bash
# Stop services
docker-compose stop

# Backup volumes
docker run --rm \
  -v wfforge-data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/wfforge-data-$(date +%Y%m%d).tar.gz -C /data .

docker run --rm \
  -v wfforge-broker:/broker \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/wfforge-broker-$(date +%Y%m%d).tar.gz -C /broker .

# Restart services
docker-compose start
```

### Restore Data

```bash
# Stop services
docker-compose down

# Restore volume
docker run --rm \
  -v wfforge-data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar xzf /backup/wfforge-data-YYYYMMDD.tar.gz -C /data

# Restart
docker-compose up -d
```

### Access Database Directly

```bash
# SQLite shell access
docker-compose exec api sqlite3 /app/data/workflows.db

# Example queries
docker-compose exec api sqlite3 /app/data/workflows.db "SELECT * FROM workflows;"
```

## Development with Docker

### Live Code Reload

For development, mount source code as volume:

```yaml
# docker-compose.dev.yml
services:
  api:
    volumes:
      - ./src:/app/src  # Mount source code
    command: uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

```bash
# Run with dev config
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### Debug Container

```bash
# Shell into running container
docker-compose exec api bash

# Or start a one-off container
docker-compose run --rm api bash
```

## Production Deployment

### Best Practices

1. **Change default secrets**:
```yaml
environment:
  - SECRET_KEY=your-production-secret-key
  - API_KEY=your-production-api-key
```

2. **Use specific image tags** (not latest):
```yaml
image: wfforge:1.0.0
```

3. **Set resource limits**:
```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

4. **Enable health checks** (already configured):
```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
  interval: 30s
  timeout: 10s
  retries: 3
```

5. **Use Docker secrets** for sensitive data:
```bash
echo "my-secret-key" | docker secret create secret_key -
```

### Deploy to Production

```bash
# Build production image
docker-compose build --no-cache

# Start in production mode
docker-compose up -d

# Monitor
docker-compose logs -f

# Check health
curl http://localhost:8000/health
```

## Scaling

### Scale Workers

```bash
# Run 3 worker instances
docker-compose up -d --scale worker=3

# Check all workers
docker-compose ps worker
```

**Note**: Only scale workers, not API or scheduler (scheduler should be single instance).

## Troubleshooting

### Services Won't Start

```bash
# Check logs
docker-compose logs api
docker-compose logs worker
docker-compose logs scheduler

# Rebuild and restart
docker-compose down
docker-compose up -d --build
```

### Permission Issues

```bash
# Fix volume permissions
docker-compose down
docker volume rm wfforge-data wfforge-broker
docker-compose up -d
```

### Database Locked

```bash
# Stop all services
docker-compose stop

# Start only API
docker-compose up -d api

# Then start others
docker-compose up -d worker scheduler
```

### High Memory Usage

```bash
# Check resource usage
docker stats

# Add memory limits in docker-compose.yml
```

### Network Issues

```bash
# Recreate network
docker-compose down
docker network prune
docker-compose up -d
```

## Monitoring

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# Docker health status
docker-compose ps
```

### Logs

```bash
# Real-time logs
docker-compose logs -f

# Errors only
docker-compose logs | grep ERROR

# Specific service
docker-compose logs -f worker
```

### Resource Usage

```bash
# CPU and memory
docker stats --no-stream

# Disk usage
docker system df

# Volume sizes
docker volume ls
```

## Docker Image Details

### Image Layers

- **Base**: python:3.11-slim
- **Size**: ~200MB (optimized multi-stage build)
- **User**: Non-root user (wfforge:1000)
- **Exposed Port**: 8000

### Security

- ✅ Multi-stage build (smaller image)
- ✅ Non-root user
- ✅ Minimal base image (slim)
- ✅ No unnecessary packages
- ✅ Health checks enabled

## FAQ

### Q: Can I use a different port?

Yes, edit docker-compose.yml:
```yaml
ports:
  - "8080:8000"  # Host:Container
```

### Q: How do I update to a new version?

```bash
git pull
docker-compose down
docker-compose up -d --build
```

### Q: Where is my data stored?

```bash
# Find volume location
docker volume inspect wfforge-data
docker volume inspect wfforge-broker
```

### Q: Can I use this with Kubernetes?

Yes! Convert docker-compose.yml to Kubernetes manifests:
```bash
# Install kompose
curl -L https://github.com/kubernetes/kompose/releases/download/v1.31.2/kompose-linux-amd64 -o kompose

# Convert
./kompose convert -f docker-compose.yml
```

### Q: How do I view the SQLite database?

```bash
# Shell into container
docker-compose exec api bash

# Run sqlite3
sqlite3 /app/data/workflows.db

# Or from host (if sqlite3 installed)
docker cp wfforge-api:/app/data/workflows.db ./workflows.db
sqlite3 workflows.db
```

## Summary

WFForge Docker deployment provides:
- ✅ **One-command deployment** - `docker-compose up -d`
- ✅ **Zero external dependencies** - No Redis, no PostgreSQL
- ✅ **Persistent data** - Named volumes for databases
- ✅ **Multi-service architecture** - API, Worker, Scheduler
- ✅ **Production-ready** - Health checks, restart policies
- ✅ **Easy scaling** - Scale workers as needed
- ✅ **Small image size** - ~200MB optimized build

Perfect for both development and production deployments!
