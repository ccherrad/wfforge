from typing import List
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, status, Request, HTTPException

from celery import group, Signature

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
    get_workflow_item,
    get_workflow_input,
    get_pipeline,
    get_workflow,
)
from .items import WorkflowItem, WorkflowInput
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
    workflow_pipeline: Signature = Depends(get_pipeline),
    workflow_item: WorkflowItem = Depends(get_workflow_item),
):
    """
    Execute workflow with a single file upload.

    The file is converted to a WorkflowItem with:
    - json: File metadata (name, size, content_type)
    - binary: Base64-encoded file content
    - metadata: Upload timestamp and source info
    """
    # Convert WorkflowItem to dict for JSON serialization
    workflow_pipeline.apply_async(args=(workflow_item.model_dump(),))
    return {
        "message": "Document pushed successfully.",
        "item": {
            "file_name": workflow_item.json.get("file_name"),
            "size": workflow_item.json.get("size")
        }
    }


@router.post(
    "/{workflow_id}/push-documents",
    status_code=status.HTTP_202_ACCEPTED,
)
async def push_documents(
    workflow_pipeline: Signature = Depends(get_pipeline),
    workflow_input: WorkflowInput = Depends(get_workflow_input),
):
    """
    Execute workflow with multiple file uploads.

    Each file is converted to a separate WorkflowItem, and the workflow
    is executed in parallel for each item using Celery groups.
    """
    pipelines = []
    for item in workflow_input.items:
        pipeline = workflow_pipeline.clone()
        # Pass the item dict to the first task
        pipeline.tasks[0].update(args=(item.model_dump(),))
        pipelines.append(pipeline)

    group(pipelines).apply_async()

    return {
        "message": "Documents pushed successfully.",
        "count": len(workflow_input.items),
        "items": [
            {
                "file_name": item.json.get("file_name"),
                "size": item.json.get("size")
            }
            for item in workflow_input.items
        ]
    }


@router.post(
    "/{workflow_id}/push-message",
    status_code=status.HTTP_202_ACCEPTED,
)
async def push_message(
    request: Request,
    workflow: Workflow = Depends(get_workflow),
):
    """
    Execute workflow with generic JSON data.

    Accepts any JSON structure:
    - Single object: Wrapped in one WorkflowItem
    - Array of objects: Each becomes a separate WorkflowItem
    - Primitive values: Wrapped in WorkflowItem.json

    The JSON data is automatically converted to the standardized WorkflowItem format.
    """
    if not workflow.pipeline:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workflow has no pipeline defined"
        )

    body = await request.json()

    # Handle different JSON input types
    if isinstance(body, list):
        # Array of items - create WorkflowInput
        workflow_input = WorkflowInput.from_json_array(body)
        pipelines = []
        for item in workflow_input.items:
            pipeline = workflow.pipeline.clone()
            pipeline.tasks[0].update(args=(item.model_dump(),))
            pipelines.append(pipeline)
        group(pipelines).apply_async()

        return {
            "message": "Messages pushed successfully.",
            "count": len(workflow_input.items)
        }
    else:
        # Single item - create WorkflowItem
        workflow_item = WorkflowItem.from_json(body)
        workflow.pipeline.apply_async(args=(workflow_item.model_dump(),))

        return {
            "message": "Message pushed successfully.",
            "item_keys": list(workflow_item.json.keys())
        }