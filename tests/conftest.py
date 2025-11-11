"""Pytest configuration and fixtures for testing WFForge API."""
import os
import sys
import pytest
import tempfile
from fastapi.testclient import TestClient
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.main import app
from src.database import Database, get_db


@pytest.fixture(scope="function")
def test_db():
    """Provide a fresh test database for each test."""
    # Create a temporary database file
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_db.close()

    # Create a test database instance
    test_database = Database(temp_db.name)

    yield test_database

    # Cleanup
    try:
        os.unlink(temp_db.name)
    except:
        pass


@pytest.fixture(scope="function")
def client(test_db, monkeypatch):
    """Provide a test client with a fresh database."""
    # Override the get_db dependency to use test database
    def override_get_db():
        with test_db.get_connection() as conn:
            yield conn

    app.dependency_overrides[get_db] = override_get_db

    # Mock Celery apply_async to avoid actual task execution
    def mock_apply_async(*args, **kwargs):
        return type('obj', (object,), {'id': 'test-task-id'})()

    # Patch signature to return a mock with apply_async
    original_signature = __import__('celery', fromlist=['signature']).signature
    def mock_signature(data):
        sig = original_signature(data) if isinstance(data, dict) else data
        sig.apply_async = mock_apply_async
        sig.clone = lambda *args, **kwargs: mock_signature(data)
        return sig

    monkeypatch.setattr('src.workflows.router.signature', mock_signature)

    with TestClient(app) as test_client:
        yield test_client

    # Clean up dependency overrides
    app.dependency_overrides.clear()


@pytest.fixture
def sample_workflow_definition():
    """Provide a simple workflow definition for testing."""
    return {
        "nodes": [
            {
                "id": "input-1",
                "type": "processing",
                "label": "File Input",
                "position": {"x": 100, "y": 100},
                "data": {
                    "task_name": "input_file",
                    "config": {}
                }
            },
            {
                "id": "agent-1",
                "type": "processing",
                "label": "AI Agent",
                "position": {"x": 400, "y": 100},
                "data": {
                    "task_name": "call_agent",
                    "agent_config": {
                        "model": "test-model",
                        "prompt": "Process this document"
                    }
                }
            }
        ],
        "edges": [
            {
                "id": "edge-1",
                "source": "input-1",
                "target": "agent-1",
                "sourceHandle": None,
                "targetHandle": None
            }
        ]
    }


@pytest.fixture
def simple_workflow_definition():
    """Provide the simplest possible workflow for basic testing."""
    return {
        "nodes": [
            {
                "id": "input-1",
                "type": "processing",
                "label": "File Input",
                "position": {"x": 100, "y": 100},
                "data": {
                    "task_name": "input_file",
                    "config": {}
                }
            }
        ],
        "edges": []
    }


@pytest.fixture
def test_file_content():
    """Provide test file content."""
    return b"This is a test document for workflow processing."


@pytest.fixture
def test_file(tmp_path, test_file_content):
    """Create a temporary test file."""
    file_path = tmp_path / "test_document.txt"
    file_path.write_bytes(test_file_content)
    return file_path
