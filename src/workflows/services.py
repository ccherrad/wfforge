from typing import List, Optional
import sqlite3
import structlog
from celery import chain, group, chord, signature
from datetime import datetime

from .models import Workflow
from src.database import serialize_json, deserialize_json, serialize_datetime

logger = structlog.get_logger(__name__)


def get_task_by_id(node_id, nodes):
    for node in nodes:
        if node["id"] == node_id:
            return node["task"]
    return None


# Build graph of task dependencies
def build_graph(nodes, edges):
    graph = {node["id"]: [] for node in nodes}
    for edge in edges:
        # Store both target and route index for router nodes
        route_index = None
        if edge.get("sourceHandle"):
            # Extract route index from sourceHandle (format: "nodeId-route-{index}")
            route_index = int(edge["sourceHandle"].split("-")[-1])
        graph[edge["source"]].append(
            {"target": edge["target"], "route_index": route_index}
        )
    return graph


def workflow_to_signature(definition, workflow_id):
    nodes = definition["nodes"]
    edges = definition["edges"]
    graph = build_graph(nodes, edges)

    def build_signature(node_id):
        outgoing_edges = graph.get(node_id, [])
        node = next((n for n in nodes if n["id"] == node_id), None)
        user_defined_name = node["label"]
        task_config = {k: v for k, v in node["data"].items() if k != "zodSchema"}
        task_config.update(node["data"].get("config", {}))
        task_config.pop("config", None)

        task_name = node["data"]["task_name"]

        # If it's a router node
        if task_name == "router":
            current_task = signature(
                task_name,
                kwargs=task_config,
                options={
                    "shadow": user_defined_name,
                    "headers": {
                        "workflow_id": workflow_id,
                    },
                },
            )

            routes = []
            for edge in outgoing_edges:
                route_index = edge.get("route_index")
                if route_index is not None:
                    routes.append(
                        {
                            "condition": task_config["conditions"][route_index],
                            "branch": build_signature(edge["target"]),
                        }
                    )

            task_config = {
                "task_name": "router",
                "task_type": "processing",
                "routes": routes,
            }

            return current_task.clone(kwargs=task_config)

        # If no outgoing edges, it's a final task
        if not outgoing_edges:
            return signature(
                task_name,
                kwargs=task_config,
                options={
                    "shadow": user_defined_name,
                    "headers": {
                        "workflow_id": workflow_id,
                    },
                },
            )

        # If there is only one outgoing edge, it's a chain
        elif len(outgoing_edges) == 1:
            current_task = signature(
                task_name,
                kwargs=task_config,
                options={
                    "shadow": user_defined_name,
                    "headers": {
                        "workflow_id": workflow_id,
                    },
                },
            )
            next_task = build_signature(outgoing_edges[0]["target"])
            return chain(current_task, next_task)

        # If there are multiple outgoing edges, it's either a group or a chord
        else:
            current_task = signature(
                task_name,
                kwargs=task_config,
                options={
                    "shadow": user_defined_name,
                    "headers": {
                        "workflow_id": workflow_id,
                    },
                },
            )
            parallel_tasks = [
                build_signature(edge["target"]) for edge in outgoing_edges
            ]

            # Check if this is a chord (all tasks converge to the same node)
            first_target = (
                graph[outgoing_edges[0]["target"]][0]["target"]
                if graph[outgoing_edges[0]["target"]]
                else None
            )
            is_chord = all(
                len(graph[edge["target"]]) == 1
                and graph[edge["target"]][0]["target"] == first_target
                for edge in outgoing_edges
            )
            if is_chord and first_target:
                last_task = build_signature(first_target)
                return chord(group(parallel_tasks), last_task)

            # Otherwise, it's a group
            return group(parallel_tasks)

    # Find the starting node (the one without incoming edges)
    start_node = next(
        node["id"]
        for node in nodes
        if not any(edge["target"] == node["id"] for edge in edges)
    )
    return build_signature(start_node)


