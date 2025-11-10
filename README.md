# WFForge - Lightweight Workflow Engine

A powerful, self-contained workflow engine built with FastAPI, Celery, and SQLite for creating and executing visual workflows. **No external dependencies required** - everything runs with built-in Python modules!

## ✨ Features

- **Visual Workflow Creation**: Design workflows with drag-and-drop interface (VueFlow-based frontend)
- **Asynchronous Task Processing**: Execute workflows using Celery with filesystem broker
- **Multiple Task Types**: File processing, AI agents, routing, and result merging
- **SQLite Database**: Lightweight, self-contained data storage
- **RESTful API**: Full CRUD operations for workflows via FastAPI
- **Scheduled Execution**: Cron-based workflow scheduling with SQLite persistence
- **Zero External Services**: No Redis, no PostgreSQL, no configuration hassle!

## 🏗️ Architecture

- **Backend**: FastAPI with Pydantic validation
- **Database**: SQLite with native Python sqlite3 (no ORM)
- **Task Queue**: Celery with **filesystem broker** (no Redis!)
- **Result Backend**: SQLite database
- **Beat Scheduler**: SQLite-based schedule persistence
- **Storage**: Everything in SQLite files

### Why No Redis?

WFForge uses a **filesystem-based message broker** instead of Redis, making it:
- ✅ **Simpler** - No external services to install or manage
- ✅ **Portable** - Works offline, easy to deploy
- ✅ **Self-contained** - All data in local files
- ✅ **Perfect for**: Development, single-server deployments, moderate workloads

See [REDIS_REMOVAL_GUIDE.md](./REDIS_REMOVAL_GUIDE.md) for details.

## 🚀 Quick Start

### Prerequisites

**Option 1: Docker (Recommended)**
- Docker Engine 20.10+
- Docker Compose 2.0+

**Option 2: Native Python**
- Python 3.9+
- That's it! No external services needed.

### Installation

#### Option 1: Using Docker (Recommended) 🐳

```bash
# Clone repository
git clone <repository-url>
cd wfforge

# Start all services with one command
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps
```

**That's it!** All services are running:
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

See [DOCKER.md](./DOCKER.md) for complete Docker documentation.

#### Option 2: Native Python Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd wfforge
```

2. Install dependencies:
```bash
# Using pip
pip install -e .

# Or using uv (recommended)
uv sync
```

3. Set up environment variables (optional):
```bash
cp .env.example .env
# Edit .env if needed (defaults work out of the box!)
```

4. **Database auto-initializes** on first run - no manual setup needed! ✨

### Running the Application

**Using Docker:**

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down
```

**Using Helper Scripts:**

```bash
# Start everything with one script
./scripts/start_all.sh
```

**Using Python Directly:**

**Option 1: Simple (3 commands)**

```bash
# Terminal 1: Start API server
uvicorn src.main:app --reload

# Terminal 2: Start Celery worker
celery -A src.tasks.worker worker --loglevel=info

# Terminal 3: Start Celery Beat scheduler (for scheduled workflows)
celery -A src.tasks.scheduler beat --loglevel=info
```

**Option 2: Background processes**

```bash
# Start all services
uvicorn src.main:app --reload &
celery -A src.tasks.worker worker --loglevel=info &
celery -A src.tasks.scheduler beat --loglevel=info &
```

That's it! 🎉 No Redis server to start, no database migrations to run.

### Verify Installation

```bash
# Check API is running
curl http://localhost:8000/health

# Response: {"status":"healthy","database":"./workflows.db"}
```

### Testing Database Initialization

```bash
# Run database verification script
python scripts/init_db.py

# Output shows all created tables:
# - workflows
# - celery_periodic_task
# - celery_crontab_schedule
# - celery_interval_schedule
# - celery_periodic_task_schedule
```

## 📡 API Endpoints

### Workflow Management
- `GET /` - API status
- `GET /health` - Health check (includes database path)
- `POST /api/v1/workflows/` - Create workflow
- `GET /api/v1/workflows/` - List all workflows
- `GET /api/v1/workflows/{id}` - Get workflow details
- `PUT /api/v1/workflows/{id}` - Update workflow
- `DELETE /api/v1/workflows/{id}` - Delete workflow

