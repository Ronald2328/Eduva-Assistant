"""Pydantic models for document management API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentUploadRequest(BaseModel):
    """Request to upload a new document."""

    document_name: str = Field(..., description="Name of the document")
    school: str = Field(..., description="School/Faculty name")
    description: str | None = Field(None, description="Document description")
    pdf_url: str | None = Field(None, description="URL of the PDF file (optional)")


class DocumentUploadResponse(BaseModel):
    """Response after document upload."""

    success: bool
    document_id: UUID
    chunks_created: int
    processing_time_seconds: float
    message: str | None = None


class DocumentInfo(BaseModel):
    """Basic document information."""

    id: UUID
    nombre: str
    descripcion: str
    school: str
    file_type: str
    chunks_count: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    """Response for listing documents."""

    documents: list[DocumentInfo]
    total: int


class DocumentDeleteResponse(BaseModel):
    """Response after document deletion."""

    success: bool
    message: str
    document_id: UUID | None = None


class ChunkMatch(BaseModel):
    """Single chunk search result."""

    chunk_id: UUID
    document_id: UUID
    document_name: str
    school: str
    chunk_index: int
    content: str
    similarity_score: float
    source_page: int | None = None
    section_title: str | None = None
    metadata: dict[str, str | int | float] | None = None


class ChunksSearchResponse(BaseModel):
    """Response from chunk search."""

    success: bool
    query: str
    school: str
    chunks: list[ChunkMatch]
    total_found: int
