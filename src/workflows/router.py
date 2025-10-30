from typing import List
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, status, Request, HTTPException

from celery import group

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
    session: Session = Depends(get_db),
):
    return services.create_workflow(session, **workflow_create.dict())


@router.get(
    "/",
    response_model=List[WorkflowOut],
    status_code=status.HTTP_200_OK,
)
def get_workflows(
    session: Session = Depends(get_db),
):
    return services.get_workflows(session)


@router.get(
    "/{workflow_id}",
    response_model=WorkflowDetails,
    status_code=status.HTTP_200_OK,
)
def get_workflow(
    workflow_id: int,
    session: Session = Depends(get_db),
):
    workflow = services.get_workflow_by_id(session, workflow_id)
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
    session: Session = Depends(get_db),
):
    workflow = services.update_workflow(session, workflow.id, **workflow_update.dict())
    return workflow


@router.delete(
    "/{workflow_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_workflow(
    workflow: Workflow = Depends(get_workflow),
    session: Session = Depends(get_db),
):
    services.delete_workflow(session, workflow.id)
    return None


@router.post(
    "/{workflow_id}/push-document",
    status_code=status.HTTP_202_ACCEPTED,
)
async def push_document(
    workflow_pipeline: dict = Depends(get_pipeline),
    workflow_file: WorkflowFile = Depends(get_file),
):
    # Convert pipeline dict back to Celery signature
    pipeline = workflow_pipeline
    pipeline.apply_async(args=(workflow_file,))
    return {"message": "Document pushed successfully."}


@router.post(
    "/{workflow_id}/push-documents",
    status_code=status.HTTP_202_ACCEPTED,
)
async def push_documents(
    workflow_pipeline: dict = Depends(get_pipeline),
    workflow_files: List[WorkflowFile] = Depends(get_files),
):
    pipelines = []
    for wf_file in workflow_files:
        pipeline = workflow_pipeline.clone()
        pipeline.tasks[0].update(args=(wf_file,))
        pipelines.append(pipeline)
    group(pipelines).apply_async()
    return {"message": "Documents pushed successfully."}


@router.post(
    "/{workflow_id}/push-message",
    status_code=status.HTTP_202_ACCEPTED,
)
async def push_message(
    request: Request,
    workflow_id: int,
    session: Session = Depends(get_db),
):
    workflow = services.get_workflow_by_id(session, workflow_id)
    workflow_pipeline = await get_pipeline(workflow)
    message = await request.json()
    workflow_pipeline.apply_async(args=(message,))
    return {"message": "Message pushed successfully."}