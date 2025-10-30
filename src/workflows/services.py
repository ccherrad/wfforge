from typing import List, Optional
import structlog
from sqlalchemy import desc
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import BinaryExpression
from celery import chain, group, chord, signature

from .models import Workflow

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


def create_workflow(session: Session, **kwargs) -> Workflow:
    new_workflow = Workflow(**kwargs)
    session.add(new_workflow)
    session.flush()

    workflow_id = new_workflow.id

    # Only create pipeline if definition exists
    definition = kwargs.get("definition")
    if definition and definition["nodes"]:
        pipeline = workflow_to_signature(definition, workflow_id)
        new_workflow.pipeline = pipeline

    session.commit()
    return new_workflow


def get_workflows(
    session: Session,
    sort_desc: bool = False,
    filters: List[BinaryExpression] = [],
) -> List[Workflow]:
    sort_by = desc(Workflow.created_at) if sort_desc else Workflow.created_at
    return session.query(Workflow).filter(*filters).order_by(sort_by).all()


def get_workflow_by_id(
    session: Session, workflow_id: int, filters: List[BinaryExpression] = []
) -> Workflow:
    filters.append(Workflow.id == workflow_id)
    return session.query(Workflow).filter(*filters).first()


def update_workflow(session: Session, workflow_id, **kwargs) -> Optional[Workflow]:
    workflow = session.query(Workflow).filter(Workflow.id == workflow_id).first()
    definition = kwargs.get("definition")
    if definition and definition["nodes"]:
        pipeline = workflow_to_signature(definition, workflow_id)
        kwargs["pipeline"] = pipeline
    if workflow:
        for key, value in kwargs.items():
            setattr(workflow, key, value)
        session.commit()
        session.refresh(workflow)
        return workflow
    return None


def delete_workflow(session: Session, workflow_id: int) -> bool:
    workflow = session.query(Workflow).filter(Workflow.id == workflow_id).first()
    if workflow:
        session.delete(workflow)
        session.commit()
        return True
    return False