# Redis Removal Guide: Filesystem Broker + SQLite Backend

This guide documents the removal of Redis dependency in favor of a fully file-based Celery setup using filesystem broker and SQLite result backend.

## What Changed

### 1. **Removed Redis Dependency**
- ❌ `redis` Python package - Removed from dependencies
- ❌ Redis server - No longer required
- ✅ **Zero external services needed** - Everything runs with built-in Python modules!

### 2. **New Celery Architecture**

#### Before (Redis-based):
```
Celery Worker → Redis (Broker) → Celery Worker
                ↓
            Redis (Results)
```

#### After (File-based):
```
Celery Worker → Filesystem (Broker) → Celery Worker
                ↓
            SQLite (Results)
```

### 3. **Configuration Changes**

#### Old Configuration (`src/config.py`):
```python
class Settings(BaseSettings):
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
```

#### New Configuration:
```python
class Settings(BaseSettings):
    # Celery filesystem broker
    celery_broker_url: str = "filesystem://"
    celery_broker_folder: str = "./celery_broker"
    celery_broker_processed_folder: str = "./celery_broker/processed"

    # SQLite result backend
    celery_result_backend: str = "db+sqlite:///./celery_results.db"
```

### 4. **Automatic Directory Creation**

The broker directories are automatically created when the config module loads:
```python
# Auto-created directories:
./celery_broker/           # Incoming messages
./celery_broker/out/       # Outgoing messages
./celery_broker/processed/ # Processed messages
```

## Celery Configuration Details

### Worker Configuration (`src/tasks/worker.py`):
```python
celery_app.conf.update(
    # Filesystem broker configuration
    broker_transport_options={
        "data_folder_in": settings.celery_broker_folder,
        "data_folder_out": settings.celery_broker_folder + "/out",
        "data_folder_processed": settings.celery_broker_processed_folder,
    },
    # SQLite result backend configuration
    result_backend_transport_options={
        "echo": False,  # Don't echo SQL queries
    },
)
```

### Scheduler Configuration (`src/tasks/scheduler.py`):
```python
celery_app.conf.update(
    beat_dburi=f"sqlite:///{db.db_path}",  # Beat schedule in SQLite
    beat_schedule_filename=None,
    # Same filesystem broker config as worker
    broker_transport_options={...},
    result_backend_transport_options={...},
)
```

## Benefits

### 1. **Zero External Dependencies**
- No Redis server to install, configure, or maintain
- No network ports to manage
- No connection pooling issues
- No Redis-specific errors

### 2. **Simplified Deployment**
```bash
# Before (with Redis)
sudo apt-get install redis-server
sudo systemctl start redis-server
pip install redis celery

# After (no Redis)
pip install celery
# That's it!
```

### 3. **File-Based Simplicity**
- Messages stored as files on disk
- Easy to inspect and debug
- Automatic cleanup of processed messages
- No memory limits (uses disk space)

### 4. **Single Storage Backend**
All application data in one place:
```
./workflows.db           # Workflow definitions
./celery_results.db      # Task results
./celery_broker/         # Message queue
```

### 5. **Better for Development**
- No external services to forget to start
- Works offline
- Easy to reset (just delete directories)
- Portable across environments

## Environment Configuration

### `.env.example`:
```bash
# Old (Redis)
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# New (Filesystem + SQLite)
CELERY_BROKER_URL=filesystem://
CELERY_BROKER_FOLDER=./celery_broker
CELERY_BROKER_PROCESSED_FOLDER=./celery_broker/processed
CELERY_RESULT_BACKEND=db+sqlite:///./celery_results.db
```

## Running the Application

```bash
# Start the API server
uvicorn src.main:app --reload

# Start Celery worker (no Redis needed!)
celery -A src.tasks.worker worker --loglevel=info

# Start Celery Beat scheduler (with SQLite persistence)
celery -A src.tasks.scheduler beat --loglevel=info
```

## How It Works

### Filesystem Broker

The filesystem broker stores messages as pickle files:

1. **Producer** writes task to `./celery_broker/` as a file
2. **Worker** reads file from `./celery_broker/`
3. **Worker** moves processed file to `./celery_broker/processed/`
4. **Cleanup** happens automatically based on retention settings

### SQLite Result Backend

Task results are stored in SQLite:

```sql
-- celery_results.db schema
CREATE TABLE celery_taskmeta (
    id INTEGER PRIMARY KEY,
    task_id VARCHAR(255) UNIQUE,
    status VARCHAR(50),
    result BLOB,
    date_done DATETIME,
    traceback TEXT
);
```

## Performance Considerations

### Filesystem Broker:
- ✅ **Good for**: Development, small-scale production, single-server deployments
- ✅ **Throughput**: Hundreds of tasks per second
- ⚠️ **Not ideal for**: Distributed systems (multiple servers)
- ⚠️ **Not ideal for**: Very high-volume (thousands of tasks/second)

### When to Use Redis Instead:
- Multiple Celery workers on different servers
- Very high message throughput (>1000 tasks/sec)
- Need for Redis-specific features (pub/sub, etc.)

### For Most Use Cases:
The filesystem broker is **perfect** for:
- Single-server deployments
- Development environments
- Small to medium workloads
- Workflows with moderate task volume

## Migration from Redis

If you have an existing Redis-based installation:

1. **Stop all workers and beat**:
```bash
# Stop Celery workers
pkill -f "celery worker"

# Stop Celery beat
pkill -f "celery beat"
```

2. **Update code** (already done in this commit)

3. **Update environment**:
```bash
# Edit .env file
nano .env

# Remove Redis settings, add filesystem settings
# (See .env.example)
```

4. **Clear old Redis data** (optional):
```bash
# Old tasks in Redis are abandoned
# They won't affect the new system
```

5. **Restart services**:
```bash
celery -A src.tasks.worker worker --loglevel=info
celery -A src.tasks.scheduler beat --loglevel=info
```

## Troubleshooting

### Issue: "FileNotFoundError: celery_broker"
**Solution**: The directories should auto-create. If not, create manually:
```bash
mkdir -p celery_broker/out celery_broker/processed
```

### Issue: "Permission denied" on broker folder
**Solution**: Ensure write permissions:
```bash
chmod -R 755 celery_broker
```

### Issue: Tasks not being processed
**Solution**: Check that worker is running and monitoring correct folder:
```bash
celery -A src.tasks.worker worker --loglevel=debug
```

### Issue: "Database is locked" on celery_results.db
**Solution**: SQLite handles this automatically with WAL mode. If issues persist:
```bash
# Delete and recreate
rm celery_results.db
# Celery will recreate it automatically
```

## Cleanup

The filesystem broker accumulates processed messages. To clean up:

```bash
# Manual cleanup
rm -rf celery_broker/processed/*

# Or configure automatic cleanup in Celery:
celery_app.conf.update(
    broker_transport_options={
        "data_folder_in": "./celery_broker",
        "data_folder_out": "./celery_broker/out",
        "data_folder_processed": "./celery_broker/processed",
        "store_processed": False,  # Don't keep processed messages
    }
)
```

## File Structure

```
wfforge/
├── workflows.db                  # Workflow definitions
├── celery_results.db            # Task results
├── celery_broker/               # Message queue
│   ├── {uuid}.msg              # Pending tasks
│   ├── out/                    # Outgoing messages
│   └── processed/              # Completed tasks
├── src/
│   ├── config.py               # Updated configuration
│   ├── tasks/
│   │   ├── worker.py          # Updated worker config
│   │   └── scheduler.py       # Updated scheduler config
│   └── ...
└── .env                        # No Redis config needed!
```

## Summary

This migration removes Redis entirely, replacing it with:
- ✅ **Filesystem broker** - Simple, file-based message queue
- ✅ **SQLite result backend** - Persistent task results
- ✅ **Zero external services** - Everything self-contained
- ✅ **Easier deployment** - No Redis to install or manage
- ✅ **Better for development** - Works offline, easy to debug

### Trade-offs:
| Feature | Redis | Filesystem |
|---------|-------|------------|
| External service | Required | None |
| Setup complexity | High | Low |
| Network dependency | Yes | No |
| Multi-server | Excellent | Limited |
| Throughput | Very High | Moderate |
| Debugging | Complex | Simple |
| Deployment | Complex | Simple |

**Verdict**: For single-server deployments and development, the filesystem broker is simpler, easier, and sufficient!

## Dependencies Removed

From `pyproject.toml`:
```toml
# Removed:
redis = "^5.0.1"

# Kept (no changes):
celery = "^5.3.4"  # Celery supports filesystem broker natively!
```

The application is now **completely self-contained** with no external service dependencies! 🎉
