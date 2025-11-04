from celery import shared_task
import structlog
from datetime import datetime

logger = structlog.get_logger(__name__)


@shared_task(bind=True)
def call_agent(self, item_data, agent_config=None):
    """
    Call an AI agent with input data from a WorkflowItem.

    Args:
        item_data: Dict representation of a WorkflowItem with structure:
            {
                "json": {...},           # Main data payload
                "binary": {...},         # Optional binary data
                "metadata": {...},       # Item metadata
                "paired_item": int       # Source item index
            }
        agent_config: Optional agent configuration dict

    Returns:
        Dict: Updated WorkflowItem with agent response
    """
    logger.info("Calling AI agent",
                task_id=self.request.id,
                agent_config=agent_config)

    # Extract data from WorkflowItem
    json_data = item_data.get("json", {})
    binary_data = item_data.get("binary", {})
    metadata = item_data.get("metadata", {})

    # Placeholder agent implementation
    # In a real implementation, you would:
    # 1. Extract text from json_data or binary files
    # 2. Call your AI agent API (OpenAI, Anthropic, etc.)
    # 3. Process the response

    agent_input = json_data.get("text") or str(json_data)

    # Simulate agent processing
    agent_response = {
        "original_input": agent_input,
        "agent_output": f"Processed by AI agent: {agent_input[:100]}...",
        "agent_config": agent_config or {},
        "timestamp": datetime.utcnow().isoformat(),
        "tokens_used": len(agent_input) // 4  # Rough estimate
    }

    # Add agent response to json data
    result_json = {
        **json_data,
        "agent_response": agent_response,
        "processed_by_agent": True
    }

    # Return updated WorkflowItem
    result = {
        "json": result_json,
        "binary": binary_data,
        "metadata": {
            **metadata,
            "processed_by": "call_agent",
            "task_id": self.request.id,
            "agent_config": agent_config
        },
        "paired_item": item_data.get("paired_item")
    }

    logger.info("Agent call completed",
                task_id=self.request.id,
                tokens_used=agent_response["tokens_used"])
    return result