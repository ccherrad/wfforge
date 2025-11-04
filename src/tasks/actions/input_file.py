from celery import shared_task
import structlog
import base64

logger = structlog.get_logger(__name__)


@shared_task(bind=True)
def input_file(self, item_data):
    """
    Process an input file from a WorkflowItem.

    Args:
        item_data: Dict representation of a WorkflowItem with structure:
            {
                "json": {...},           # File metadata
                "binary": {...},         # Base64-encoded files
                "metadata": {...},       # Item metadata
                "paired_item": int       # Source item index
            }

    Returns:
        Dict: Updated WorkflowItem with processed file information
    """
    logger.info("Processing input file", task_id=self.request.id)

    # Extract data from WorkflowItem structure
    json_data = item_data.get("json", {})
    binary_data = item_data.get("binary", {})
    metadata = item_data.get("metadata", {})

    # Process binary files if present
    processed_files = {}
    if binary_data:
        for key, file_info in binary_data.items():
            # Get file details
            file_name = file_info.get("file_name", "unknown")
            mime_type = file_info.get("mime_type", "application/octet-stream")
            file_size = file_info.get("file_size", 0)

            # You can decode and process the file content here
            # file_content = base64.b64decode(file_info["data"])
            # ... process file_content ...

            processed_files[key] = {
                "file_name": file_name,
                "mime_type": mime_type,
                "size": file_size,
                "processed": True
            }

    # Update the json data with processing results
    result_json = {
        **json_data,
        "processed_files": processed_files,
        "processing_status": "completed",
        "task_id": self.request.id
    }

    # Return updated WorkflowItem
    result = {
        "json": result_json,
        "binary": binary_data,  # Keep original binary data
        "metadata": {
            **metadata,
            "processed_by": "input_file",
            "task_id": self.request.id
        },
        "paired_item": item_data.get("paired_item")
    }

    logger.info("Input file processed",
                file_count=len(processed_files),
                task_id=self.request.id)
    return result