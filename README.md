# WFForge - Workflow Engine

A powerful workflow engine built with FastAPI, Celery, and SQLite for creating and executing visual workflows.

## Features

- **Visual Workflow Creation**: Design workflows with drag-and-drop interface (frontend separate)
- **Task Processing**: Execute workflows asynchronously using Celery
- **Multiple Task Types**: File processing, AI agents, routing, and result merging
- **SQLite Database**: Lightweight data storage for workflows and metadata
- **RESTful API**: Full CRUD operations for workflows via FastAPI
- **Scheduled Execution**: Cron-based workflow scheduling
- **Redis Integration**: Message brokering and result backend

## Architecture

- **Backend**: FastAPI with Pydantic validation
- **Database**: SQLite with SQLAlchemy ORM
- **Task Queue**: Celery with Redis broker
- **Storage**: SQLite for metadata, Redis for caching

## Quick Start

### Prerequisites

- Python 3.9+
- Redis server
- uv package manager

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd wfforge
```

2. Install dependencies with uv:
```bash
uv sync
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Initialize the database:
```bash
python -c "from src.database import engine, Base; Base.metadata.create_all(bind=engine)"
```

### Running the Application

1. Start Redis:
```bash
redis-server
```

2. Start the Celery worker:
```bash
celery -A src.tasks.worker.celery_app worker --loglevel=info
```

3. Start the FastAPI server:
```bash
uvicorn src.main:app --reload
```

### API Endpoints

- `GET /` - API status
- `GET /health` - Health check
- `POST /api/v1/workflows/` - Create workflow
- `GET /api/v1/workflows/` - List workflows
- `GET /api/v1/workflows/{id}` - Get workflow details
- `PUT /api/v1/workflows/{id}` - Update workflow
- `DELETE /api/v1/workflows/{id}` - Delete workflow
- `POST /api/v1/workflows/{id}/push-document` - Trigger workflow with file
- `POST /api/v1/workflows/{id}/push-documents` - Trigger with multiple files
- `POST /api/v1/workflows/{id}/push-message` - Trigger with message

## Development

### Running Tests

```bash
uv run pytest
```

### Code Formatting

```bash
uv run black src/
uv run isort src/
uv run flake8 src/
```

## License

MIT License - see LICENSE file for details