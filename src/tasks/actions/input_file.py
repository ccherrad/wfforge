from celery import shared_task
import structlog

logger = structlog.get_logger(__name__)


@shared_task(bind=True)
def input_file(self, file_data):
    """
    Process an input file

    Args:
        file_data: File data object containing file and metadata

    Returns:
        Processed file data
    """
    logger.info("Processing input file", task_id=self.request.id)

    # Extract file information
    file = file_data.file
    metadata = file_data.metadata

    # Process the file (placeholder implementation)
    result = {
        "filename": file.filename,
        "content_type": file.content_type,
        "size": len(file.file.read()) if hasattr(file.file, 'read') else 0,
        "metadata": metadata,
        "processed": True
    }

    logger.info("Input file processed", result=result)
    return result