import sqlite3
import json
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, Dict, Any
import structlog

from .config import settings

logger = structlog.get_logger(__name__)

# Thread-local storage for database connections
_thread_local = threading.local()


class Database:
    """SQLite database manager with auto-initialization"""

    def __init__(self, db_path: str):
        # Extract path from SQLite URL format (sqlite:///./file.db -> ./file.db)
        if db_path.startswith("sqlite:///"):
            db_path = db_path.replace("sqlite:///", "")
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database and create tables if they don't exist"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Create workflows table with JSON support
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS workflows (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'EDIT',
                    draft BOOLEAN DEFAULT 1,
                    definition TEXT,
                    pipeline TEXT,
                    crontab_expression TEXT,
                    last_run_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Create index on id for faster lookups
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_workflows_id
                ON workflows(id)
                """
            )

            # Create Celery Beat schedule table for SQLite scheduler
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS celery_periodic_task (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    task TEXT NOT NULL,
                    args TEXT DEFAULT '[]',
                    kwargs TEXT DEFAULT '{}',
                    queue TEXT,
                    exchange TEXT,
                    routing_key TEXT,
                    priority INTEGER,
                    expires TEXT,
                    enabled BOOLEAN DEFAULT 1,
                    last_run_at TEXT,
                    total_run_count INTEGER DEFAULT 0,
                    date_changed TEXT DEFAULT CURRENT_TIMESTAMP,
                    description TEXT
                )
                """
            )

            # Create Celery Beat crontab schedule table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS celery_crontab_schedule (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    minute TEXT DEFAULT '*',
                    hour TEXT DEFAULT '*',
                    day_of_week TEXT DEFAULT '*',
                    day_of_month TEXT DEFAULT '*',
                    month_of_year TEXT DEFAULT '*',
                    timezone TEXT DEFAULT 'UTC'
                )
                """
            )

            # Create Celery Beat interval schedule table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS celery_interval_schedule (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    every INTEGER NOT NULL,
                    period TEXT NOT NULL
                )
                """
            )

            # Link periodic tasks to schedules
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS celery_periodic_task_schedule (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    periodic_task_id INTEGER NOT NULL,
                    crontab_id INTEGER,
                    interval_id INTEGER,
                    FOREIGN KEY (periodic_task_id) REFERENCES celery_periodic_task(id),
                    FOREIGN KEY (crontab_id) REFERENCES celery_crontab_schedule(id),
                    FOREIGN KEY (interval_id) REFERENCES celery_interval_schedule(id)
                )
                """
            )

            conn.commit()
            logger.info("Database initialized successfully", db_path=self.db_path)

    @contextmanager
    def get_connection(self):
        """Get a thread-safe database connection"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
        finally:
            conn.close()

    def dict_factory(self, cursor, row):
        """Convert sqlite3.Row to dict"""
        return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


# Global database instance
db = Database(settings.database_url)


def get_db():
    """Dependency for FastAPI to get database connection"""
    with db.get_connection() as conn:
        yield conn


# Helper functions for JSON serialization/deserialization
def serialize_json(data: Any) -> str:
    """Serialize Python object to JSON string for SQLite storage"""
    if data is None:
        return None
    return json.dumps(data)


def deserialize_json(data: str) -> Any:
    """Deserialize JSON string from SQLite to Python object"""
    if data is None or data == "":
        return None
    return json.loads(data)


# Helper functions for datetime
def serialize_datetime(dt: Optional[datetime]) -> Optional[str]:
    """Serialize datetime to ISO format string"""
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    return dt.isoformat()


def deserialize_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """Deserialize ISO format string to datetime"""
    if dt_str is None or dt_str == "":
        return None
    if isinstance(dt_str, datetime):
        return dt_str
    return datetime.fromisoformat(dt_str)
