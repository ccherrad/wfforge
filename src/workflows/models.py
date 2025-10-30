from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Boolean
from sqlalchemy.sql import func
from sqlalchemy.ext.mutable import MutableDict

from src.database import Base


class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="EDIT")  # EDIT, ACTIVE
    draft = Column(Boolean, default=True)
    definition = Column(MutableDict.as_mutable(JSON), nullable=True)  # VueFlow definition
    pipeline = Column(MutableDict.as_mutable(JSON), nullable=True)  # Celery pipeline
    crontab_expression = Column(String(100), nullable=True)  # For scheduled workflows
    last_run_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())