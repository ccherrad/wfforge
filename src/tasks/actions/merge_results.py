from celery import shared_task
import structlog
from datetime import datetime

logger = structlog.get_logger(__name__)


@shared_task(bind=True)
def merge_results(self, results_list):
    """
    Merge multiple WorkflowItem results into a single WorkflowItem.

    Args:
        results_list: List of WorkflowItem dicts from parallel tasks

    Returns:
        Dict: A single merged WorkflowItem containing all results
    """
    logger.info("Merging results",
                task_id=self.request.id,
                count=len(results_list))

    if not results_list:
        return {
            "json": {"error": "No results to merge"},
            "metadata": {"merged_count": 0}
        }

    # Collect all JSON data from results
    merged_json_items = []
    all_binary = {}
    all_metadata = {}

    for idx, result in enumerate(results_list):
        if isinstance(result, dict):
            # Extract WorkflowItem components
            json_data = result.get("json", {})
            binary_data = result.get("binary", {})
            metadata = result.get("metadata", {})

            # Add to merged collections
            merged_json_items.append({
                "item_index": idx,
                **json_data
            })

            # Merge binary data with prefixed keys to avoid collisions
            if binary_data:
                for key, value in binary_data.items():
                    all_binary[f"item_{idx}_{key}"] = value

            # Track metadata
            all_metadata[f"item_{idx}"] = metadata

    # Create merged WorkflowItem
    merged_result = {
        "json": {
            "merged_count": len(results_list),
            "items": merged_json_items,
            "summary": f"Merged {len(results_list)} workflow items",
            "merge_timestamp": datetime.utcnow().isoformat()
        },
        "binary": all_binary if all_binary else None,
        "metadata": {
            "merged_from": len(results_list),
            "source_metadata": all_metadata,
            "processed_by": "merge_results",
            "task_id": self.request.id
        },
        "paired_item": None  # Merged items don't have single source
    }

    logger.info("Results merged successfully",
                task_id=self.request.id,
                merged_count=len(results_list),
                binary_items=len(all_binary))

    return merged_result