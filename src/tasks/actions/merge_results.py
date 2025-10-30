from celery import shared_task
import structlog

logger = structlog.get_logger(__name__)


@shared_task(bind=True)
def merge_results(self, results_list):
    """
    Merge multiple results into a single output

    Args:
        results_list: List of results to merge

    Returns:
        Merged result
    """
    logger.info("Merging results", task_id=self.request.id, count=len(results_list))

    # Simple merge implementation (placeholder)
    merged_result = {
        "merged_from": len(results_list),
        "results": results_list,
        "summary": f"Merged {len(results_list)} results"
    }

    logger.info("Results merged", result=merged_result)
    return merged_result