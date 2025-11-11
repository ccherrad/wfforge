from typing import List
import sqlite3
from fastapi import APIRouter, Depends, status, Request, HTTPException

from celery import group, signature

from .models import Workflow
from .schemas import (
    WorkflowOut,
    WorkflowDetails,
    WorkflowCreate,
    WorkflowUpdate,
    WorkflowsPagination,
)
from . import services
from .deps import (
    get_file,
    get_files,
    get_pipeline,
    WorkflowFile,
    get_workflow,
)
from src.database import get_db

router = APIRouter(prefix="/workflows", tags=["Workflows"])


@router.post(
    "/",
    response_model=WorkflowOut,
    status_code=status.HTTP_201_CREATED,
)
def create_workflow(
    workflow_create: WorkflowCreate,
    conn: sqlite3.Connection = Depends(get_db),
):
    return services.create_workflow(conn, **workflow_create.model_dump())


@router.get(
    "/",
    response_model=List[WorkflowOut],
    status_code=status.HTTP_200_OK,
)
def get_workflows(
    conn: sqlite3.Connection = Depends(get_db),
):
    return services.get_workflows(conn)


@router.get(
    "/{workflow_id}",
    response_model=WorkflowDetails,
    status_code=status.HTTP_200_OK,
)
def get_workflow(
    workflow_id: int,
    conn: sqlite3.Connection = Depends(get_db),
):
    workflow = services.get_workflow_by_id(conn, workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found"
        )
    return workflow


@router.put(
    "/{workflow_id}",
    response_model=WorkflowOut,
)
def update_workflow(
    workflow_update: WorkflowUpdate,
    workflow: Workflow = Depends(get_workflow),
    conn: sqlite3.Connection = Depends(get_db),
):
    workflow = services.update_workflow(conn, workflow.id, **workflow_update.model_dump(exclude_unset=True))
    return workflow


@router.delete(
    "/{workflow_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_workflow(
    workflow: Workflow = Depends(get_workflow),
    conn: sqlite3.Connection = Depends(get_db),
):
    services.delete_workflow(conn, workflow.id)
    return None


@router.post(
    "/{workflow_id}/push-document",
    status_code=status.HTTP_202_ACCEPTED,
)
async def push_document(
    workflow: Workflow = Depends(get_workflow),
    workflow_file: WorkflowFile = Depends(get_file),
):
    # Get pipeline from workflow
    workflow_pipeline_dict = await get_pipeline(workflow)
    # Convert pipeline dict back to Celery signature
    pipeline = signature(workflow_pipeline_dict)
    pipeline.apply_async(args=(workflow_file,))
    return {"message": "Document pushed successfully. Task queued for execution."}


@router.post(
    "/{workflow_id}/push-documents",
    status_code=status.HTTP_202_ACCEPTED,
)
async def push_documents(
    workflow: Workflow = Depends(get_workflow),
    workflow_files: List[WorkflowFile] = Depends(get_files),
):
    # Get pipeline from workflow
    workflow_pipeline_dict = await get_pipeline(workflow)
    pipelines = []
    for wf_file in workflow_files:
        # Convert pipeline dict back to Celery signature for each file
        pipeline = signature(workflow_pipeline_dict)
        pipelines.append(pipeline.clone(args=(wf_file,)))
    group(pipelines).apply_async()
    return {"message": "Documents pushed successfully. Tasks queued for execution."}


@router.post(
    "/{workflow_id}/push-message",
    status_code=status.HTTP_202_ACCEPTED,
)
async def push_message(
    request: Request,
    workflow_id: int,
    conn: sqlite3.Connection = Depends(get_db),
):
    workflow = services.get_workflow_by_id(conn, workflow_id)
    workflow_pipeline_dict = await get_pipeline(workflow)
    message = await request.json()
    # Convert pipeline dict back to Celery signature
    pipeline = signature(workflow_pipeline_dict)
    pipeline.apply_async(args=(message,))
    return {"message": "Message pushed successfully. Task queued for execution."}