### Workflow Execution
- `POST /api/v1/workflows/{id}/push-document` - Execute workflow with single file
- `POST /api/v1/workflows/{id}/push-documents` - Execute workflow with multiple files
- `POST /api/v1/workflows/{id}/push-message` - Execute workflow with JSON message

## 🗂️ File Structure

```
wfforge/
├── workflows.db                 # Main database (auto-created)
├── celery_results.db           # Task results (auto-created)
├── celery_broker/              # Message queue (auto-created)
│   ├── *.msg                  # Pending tasks
│   ├── out/                   # Outgoing messages
│   └── processed/             # Completed tasks
├── src/
│   ├── config.py              # Configuration (no Redis!)
│   ├── database.py            # SQLite manager (auto-init)
│   ├── main.py                # FastAPI app
│   ├── tasks/
│   │   ├── worker.py         # Celery worker (filesystem broker)
│   │   ├── scheduler.py      # Celery Beat (SQLite backend)
│   │   └── actions/          # Task implementations
│   └── workflows/
│       ├── models.py          # Dataclass models (no ORM)
│       ├── services.py        # Database operations
│       ├── router.py          # API endpoints
│       └── schemas.py         # Pydantic schemas
└── scripts/
    └── init_db.py             # Database verification
```

## 🔧 Configuration

All configuration is in `src/config.py` with sensible defaults:

```python
# Database
database_url: str = "sqlite:///./workflows.db"

# Celery (filesystem broker + SQLite backend)
celery_broker_url: str = "filesystem://"
celery_broker_folder: str = "./celery_broker"
celery_result_backend: str = "db+sqlite:///./celery_results.db"

# API
host: str = "0.0.0.0"
port: int = 8000
```

Override via environment variables in `.env` file.

## 📊 Workflow Definition Format

Workflows use VueFlow's JSON format:

```json
{
  "nodes": [
    {
      "id": "node-1",
      "type": "processing",
      "label": "Process File",
      "position": {"x": 100, "y": 100},
      "data": {
        "task_name": "input_file",
        "config": {...}
      }
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
```

The backend automatically converts this to a Celery pipeline for execution.

## 🧪 Development

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

### Database Inspection

```bash
# View workflows
sqlite3 workflows.db "SELECT * FROM workflows;"

# View Celery results
sqlite3 celery_results.db "SELECT * FROM celery_taskmeta LIMIT 10;"

# View scheduled tasks
sqlite3 workflows.db "SELECT * FROM celery_periodic_task;"
```

## 📚 Documentation

- [DOCKER.md](./DOCKER.md) - Complete Docker deployment guide
- [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md) - SQLAlchemy to native SQLite migration
- [REDIS_REMOVAL_GUIDE.md](./REDIS_REMOVAL_GUIDE.md) - Redis to filesystem broker migration

## 🎯 Use Cases

Perfect for:
- ✅ **Development environments** - No external services to manage
- ✅ **Single-server deployments** - Everything self-contained
- ✅ **Document processing pipelines** - Async file processing
- ✅ **AI agent workflows** - Chained LLM operations
- ✅ **Data transformation** - ETL-like operations
- ✅ **Scheduled tasks** - Cron-based automation

## ⚡ Performance

- **Throughput**: Hundreds of tasks per second
- **Latency**: Low (filesystem I/O)
- **Scalability**: Single server, moderate workloads
- **Storage**: Limited only by disk space

For **very high volume** (1000+ tasks/sec) or **distributed** deployments, consider using Redis broker instead. See [REDIS_REMOVAL_GUIDE.md](./REDIS_REMOVAL_GUIDE.md) for trade-offs.

## 🔐 Security

- API key authentication via headers
- Secret key for session management
- No network exposure of message broker (filesystem-based)
- SQLite file permissions for data access control

## 🚧 Roadmap

- [ ] Web-based workflow designer UI
- [ ] Workflow templates library
- [ ] Advanced task types (webhooks, transformations)
- [ ] Monitoring dashboard
- [ ] Workflow versioning
- [ ] Export/import workflows

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- **FastAPI** - Modern Python web framework
- **Celery** - Distributed task queue
- **SQLite** - Embedded database engine
- **VueFlow** - Workflow visualization library

---

**Version**: 0.2.0
**Status**: Production-ready for single-server deployments
**Dependencies**: Pure Python + FastAPI ecosystem (no external services!)
