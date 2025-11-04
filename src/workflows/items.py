"""
Generic workflow item structure inspired by n8n's INodeExecutionData.

This module provides a standardized data structure for passing data between
workflow tasks, supporting JSON data, binary files, and metadata.
"""
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
import base64


class BinaryData(BaseModel):
    """Binary data representation (files, images, etc.)"""
    data: str = Field(..., description="Base64-encoded binary content")
    mime_type: str = Field(..., description="MIME type (e.g., 'image/png', 'application/pdf')")
    file_name: Optional[str] = Field(None, description="Original filename")
    file_extension: Optional[str] = Field(None, description="File extension (e.g., '.png')")
    file_size: Optional[int] = Field(None, description="Size in bytes")

    class Config:
        json_schema_extra = {
            "example": {
                "data": "iVBORw0KGgoAAAANSUhEUg...",
                "mime_type": "image/png",
                "file_name": "screenshot.png",
                "file_extension": ".png",
                "file_size": 45678
            }
        }


class WorkflowItem(BaseModel):
    """
    Standardized workflow data item.

    All data passed between tasks uses this structure:
    - json: Main data payload (required)
    - binary: Optional binary data (files, images, etc.)
    - metadata: Optional metadata about the item
    - paired_item: Optional index linking this item to its source
    """
    json: Dict[str, Any] = Field(
        default_factory=dict,
        description="Main JSON data payload"
    )
    binary: Optional[Dict[str, BinaryData]] = Field(
        None,
        description="Binary data (files) keyed by property name"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Metadata about this item (timestamps, source, etc.)"
    )
    paired_item: Optional[int] = Field(
        None,
        description="Index of the source item that produced this item"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "json": {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "age": 30
                },
                "binary": {
                    "avatar": {
                        "data": "iVBORw0KG...",
                        "mime_type": "image/png",
                        "file_name": "avatar.png",
                        "file_extension": ".png",
                        "file_size": 12345
                    }
                },
                "metadata": {
                    "source": "api",
                    "timestamp": "2024-01-01T00:00:00Z",
                    "workflow_id": 1
                },
                "paired_item": 0
            }
        }

    @classmethod
    async def from_upload_file(
        cls,
        file,
        json_data: Optional[Dict[str, Any]] = None,
        binary_key: str = "file",
        metadata: Optional[Dict[str, Any]] = None
    ) -> "WorkflowItem":
        """
        Create a WorkflowItem from a FastAPI UploadFile.

        Args:
            file: FastAPI UploadFile object
            json_data: Optional JSON data to include
            binary_key: Key to store the file under in binary dict
            metadata: Optional metadata

        Returns:
            WorkflowItem with the file as binary data
        """
        # Read file content
        content = await file.read()
        await file.seek(0)  # Reset file pointer

        # Encode to base64
        base64_content = base64.b64encode(content).decode('utf-8')

        # Get file extension
        file_extension = None
        if file.filename and '.' in file.filename:
            file_extension = '.' + file.filename.rsplit('.', 1)[1]

        # Create binary data
        binary_data = BinaryData(
            data=base64_content,
            mime_type=file.content_type or 'application/octet-stream',
            file_name=file.filename,
            file_extension=file_extension,
            file_size=len(content)
        )

        # Build item
        item = cls(
            json=json_data or {
                "file_name": file.filename,
                "content_type": file.content_type,
                "size": len(content)
            },
            binary={binary_key: binary_data},
            metadata=metadata or {
                "source": "upload",
                "timestamp": datetime.utcnow().isoformat(),
                "original_filename": file.filename
            }
        )

        return item

    @classmethod
    def from_json(
        cls,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> "WorkflowItem":
        """
        Create a WorkflowItem from JSON data.

        Args:
            data: JSON data dictionary
            metadata: Optional metadata

        Returns:
            WorkflowItem with JSON data
        """
        return cls(
            json=data,
            metadata=metadata or {
                "source": "json",
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    def get_binary_content(self, key: str = "file") -> Optional[bytes]:
        """
        Get decoded binary content from a binary property.

        Args:
            key: Binary property key

        Returns:
            Decoded bytes or None if not found
        """
        if not self.binary or key not in self.binary:
            return None

        return base64.b64decode(self.binary[key].data)

    def add_binary(
        self,
        key: str,
        content: bytes,
        mime_type: str,
        file_name: Optional[str] = None,
        file_extension: Optional[str] = None
    ) -> None:
        """
        Add binary data to this item.

        Args:
            key: Key to store binary data under
            content: Raw binary content
            mime_type: MIME type
            file_name: Optional filename
            file_extension: Optional file extension
        """
        if self.binary is None:
            self.binary = {}

        self.binary[key] = BinaryData(
            data=base64.b64encode(content).decode('utf-8'),
            mime_type=mime_type,
            file_name=file_name,
            file_extension=file_extension,
            file_size=len(content)
        )

    def set_metadata(self, key: str, value: Any) -> None:
        """Add or update a metadata field."""
        if self.metadata is None:
            self.metadata = {}
        self.metadata[key] = value

    def clone(self) -> "WorkflowItem":
        """Create a deep copy of this item."""
        return WorkflowItem(**self.model_dump())


class WorkflowInput(BaseModel):
    """
    Input to a workflow execution.

    Supports multiple items for batch processing.
    """
    items: List[WorkflowItem] = Field(
        default_factory=list,
        description="List of workflow items to process"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "json": {"name": "Item 1"},
                        "metadata": {"index": 0}
                    },
                    {
                        "json": {"name": "Item 2"},
                        "metadata": {"index": 1}
                    }
                ]
            }
        }

    @classmethod
    async def from_files(
        cls,
        files: List,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "WorkflowInput":
        """
        Create WorkflowInput from multiple files.

        Args:
            files: List of UploadFile objects
            metadata: Optional shared metadata

        Returns:
            WorkflowInput with one item per file
        """
        items = []
        for idx, file in enumerate(files):
            item_metadata = (metadata or {}).copy()
            item_metadata["file_index"] = idx

            item = await WorkflowItem.from_upload_file(
                file,
                metadata=item_metadata
            )
            item.paired_item = idx
            items.append(item)

        return cls(items=items)

    @classmethod
    def from_json_array(
        cls,
        data: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> "WorkflowInput":
        """
        Create WorkflowInput from array of JSON objects.

        Args:
            data: List of JSON dictionaries
            metadata: Optional shared metadata

        Returns:
            WorkflowInput with one item per JSON object
        """
        items = []
        for idx, item_data in enumerate(data):
            item_metadata = (metadata or {}).copy()
            item_metadata["item_index"] = idx

            item = WorkflowItem.from_json(
                item_data,
                metadata=item_metadata
            )
            item.paired_item = idx
            items.append(item)

        return cls(items=items)
