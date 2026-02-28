"""PostgreSQL service for document chunk search with vector similarity."""

from __future__ import annotations

import json

import logfire
from langchain_openai import OpenAIEmbeddings
from pydantic import BaseModel, SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database.database import AsyncSessionLocal
from app.core.database.models import Document, DocumentChunk


class DocumentInfo(BaseModel):
    """Information about a document."""

    id: str
    name: str
    description: str
    type: str


class DocumentsResult(BaseModel):
    """Result of document search by school."""

    documents: list[DocumentInfo]


class ChunkMatch(BaseModel):
    """A chunk that matches the search query."""

    id: str
    document_name: str
    school: str
    chunk_index: int
    content: str
    score: float
    metadata: dict[str, str | int | float] | None = None


class SearchChunksResult(BaseModel):
    """Result of chunk search."""

    matches: list[ChunkMatch]


class PostgresService:
    """PostgreSQL service for document chunk search with vector similarity."""

    def __init__(self) -> None:
        self.embedding = OpenAIEmbeddings(
            api_key=SecretStr(settings.OPENAI_API_KEY),
            model=settings.OPENAI_EMBEDDING_MODEL,
        )
        self.session: AsyncSession | None = None

    async def connect_db(self) -> AsyncSession:
        """Create database session."""
        self.session = AsyncSessionLocal()
        return self.session

    async def query_to_embedding(self, query: str) -> list[float]:
        """Convert text query to embedding vector."""
        return await self.embedding.aembed_query(query)

    async def get_documents_by_school(self, school: str) -> DocumentsResult:
        """Get all active documents from a school.

        Args:
            school: School name

        Returns:
            DocumentsResult with list of found documents
        """
        if self.session is None:
            raise ValueError("Database not connected. Call connect_db() first.")

        stmt = select(Document).where(
            Document.school == school,
            Document.is_active == True,  # noqa: E712
        )
        result = await self.session.execute(stmt)
        documents_orm = result.scalars().all()

        documents = [
            DocumentInfo(
                id=str(doc.id),
                name=doc.nombre,
                description=doc.descripcion,
                type=doc.school,
            )
            for doc in documents_orm
        ]

        return DocumentsResult(documents=documents)

    @logfire.instrument("PostgresService.search_chunks_by_school")
    async def search_chunks_by_school(
        self,
        query: str,
        school: str,
        limit: int = 5,
    ) -> SearchChunksResult:
        """Search for relevant chunks filtered by school + 'Información General'.

        Directly searches chunks via vector similarity, filtering by
        the user's school AND universal 'Información General' documents.

        Args:
            query: Search text
            school: User's school (e.g., 'Ingeniería Informática')
            limit: Maximum number of results

        Returns:
            SearchChunksResult with best matching chunks
        """
        if self.session is None:
            raise ValueError("Database not connected. Call connect_db() first.")

        query_embedding = await self.query_to_embedding(query)

        # Vector search with school filter: user's school + "Información General"
        stmt = (
            select(
                DocumentChunk,
                Document.nombre,
                Document.school,
                (DocumentChunk.embedding.cosine_distance(query_embedding)).label("distance"),
            )
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(
                Document.is_active == True,  # noqa: E712
                Document.school.in_([school, "Información General"]),
            )
            .order_by("distance")
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        matches: list[ChunkMatch] = []
        for chunk, doc_nombre, doc_school, distance in rows:
            similarity_score = 1 - (distance / 2)

            metadata = None
            if chunk.chunk_metadata:
                try:
                    metadata = json.loads(chunk.chunk_metadata) if isinstance(chunk.chunk_metadata, str) else chunk.chunk_metadata
                except Exception:
                    metadata = None

            matches.append(
                ChunkMatch(
                    id=str(chunk.id),
                    document_name=doc_nombre,
                    school=doc_school,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    score=similarity_score,
                    metadata=metadata,
                )
            )

        logfire.info(
            "Chunk search completed",
            school=school,
            query_length=len(query),
            results_count=len(matches),
            avg_score=round(sum(m.score for m in matches) / len(matches), 4) if matches else 0,
        )

        return SearchChunksResult(matches=matches)

    async def close_connection(self) -> None:
        """Close database session."""
        if self.session:
            await self.session.close()
            self.session = None
