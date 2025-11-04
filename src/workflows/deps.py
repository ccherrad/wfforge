from typing import List
from fastapi import HTTPException, status, UploadFile, File, Depends
from sqlalchemy.orm import Session
from celery import Signature

from .models import Workflow
from .items import WorkflowItem, WorkflowInput
from src.database import get_db


async def get_workflow_item(file: UploadFile = File(...)) -> WorkflowItem:
    """
    Create a WorkflowItem from an uploaded file.

    This converts the file to a serialization-safe format with base64 encoding.
    """
    return await WorkflowItem.from_upload_file(file)


async def get_workflow_input(files: List[UploadFile] = File(...)) -> WorkflowInput:
    """
    Create a WorkflowInput from multiple uploaded files.

    Each file becomes a separate item in the workflow input.
    """
    return await WorkflowInput.from_files(files)


def get_workflow(workflow_id: int, session: Session = Depends(get_db)) -> Workflow:
    """Get a workflow by ID."""
    workflow = session.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found"
        )
    return workflow


def get_pipeline(workflow: Workflow = Depends(get_workflow)) -> Signature:
    """Get the Celery pipeline signature for a workflow."""
    if not workflow.pipeline:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workflow has no pipeline defined"
        )
    return workflow.pipeline