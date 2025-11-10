from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class Workflow:
    """Workflow model representing a workflow in the database"""

    id: Optional[int] = None
    name: str = ""
    description: Optional[str] = None
    status: str = "EDIT"  # EDIT, ACTIVE
    draft: bool = True
    definition: Optional[Dict[str, Any]] = None  # VueFlow definition (JSON)
    pipeline: Optional[Dict[str, Any]] = None  # Celery pipeline (JSON)
    crontab_expression: Optional[str] = None
    last_run_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_db_row(cls, row) -> "Workflow":
        """Create a Workflow instance from a database row"""
        from src.database import deserialize_json, deserialize_datetime

        return cls(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            status=row["status"],
            draft=bool(row["draft"]),
            definition=deserialize_json(row["definition"]),
            pipeline=deserialize_json(row["pipeline"]),
            crontab_expression=row["crontab_expression"],
            last_run_at=deserialize_datetime(row["last_run_at"]),
            created_at=deserialize_datetime(row["created_at"]),
            updated_at=deserialize_datetime(row["updated_at"]),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert Workflow to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "draft": self.draft,
            "definition": self.definition,
            "pipeline": self.pipeline,
            "crontab_expression": self.crontab_expression,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
