# Migration Guide: SQLAlchemy to Native SQLite

This guide documents the migration from SQLAlchemy ORM to native SQLite3 implementation.

## What Changed

### 1. **Removed Dependencies**
- ❌ `sqlalchemy` - Removed ORM dependency
- ❌ `alembic` - No longer needed for migrations
- ✅ Native Python `sqlite3` module (built-in)

### 2. **Database Auto-Initialization**
- **Before**: Required running `alembic upgrade head` or manual table creation
- **After**: Tables are automatically created on first import of `src.database`
- The database initializes itself when the application starts - no manual setup required!

### 3. **SQLite for Celery Beat**
- **Before**: Celery Beat used file-based or Redis scheduler
- **After**: Celery Beat now uses SQLite database for schedule persistence
- Configuration: `beat_dburi=f"sqlite:///{db.db_path}"`

### 4. **Architecture Changes**

#### Database Module (`src/database.py`)
```python
# Old (SQLAlchemy)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(database_url)
SessionLocal = sessionmaker(bind=engine)

# New (Native SQLite)
import sqlite3
from contextlib import contextmanager

class Database:
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        yield conn
        conn.close()
```

#### Models (`src/workflows/models.py`)
```python
# Old (SQLAlchemy)
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

class Workflow(Base):
    __tablename__ = "workflows"
    id = Column(Integer, primary_key=True)
    name = Column(String(255))

# New (Dataclass)
from dataclasses import dataclass

@dataclass
class Workflow:
    id: Optional[int] = None
    name: str = ""

    @classmethod
    def from_db_row(cls, row):
        return cls(id=row["id"], name=row["name"])
```

#### Services (`src/workflows/services.py`)
```python
# Old (SQLAlchemy)
def create_workflow(session: Session, **kwargs):
    workflow = Workflow(**kwargs)
    session.add(workflow)
    session.commit()
    return workflow

# New (Native SQLite)
def create_workflow(conn: sqlite3.Connection, **kwargs):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO workflows (name) VALUES (?)",
        (kwargs.get("name"),)
    )
    conn.commit()
    return Workflow.from_db_row(cursor.fetchone())
```

#### API Routes (`src/workflows/router.py`)
```python
# Old (SQLAlchemy)
from sqlalchemy.orm import Session

@router.get("/")
def get_workflows(session: Session = Depends(get_db)):
    return services.get_workflows(session)

# New (Native SQLite)
import sqlite3

@router.get("/")
def get_workflows(conn: sqlite3.Connection = Depends(get_db)):
    return services.get_workflows(conn)
```

## JSON Support

SQLite's native JSON support is fully utilized:
- JSON columns store workflow definitions and pipelines as TEXT
- Serialization/deserialization handled by helper functions:
  - `serialize_json()` - Python → JSON string
  - `deserialize_json()` - JSON string → Python

```python
# JSON is stored as TEXT in SQLite
definition TEXT,  # Stores VueFlow definition as JSON
pipeline TEXT,    # Stores Celery pipeline as JSON
```

## Celery Beat Integration

The scheduler now uses SQLite for persistence:

```python
# src/tasks/scheduler.py
celery_app.conf.update(
    beat_dburi=f"sqlite:///{db.db_path}",
    beat_schedule_filename=None,
)
```

**Celery Beat Tables Created:**
- `celery_periodic_task` - Scheduled tasks
- `celery_crontab_schedule` - Crontab schedules
- `celery_interval_schedule` - Interval schedules
- `celery_periodic_task_schedule` - Links tasks to schedules

## Benefits

1. **Zero Configuration**: Database tables created automatically on startup
2. **Fewer Dependencies**: Removed SQLAlchemy and Alembic (~10 fewer packages)
3. **Better Performance**: Direct SQLite queries are faster than ORM
4. **Simpler Codebase**: More readable, less "magic"
5. **Single Database**: Workflows and Celery schedules in one SQLite file
6. **No Migrations**: Schema changes are immediate, no migration scripts needed

## Installation

```bash
# Old requirements
pip install sqlalchemy alembic

# New requirements (SQLite3 is built into Python)
# No additional packages needed!
```

## Running the Application

```bash
# Start the API server (database auto-initializes)
python -m src.main

# Or use uvicorn directly
uvicorn src.main:app --reload

# Start Celery worker
celery -A src.tasks.worker worker --loglevel=info

# Start Celery Beat scheduler (with SQLite backend)
celery -A src.tasks.scheduler beat --loglevel=info
```

## Database Location

Default: `./workflows.db`

Configure via environment variable:
```bash
DATABASE_URL=sqlite:///./my_workflows.db
```

## Backward Compatibility

⚠️ **Breaking Change**: Existing SQLAlchemy-based databases need migration.

To migrate existing data:
1. Export data from old database
2. Delete old database file
3. Start new application (creates new schema automatically)
4. Import data via API endpoints

## Testing

Run the database verification script:
```bash
python scripts/init_db.py
```

Expected output:
```
Initializing database...
Database path: ./workflows.db

Existing tables:
  - celery_crontab_schedule
  - celery_interval_schedule
  - celery_periodic_task
  - celery_periodic_task_schedule
  - workflows

Database initialization verified successfully!
```

## Troubleshooting

### Issue: "Table already exists" error
**Solution**: This shouldn't happen. If it does, check for conflicting database files.

### Issue: "No such table" error
**Solution**: Ensure you're importing `from src.database import db` before using database functions.

### Issue: JSON deserialization errors
**Solution**: Ensure JSON fields are properly serialized using `serialize_json()` before storing.

## API Changes

No API endpoint changes! All REST endpoints remain the same:
- `POST /api/v1/workflows/` - Create workflow
- `GET /api/v1/workflows/` - List workflows
- `GET /api/v1/workflows/{id}` - Get workflow
- `PUT /api/v1/workflows/{id}` - Update workflow
- `DELETE /api/v1/workflows/{id}` - Delete workflow
- `POST /api/v1/workflows/{id}/push-document` - Execute workflow
- `POST /api/v1/workflows/{id}/push-documents` - Execute workflow with multiple files
- `POST /api/v1/workflows/{id}/push-message` - Execute workflow with message

## Summary

This migration removes the SQLAlchemy ORM layer in favor of direct SQLite3 operations, providing:
- ✅ Automatic database initialization
- ✅ Reduced dependencies
- ✅ Better performance
- ✅ SQLite backend for Celery Beat
- ✅ Full JSON support maintained
- ✅ Simpler, more maintainable code

The application is now lighter, faster, and easier to deploy!
