from typing import List
import sqlite3
from fastapi import HTTPException, status, UploadFile, File, Depends
from celery import Signature

from .models import Workflow
from . import services
from src.database import get_db


class WorkflowFile:
    def __init__(self, file: UploadFile, metadata: dict = None):
        self.file = file
        self.metadata = metadata or {}


async def get_file(file: UploadFile = File(...)):
    return WorkflowFile(file)


async def get_files(files: List[UploadFile] = File(...)):
    return [WorkflowFile(file) for file in files]


async def get_pipeline(workflow: Workflow) -> Signature:
    if not workflow.pipeline:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workflow has no pipeline defined",
        )
    return workflow.pipeline


def get_workflow(workflow_id: int, conn: sqlite3.Connection = Depends(get_db)) -> Workflow:
    workflow = services.get_workflow_by_id(conn, workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found"
        )
    return workflow
