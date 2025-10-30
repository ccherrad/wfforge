from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime


class Node(BaseModel):
    id: str
    type: str = "processing"
    position: Dict[str, float]
    data: Dict[str, Any]
    label: str


class Edge(BaseModel):
    id: str
    source: str
    target: str
    sourceHandle: Optional[str] = None
    targetHandle: Optional[str] = None


class WorkflowDefinition(BaseModel):
    nodes: List[Node]
    edges: List[Edge]


class WorkflowBase(BaseModel):
    name: str
    description: Optional[str] = None
    status: str = "EDIT"
    draft: bool = True
    crontab_expression: Optional[str] = None


class WorkflowCreate(WorkflowBase):
    definition: Optional[WorkflowDefinition] = None


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    draft: Optional[bool] = None
    definition: Optional[WorkflowDefinition] = None
    crontab_expression: Optional[str] = None


class WorkflowOut(WorkflowBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkflowDetails(WorkflowOut):
    definition: Optional[WorkflowDefinition] = None
    pipeline: Optional[Dict[str, Any]] = None
    last_run_at: Optional[datetime] = None


class WorkflowsPagination(BaseModel):
    items: List[WorkflowOut]
    total: int
    page: int
    size: int
    pages: int