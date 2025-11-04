# Generic Input System for WFForge

WFForge now uses a standardized, flexible input system inspired by n8n's data model. This allows you to pass **any type of data** through workflows while maintaining consistency and type safety.

## Table of Contents

- [Overview](#overview)
- [WorkflowItem Structure](#workflowitem-structure)
- [Input Methods](#input-methods)
- [Task Implementation](#task-implementation)
- [Examples](#examples)
- [Migration Guide](#migration-guide)

---

## Overview

The generic input system solves several problems:

1. **Type Safety**: Pydantic validation ensures data integrity
2. **Serialization**: Base64-encoded files work across Celery workers
3. **Flexibility**: Supports JSON, files, and mixed data types
4. **Consistency**: All tasks use the same data structure
5. **Lineage**: Track data through the workflow with `paired_item`

---

## WorkflowItem Structure

All data passed between tasks uses this standardized structure:

```python
{
    "json": {                    # Main data payload (required)
        "name": "John Doe",
        "email": "john@example.com",
        "age": 30
    },
    "binary": {                  # Optional binary data (files)
        "avatar": {
            "data": "iVBORw0KG...",         # Base64-encoded content
            "mime_type": "image/png",
            "file_name": "avatar.png",
            "file_extension": ".png",
            "file_size": 12345
        }
    },
    "metadata": {                # Optional metadata
        "source": "api",
        "timestamp": "2024-01-01T00:00:00Z",
        "workflow_id": 1
    },
    "paired_item": 0             # Optional source item index
}
```

### Fields Explained

- **`json`** (required): Your main data as a dictionary. This is where most workflow data lives.
- **`binary`** (optional): Files, images, PDFs, etc. as base64-encoded strings with metadata.
- **`metadata`** (optional): Information about the item (timestamps, source, workflow ID, etc.)
- **`paired_item`** (optional): Index linking this item to its source for tracking data lineage.

---

## Input Methods

WFForge automatically converts different input types to `WorkflowItem` format.

### 1. File Upload (Single)

**Endpoint**: `POST /api/v1/workflows/{id}/push-document`

Upload a single file:

```bash
curl -X POST "http://localhost:8000/api/v1/workflows/1/push-document" \
  -F "file=@document.pdf"
```

**Resulting WorkflowItem**:
```python
{
    "json": {
        "file_name": "document.pdf",
        "content_type": "application/pdf",
        "size": 123456
    },
    "binary": {
        "file": {
            "data": "JVBERi0xLjQK...",     # Base64 PDF content
            "mime_type": "application/pdf",
            "file_name": "document.pdf",
            "file_extension": ".pdf",
            "file_size": 123456
        }
    },
    "metadata": {
        "source": "upload",
        "timestamp": "2024-01-01T12:00:00Z",
        "original_filename": "document.pdf"
    }
}
```

### 2. Multiple Files

**Endpoint**: `POST /api/v1/workflows/{id}/push-documents`

Upload multiple files (processes each in parallel):

```bash
curl -X POST "http://localhost:8000/api/v1/workflows/1/push-documents" \
  -F "files=@doc1.pdf" \
  -F "files=@doc2.pdf" \
  -F "files=@image.png"
```

Each file becomes a separate `WorkflowItem` with `paired_item` set to its index (0, 1, 2, etc.)

### 3. JSON Data (Single Object)

**Endpoint**: `POST /api/v1/workflows/{id}/push-message`

Send any JSON object:

```bash
curl -X POST "http://localhost:8000/api/v1/workflows/1/push-message" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "Alice",
    "order_id": "ORD-12345",
    "total": 99.99,
    "items": ["Widget", "Gadget"]
  }'
```

**Resulting WorkflowItem**:
```python
{
    "json": {
        "customer_name": "Alice",
        "order_id": "ORD-12345",
        "total": 99.99,
        "items": ["Widget", "Gadget"]
    },
    "metadata": {
        "source": "json",
        "timestamp": "2024-01-01T12:00:00Z"
    }
}
```

### 4. JSON Array (Multiple Items)

**Endpoint**: `POST /api/v1/workflows/{id}/push-message`

Send an array of objects (processes each in parallel):

```bash
curl -X POST "http://localhost:8000/api/v1/workflows/1/push-message" \
  -H "Content-Type: application/json" \
  -d '[
    {"name": "Alice", "score": 95},
    {"name": "Bob", "score": 87},
    {"name": "Charlie", "score": 92}
  ]'
```

Each object becomes a separate `WorkflowItem` with `paired_item` tracking.

---

## Task Implementation

### Writing Tasks

All tasks receive and return `WorkflowItem` dictionaries:

```python
from celery import shared_task

@shared_task(bind=True)
def my_custom_task(self, item_data):
    """
    Process a WorkflowItem.

    Args:
        item_data: Dict with keys: json, binary, metadata, paired_item

    Returns:
        Dict: Updated WorkflowItem
    """
    # Extract data
    json_data = item_data.get("json", {})
    binary_data = item_data.get("binary", {})
    metadata = item_data.get("metadata", {})

    # Process your data
    result_data = {
        "input_value": json_data.get("some_field"),
        "processed": True,
        "timestamp": datetime.utcnow().isoformat()
    }

    # Return updated WorkflowItem
    return {
        "json": {
            **json_data,
            "my_task_result": result_data
        },
        "binary": binary_data,  # Preserve binary data
        "metadata": {
            **metadata,
            "processed_by": "my_custom_task",
            "task_id": self.request.id
        },
        "paired_item": item_data.get("paired_item")
    }
```

### Accessing Binary Data

Decode base64 files when needed:

```python
import base64

@shared_task(bind=True)
def process_image(self, item_data):
    binary_data = item_data.get("binary", {})

    if "file" in binary_data:
        # Get the base64-encoded file
        file_info = binary_data["file"]
        file_content = base64.b64decode(file_info["data"])

        # Process the file content
        # ... your image processing logic ...

        # Return updated item
        return {
            "json": {
                **item_data.get("json", {}),
                "image_processed": True,
                "file_size": len(file_content)
            },
            "binary": binary_data,
            "metadata": item_data.get("metadata", {})
        }
```

### Adding Binary Data

Tasks can add new binary data:

```python
@shared_task(bind=True)
def generate_thumbnail(self, item_data):
    # ... generate thumbnail from original image ...

    thumbnail_content = b"..."  # Your thumbnail bytes

    binary_data = item_data.get("binary", {}) or {}

    # Add thumbnail as new binary property
    binary_data["thumbnail"] = {
        "data": base64.b64encode(thumbnail_content).decode('utf-8'),
        "mime_type": "image/png",
        "file_name": "thumbnail.png",
        "file_extension": ".png",
        "file_size": len(thumbnail_content)
    }

    return {
        "json": item_data.get("json", {}),
        "binary": binary_data,
        "metadata": item_data.get("metadata", {})
    }
```

---

## Examples

### Example 1: File Processing Pipeline

**Workflow**: Upload PDF → Extract text → Analyze with AI → Return results

```python
# Task 1: Extract text from PDF
@shared_task(bind=True)
def extract_pdf_text(self, item_data):
    import PyPDF2
    import base64
    from io import BytesIO

    binary_data = item_data.get("binary", {})
    pdf_info = binary_data.get("file", {})
    pdf_bytes = base64.b64decode(pdf_info["data"])

    # Extract text
    pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_bytes))
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()

    return {
        "json": {
            "file_name": pdf_info.get("file_name"),
            "extracted_text": text,
            "page_count": len(pdf_reader.pages)
        },
        "binary": binary_data,  # Keep original PDF
        "metadata": item_data.get("metadata", {})
    }

# Task 2: Analyze with AI
@shared_task(bind=True)
def analyze_text(self, item_data):
    text = item_data["json"]["extracted_text"]

    # Call your AI API
    analysis = call_openai_api(text)

    return {
        "json": {
            **item_data["json"],
            "analysis": analysis,
            "summary": analysis.get("summary"),
            "key_points": analysis.get("key_points")
        },
        "binary": item_data.get("binary"),
        "metadata": item_data.get("metadata")
    }
```

### Example 2: Batch Processing with Routing

**Workflow**: Upload multiple files → Route by type → Process accordingly

```python
# Router task (built-in)
{
    "routes": [
        {
            "name": "images",
            "condition": {
                "field": "content_type",
                "operator": "contains",
                "value": "image"
            },
            "branch": image_processing_signature
        },
        {
            "name": "pdfs",
            "condition": {
                "field": "content_type",
                "operator": "equals",
                "value": "application/pdf"
            },
            "branch": pdf_processing_signature
        }
    ]
}
```

### Example 3: JSON Data Processing

**Send JSON data**:
```bash
curl -X POST "http://localhost:8000/api/v1/workflows/1/push-message" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 123,
    "action": "purchase",
    "amount": 49.99,
    "product": "Premium Plan"
  }'
```

**Process in task**:
```python
@shared_task(bind=True)
def process_purchase(self, item_data):
    purchase_data = item_data["json"]

    user_id = purchase_data["user_id"]
    amount = purchase_data["amount"]

    # Process purchase
    receipt = create_receipt(user_id, amount)

    return {
        "json": {
            **purchase_data,
            "receipt_id": receipt.id,
            "status": "completed"
        },
        "metadata": item_data.get("metadata")
    }
```

---

## Migration Guide

### Old WorkflowFile Format

**Before**:
```python
class WorkflowFile:
    def __init__(self, file: UploadFile, metadata: dict = None):
        self.file = file
        self.metadata = metadata or {}

# Task received WorkflowFile object
@shared_task
def old_task(self, file_data):
    filename = file_data.file.filename
```

### New WorkflowItem Format

**After**:
```python
# Task receives WorkflowItem dict
@shared_task(bind=True)
def new_task(self, item_data):
    filename = item_data["json"]["file_name"]
    file_content = base64.b64decode(item_data["binary"]["file"]["data"])
```

### Key Differences

| Old | New |
|-----|-----|
| Python object (WorkflowFile) | Plain dict (JSON-serializable) |
| Pickle serialization | JSON + Base64 for files |
| File pointer (breaks in Celery) | Base64 string (works anywhere) |
| No validation | Pydantic validation |
| Limited metadata | Rich metadata support |

---

## Benefits Over n8n

While inspired by n8n's data model, WFForge offers additional advantages:

1. **Python-Native**: Full Python ecosystem for task logic
2. **Celery-Powered**: Distributed task execution at scale
3. **SQLite Persistence**: Lightweight workflow storage
4. **FastAPI**: Modern async API with automatic OpenAPI docs
5. **Type Safety**: Pydantic models with IDE autocomplete

---

## API Reference

### WorkflowItem Class

```python
from src.workflows.items import WorkflowItem

# Create from uploaded file
item = await WorkflowItem.from_upload_file(
    file=upload_file,
    json_data={"custom": "metadata"},
    binary_key="document",
    metadata={"source": "api"}
)

# Create from JSON
item = WorkflowItem.from_json(
    data={"name": "Alice", "age": 30},
    metadata={"source": "webhook"}
)

# Get binary content
file_bytes = item.get_binary_content("file")

# Add binary data
item.add_binary(
    key="thumbnail",
    content=thumbnail_bytes,
    mime_type="image/png",
    file_name="thumb.png"
)

# Clone item
new_item = item.clone()
```

### WorkflowInput Class

```python
from src.workflows.items import WorkflowInput

# Create from multiple files
workflow_input = await WorkflowInput.from_files(
    files=[file1, file2, file3],
    metadata={"batch_id": "batch_001"}
)

# Create from JSON array
workflow_input = WorkflowInput.from_json_array(
    data=[
        {"name": "Item 1"},
        {"name": "Item 2"}
    ],
    metadata={"source": "import"}
)

# Access items
for item in workflow_input.items:
    print(item.json)
```

---

## Best Practices

1. **Always preserve binary data**: Unless you're removing files intentionally, pass `binary` through unchanged
2. **Enrich json data**: Add your task's output to `json` dict
3. **Update metadata**: Track which tasks processed the item
4. **Use paired_item**: Maintain data lineage for debugging
5. **Handle missing fields**: Use `.get()` with defaults
6. **Decode once**: If processing files, decode at the start and cache
7. **Return consistent structure**: Always return a complete WorkflowItem dict

---

## Troubleshooting

### Problem: Binary data not available in downstream tasks

**Cause**: Forgot to include `binary` in return dict

**Solution**:
```python
return {
    "json": {...},
    "binary": item_data.get("binary"),  # ← Don't forget this!
    "metadata": {...}
}
```

### Problem: Task receives dict instead of expected object

**Cause**: WorkflowItem is serialized as dict for Celery

**Solution**: Use dict access instead of attribute access:
```python
# Wrong
filename = item_data.file_name

# Correct
filename = item_data["json"]["file_name"]
```

### Problem: File content is corrupt

**Cause**: Base64 decoding error or missing padding

**Solution**: Validate base64 string before decoding:
```python
import base64

try:
    file_content = base64.b64decode(file_info["data"])
except Exception as e:
    logger.error(f"Base64 decode error: {e}")
```

---

## Next Steps

- **Create custom tasks**: Implement your business logic with WorkflowItem
- **Build workflows**: Chain tasks together in the visual editor
- **Test with examples**: Use the provided examples as templates
- **Extend the system**: Add new task types as needed

For more information, see the main [README.md](../README.md) and API documentation at `/docs` when running the server.
