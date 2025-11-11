"""API tests for workflow creation and execution."""
import pytest
import json
import io
from typing import Dict, Any


class TestWorkflowCRUD:
    """Test workflow CRUD operations."""

    def test_create_workflow(self, client, simple_workflow_definition):
        """Test creating a new workflow via API."""
        workflow_data = {
            "name": "Test Workflow",
            "description": "A simple test workflow",
            "status": "ACTIVE",
            "draft": False,
            "definition": simple_workflow_definition
        }

        response = client.post("/api/v1/workflows/", json=workflow_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Workflow"
        assert data["description"] == "A simple test workflow"
        assert data["status"] == "ACTIVE"
        assert data["draft"] is False
        assert "id" in data
        assert data["id"] > 0

    def test_list_workflows(self, client, simple_workflow_definition):
        """Test listing all workflows."""
        # Create a few workflows
        for i in range(3):
            workflow_data = {
                "name": f"Test Workflow {i}",
                "description": f"Description {i}",
                "status": "EDIT",
                "draft": True,
                "definition": simple_workflow_definition
            }
            client.post("/api/v1/workflows/", json=workflow_data)

        # List workflows
        response = client.get("/api/v1/workflows/")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3

    def test_get_workflow_details(self, client, sample_workflow_definition):
        """Test getting workflow details by ID."""
        # Create a workflow
        workflow_data = {
            "name": "Detailed Workflow",
            "description": "Test workflow with details",
            "status": "ACTIVE",
            "draft": False,
            "definition": sample_workflow_definition
        }
        create_response = client.post("/api/v1/workflows/", json=workflow_data)
        workflow_id = create_response.json()["id"]

        # Get workflow details
        response = client.get(f"/api/v1/workflows/{workflow_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == workflow_id
        assert data["name"] == "Detailed Workflow"
        assert "definition" in data
        assert data["definition"] is not None
        assert len(data["definition"]["nodes"]) == 2
        assert len(data["definition"]["edges"]) == 1
        assert "pipeline" in data  # Should have auto-generated pipeline

    def test_update_workflow(self, client, simple_workflow_definition):
        """Test updating a workflow."""
        # Create a workflow
        workflow_data = {
            "name": "Original Name",
            "description": "Original Description",
            "status": "EDIT",
            "draft": True,
            "definition": simple_workflow_definition
        }
        create_response = client.post("/api/v1/workflows/", json=workflow_data)
        workflow_id = create_response.json()["id"]

        # Update the workflow
        update_data = {
            "name": "Updated Name",
            "description": "Updated Description",
            "status": "ACTIVE",
            "draft": False
        }
        response = client.put(f"/api/v1/workflows/{workflow_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated Description"
        assert data["status"] == "ACTIVE"
        assert data["draft"] is False

    def test_delete_workflow(self, client, simple_workflow_definition):
        """Test deleting a workflow."""
        # Create a workflow
        workflow_data = {
            "name": "To Be Deleted",
            "description": "This workflow will be deleted",
            "status": "EDIT",
            "draft": True,
            "definition": simple_workflow_definition
        }
        create_response = client.post("/api/v1/workflows/", json=workflow_data)
        workflow_id = create_response.json()["id"]

        # Delete the workflow
        response = client.delete(f"/api/v1/workflows/{workflow_id}")

        assert response.status_code == 204

        # Verify it's deleted
        get_response = client.get(f"/api/v1/workflows/{workflow_id}")
        assert get_response.status_code == 404

    def test_get_nonexistent_workflow(self, client):
        """Test getting a workflow that doesn't exist."""
        response = client.get("/api/v1/workflows/99999")
        assert response.status_code == 404


class TestWorkflowExecution:
    """Test workflow execution endpoints."""

    def test_push_single_document(self, client, simple_workflow_definition, test_file):
        """Test executing a workflow with a single document."""
        # Create a workflow
        workflow_data = {
            "name": "Document Processing Workflow",
            "description": "Process a single document",
            "status": "ACTIVE",
            "draft": False,
            "definition": simple_workflow_definition
        }
        create_response = client.post("/api/v1/workflows/", json=workflow_data)
        workflow_id = create_response.json()["id"]

        # Execute with a document
        with open(test_file, "rb") as f:
            files = {"file": ("test_document.txt", f, "text/plain")}
            response = client.post(
                f"/api/v1/workflows/{workflow_id}/push-document",
                files=files
            )

        assert response.status_code == 202
        data = response.json()
        assert "message" in data
        assert "queued" in data["message"].lower()

    def test_push_multiple_documents(self, client, simple_workflow_definition, tmp_path):
        """Test executing a workflow with multiple documents."""
        # Create test files
        file1 = tmp_path / "doc1.txt"
        file2 = tmp_path / "doc2.txt"
        file1.write_text("Content of document 1")
        file2.write_text("Content of document 2")

        # Create a workflow
        workflow_data = {
            "name": "Multi-Document Workflow",
            "description": "Process multiple documents",
            "status": "ACTIVE",
            "draft": False,
            "definition": simple_workflow_definition
        }
        create_response = client.post("/api/v1/workflows/", json=workflow_data)
        workflow_id = create_response.json()["id"]

        # Execute with multiple documents
        with open(file1, "rb") as f1, open(file2, "rb") as f2:
            files = [
                ("files", ("doc1.txt", f1, "text/plain")),
                ("files", ("doc2.txt", f2, "text/plain"))
            ]
            response = client.post(
                f"/api/v1/workflows/{workflow_id}/push-documents",
                files=files
            )

        assert response.status_code == 202
        data = response.json()
        assert "message" in data
        assert "queued" in data["message"].lower()

    def test_push_message(self, client, simple_workflow_definition):
        """Test executing a workflow with a JSON message."""
        # Create a workflow
        workflow_data = {
            "name": "Message Processing Workflow",
            "description": "Process JSON messages",
            "status": "ACTIVE",
            "draft": False,
            "definition": simple_workflow_definition
        }
        create_response = client.post("/api/v1/workflows/", json=workflow_data)
        workflow_id = create_response.json()["id"]

        # Execute with a message
        message_data = {
            "data": "Test message content",
            "metadata": {
                "user_id": 123,
                "timestamp": "2025-11-11T10:00:00Z"
            }
        }
        response = client.post(
            f"/api/v1/workflows/{workflow_id}/push-message",
            json=message_data
        )

        assert response.status_code == 202
        data = response.json()
        assert "message" in data
        assert "queued" in data["message"].lower()

    def test_execute_nonexistent_workflow(self, client, test_file):
        """Test executing a workflow that doesn't exist."""
        with open(test_file, "rb") as f:
            files = {"file": ("test_document.txt", f, "text/plain")}
            response = client.post(
                "/api/v1/workflows/99999/push-document",
                files=files
            )

        assert response.status_code == 404


class TestWorkflowDefinitions:
    """Test workflow definition validation and pipeline generation."""

    def test_workflow_with_two_node_chain(self, client):
        """Test creating a workflow with two nodes in sequence."""
        workflow_definition = {
            "nodes": [
                {
                    "id": "node-1",
                    "type": "processing",
                    "label": "Input",
                    "position": {"x": 0, "y": 0},
                    "data": {"task_name": "input_file"}
                },
                {
                    "id": "node-2",
                    "type": "processing",
                    "label": "Process",
                    "position": {"x": 200, "y": 0},
                    "data": {"task_name": "call_agent", "agent_config": {}}
                }
            ],
            "edges": [
                {
                    "id": "edge-1",
                    "source": "node-1",
                    "target": "node-2"
                }
            ]
        }

        workflow_data = {
            "name": "Two Node Chain",
            "description": "Sequential processing",
            "status": "ACTIVE",
            "draft": False,
            "definition": workflow_definition
        }

        response = client.post("/api/v1/workflows/", json=workflow_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Two Node Chain"

        # Get details to check pipeline
        workflow_id = data["id"]
        details_response = client.get(f"/api/v1/workflows/{workflow_id}")
        details = details_response.json()

        assert "pipeline" in details
        assert details["pipeline"] is not None

    def test_workflow_with_parallel_nodes(self, client):
        """Test creating a workflow with parallel processing."""
        workflow_definition = {
            "nodes": [
                {
                    "id": "input",
                    "type": "processing",
                    "label": "Input",
                    "position": {"x": 0, "y": 100},
                    "data": {"task_name": "input_file"}
                },
                {
                    "id": "process-1",
                    "type": "processing",
                    "label": "Process 1",
                    "position": {"x": 200, "y": 0},
                    "data": {"task_name": "call_agent", "agent_config": {}}
                },
                {
                    "id": "process-2",
                    "type": "processing",
                    "label": "Process 2",
                    "position": {"x": 200, "y": 200},
                    "data": {"task_name": "call_agent", "agent_config": {}}
                },
                {
                    "id": "merge",
                    "type": "processing",
                    "label": "Merge Results",
                    "position": {"x": 400, "y": 100},
                    "data": {"task_name": "merge_results"}
                }
            ],
            "edges": [
                {"id": "e1", "source": "input", "target": "process-1"},
                {"id": "e2", "source": "input", "target": "process-2"},
                {"id": "e3", "source": "process-1", "target": "merge"},
                {"id": "e4", "source": "process-2", "target": "merge"}
            ]
        }

        workflow_data = {
            "name": "Parallel Processing",
            "description": "Process in parallel and merge",
            "status": "ACTIVE",
            "draft": False,
            "definition": workflow_definition
        }

        response = client.post("/api/v1/workflows/", json=workflow_data)

        assert response.status_code == 201


class TestHealthAndInfo:
    """Test health check and info endpoints."""

    def test_health_check(self, client):
        """Test the health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "database" in data

    def test_root_endpoint(self, client):
        """Test the root endpoint."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data or "name" in data


class TestCompleteWorkflowScenario:
    """End-to-end test of creating and executing a workflow."""

    def test_complete_workflow_lifecycle(self, client, sample_workflow_definition, test_file):
        """Test the complete lifecycle: create, execute, and verify a workflow."""
        # Step 1: Create a workflow
        workflow_data = {
            "name": "Complete Test Workflow",
            "description": "End-to-end workflow test",
            "status": "ACTIVE",
            "draft": False,
            "definition": sample_workflow_definition
        }

        create_response = client.post("/api/v1/workflows/", json=workflow_data)
        assert create_response.status_code == 201
        workflow_id = create_response.json()["id"]
        print(f"\n✓ Created workflow with ID: {workflow_id}")

        # Step 2: Verify workflow details
        details_response = client.get(f"/api/v1/workflows/{workflow_id}")
        assert details_response.status_code == 200
        details = details_response.json()
        assert details["status"] == "ACTIVE"
        assert details["definition"] is not None
        assert details["pipeline"] is not None
        print(f"✓ Workflow details verified")
        print(f"  - Nodes: {len(details['definition']['nodes'])}")
        print(f"  - Edges: {len(details['definition']['edges'])}")

        # Step 3: Execute workflow with a document
        with open(test_file, "rb") as f:
            files = {"file": ("test_document.txt", f, "text/plain")}
            exec_response = client.post(
                f"/api/v1/workflows/{workflow_id}/push-document",
                files=files
            )

        assert exec_response.status_code == 202
        print(f"✓ Workflow execution queued successfully")

        # Step 4: Execute with message
        message_data = {"data": "Test message", "metadata": {"test": True}}
        msg_response = client.post(
            f"/api/v1/workflows/{workflow_id}/push-message",
            json=message_data
        )

        assert msg_response.status_code == 202
        data = msg_response.json()
        assert "message" in data
        assert "queued" in data["message"].lower()
        print(f"✓ Message-based execution queued successfully")

        # Step 5: List workflows and verify our workflow is there
        list_response = client.get("/api/v1/workflows/")
        assert list_response.status_code == 200
        workflows = list_response.json()
        assert isinstance(workflows, list)
        workflow_ids = [w["id"] for w in workflows]
        assert workflow_id in workflow_ids
        print(f"✓ Workflow appears in listing")

        # Step 6: Update workflow
        update_data = {
            "description": "Updated description after testing",
            "status": "EDIT"
        }
        update_response = client.put(f"/api/v1/workflows/{workflow_id}", json=update_data)
        assert update_response.status_code == 200
        assert update_response.json()["description"] == "Updated description after testing"
        print(f"✓ Workflow updated successfully")

        print(f"\n✓ Complete workflow lifecycle test passed!")