def create_workflow(conn: sqlite3.Connection, **kwargs) -> Workflow:
    """Create a new workflow in the database"""
    cursor = conn.cursor()

    # Extract fields
    name = kwargs.get("name", "")
    description = kwargs.get("description")
    status = kwargs.get("status", "EDIT")
    draft = kwargs.get("draft", True)
    definition = kwargs.get("definition")
    crontab_expression = kwargs.get("crontab_expression")

    # Serialize JSON fields
    definition_json = serialize_json(definition)
    pipeline_json = None

    # Insert workflow without pipeline first to get the ID
    cursor.execute(
        """
        INSERT INTO workflows (name, description, status, draft, definition, pipeline, crontab_expression)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (name, description, status, draft, definition_json, pipeline_json, crontab_expression),
    )
    conn.commit()

    workflow_id = cursor.lastrowid

    # Generate pipeline if definition exists
    if definition and definition.get("nodes"):
        pipeline = workflow_to_signature(definition, workflow_id)
        pipeline_json = serialize_json(pipeline)

        # Update workflow with pipeline
        cursor.execute(
            """
            UPDATE workflows
            SET pipeline = ?
            WHERE id = ?
            """,
            (pipeline_json, workflow_id),
        )
        conn.commit()

    # Fetch the created workflow
    cursor.execute("SELECT * FROM workflows WHERE id = ?", (workflow_id,))
    row = cursor.fetchone()

    return Workflow.from_db_row(row)


def get_workflows(
    conn: sqlite3.Connection,
    sort_desc: bool = False,
    status_filter: Optional[str] = None,
) -> List[Workflow]:
    """Get all workflows from the database"""
    cursor = conn.cursor()

    query = "SELECT * FROM workflows"
    params = []

    if status_filter:
        query += " WHERE status = ?"
        params.append(status_filter)

    if sort_desc:
        query += " ORDER BY created_at DESC"
    else:
        query += " ORDER BY created_at ASC"

    cursor.execute(query, params)
    rows = cursor.fetchall()

    return [Workflow.from_db_row(row) for row in rows]


def get_workflow_by_id(
    conn: sqlite3.Connection,
    workflow_id: int,
    status_filter: Optional[str] = None,
) -> Optional[Workflow]:
    """Get a workflow by ID from the database"""
    cursor = conn.cursor()

    query = "SELECT * FROM workflows WHERE id = ?"
    params = [workflow_id]

    if status_filter:
        query += " AND status = ?"
        params.append(status_filter)

    cursor.execute(query, params)
    row = cursor.fetchone()

    if row:
        return Workflow.from_db_row(row)
    return None


def update_workflow(
    conn: sqlite3.Connection, workflow_id: int, **kwargs
) -> Optional[Workflow]:
    """Update a workflow in the database"""
    cursor = conn.cursor()

    # Check if workflow exists
    cursor.execute("SELECT * FROM workflows WHERE id = ?", (workflow_id,))
    row = cursor.fetchone()

    if not row:
        return None

    # Build update query dynamically based on provided fields
    update_fields = []
    params = []

    for key, value in kwargs.items():
        if key == "definition":
            update_fields.append("definition = ?")
            params.append(serialize_json(value))

            # Regenerate pipeline if definition is updated
            if value and value.get("nodes"):
                pipeline = workflow_to_signature(value, workflow_id)
                update_fields.append("pipeline = ?")
                params.append(serialize_json(pipeline))
        elif key == "pipeline":
            update_fields.append("pipeline = ?")
            params.append(serialize_json(value))
        elif key == "last_run_at":
            update_fields.append("last_run_at = ?")
            params.append(serialize_datetime(value))
        elif key in ["name", "description", "status", "draft", "crontab_expression"]:
            update_fields.append(f"{key} = ?")
            params.append(value)

    # Always update updated_at
    update_fields.append("updated_at = CURRENT_TIMESTAMP")

    if not update_fields:
        return Workflow.from_db_row(row)

    # Execute update
    params.append(workflow_id)
    query = f"UPDATE workflows SET {', '.join(update_fields)} WHERE id = ?"

    cursor.execute(query, params)
    conn.commit()

    # Fetch updated workflow
    cursor.execute("SELECT * FROM workflows WHERE id = ?", (workflow_id,))
    row = cursor.fetchone()

    return Workflow.from_db_row(row)


def delete_workflow(conn: sqlite3.Connection, workflow_id: int) -> bool:
    """Delete a workflow from the database"""
    cursor = conn.cursor()

    cursor.execute("DELETE FROM workflows WHERE id = ?", (workflow_id,))
    conn.commit()

    return cursor.rowcount > 0
