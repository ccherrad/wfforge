from celery import shared_task
import structlog

logger = structlog.get_logger(__name__)


@shared_task(bind=True)
def router(self, item_data, routes=None):
    """
    Route data based on conditions in a WorkflowItem.

    Args:
        item_data: Dict representation of a WorkflowItem
        routes: List of route configurations with conditions and branches
                Example: [
                    {
                        "name": "route_a",
                        "condition": {"field": "status", "operator": "equals", "value": "active"},
                        "branch": <celery_signature>
                    }
                ]

    Returns:
        Dict: WorkflowItem with routing metadata added
    """
    logger.info("Routing data", task_id=self.request.id, route_count=len(routes or []))

    routes = routes or []
    json_data = item_data.get("json", {})
    metadata = item_data.get("metadata", {})

    # Evaluate conditions and find matching route
    matched_route = None
    for idx, route in enumerate(routes):
        condition = route.get("condition", {})
        route_name = route.get("name", f"route_{idx}")

        if _evaluate_condition(json_data, condition):
            logger.info("Condition matched",
                       route_name=route_name,
                       condition=condition)
            matched_route = route
            break

    # Add routing metadata to item
    result = {
        **item_data,
        "metadata": {
            **metadata,
            "routed_by": "router",
            "task_id": self.request.id,
            "matched_route": matched_route.get("name") if matched_route else "default",
            "total_routes_checked": len(routes)
        }
    }

    # If a route matched and has a branch, execute it
    # Note: In Celery chains, we return the data, not the AsyncResult
    if matched_route and matched_route.get("branch"):
        logger.info("Executing matched branch",
                   route=matched_route.get("name"))
        # The branch should be handled in the workflow definition
        # Here we just mark which route was matched
        result["json"]["__route__"] = matched_route.get("name")

    logger.info("Routing completed",
               matched=matched_route.get("name") if matched_route else None)
    return result


def _evaluate_condition(data, condition):
    """
    Evaluate a condition against JSON data.

    Supported operators:
    - equals: Field equals value
    - not_equals: Field not equals value
    - contains: String/list contains value
    - greater_than: Field > value
    - less_than: Field < value
    - exists: Field exists in data

    Args:
        data: JSON data dict to evaluate
        condition: Condition dict with field, operator, value

    Returns:
        Boolean indicating if condition matches
    """
    if not condition:
        return True  # Empty condition always matches

    field = condition.get("field")
    operator = condition.get("operator", "equals")
    expected_value = condition.get("value")

    # Get field value from data (supports nested fields with dot notation)
    field_value = data
    if field:
        for key in field.split("."):
            if isinstance(field_value, dict):
                field_value = field_value.get(key)
            else:
                return False

    # Evaluate based on operator
    if operator == "equals":
        return field_value == expected_value
    elif operator == "not_equals":
        return field_value != expected_value
    elif operator == "contains":
        if isinstance(field_value, (list, str)):
            return expected_value in field_value
        return False
    elif operator == "greater_than":
        try:
            return float(field_value) > float(expected_value)
        except (ValueError, TypeError):
            return False
    elif operator == "less_than":
        try:
            return float(field_value) < float(expected_value)
        except (ValueError, TypeError):
            return False
    elif operator == "exists":
        return field_value is not None
    else:
        logger.warning("Unknown operator", operator=operator)
        return False