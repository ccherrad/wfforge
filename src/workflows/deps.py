from typing import List
from fastapi import HTTPException, status, UploadFile, File, Depends
from sqlalchemy.orm import Session
from celery import Signature

from .models import Workflow
from src.database import get_db


class WorkflowFile:
    def __init__(self, file: UploadFile, metadata: dict = None):
        self.file = file
        self.metadata = metadata or {}


async def get_file(file: UploadFile = File(...)):
    return WorkflowFile(file)


async def get_files(files: List[UploadFile] = File(...)):
    return [WorkflowFile(file) for file in files]


def get_workflow(workflow_id: int, session: Session = Depends(get_db)) -> Workflow:
    workflow = session.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found"
        )
    return workflow


def get_pipeline(workflow: Workflow = Depends(get_workflow)) -> Signature:
    if not workflow.pipeline:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workflow has no pipeline defined"
        )
    return workflow.pipeline