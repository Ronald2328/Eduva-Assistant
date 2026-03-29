"""PostgreSQL service for document chunk search with vector similarity."""

from __future__ import annotations

import json
import re
from uuid import UUID

import logfire
from langchain_openai import OpenAIEmbeddings
from pydantic import BaseModel, SecretStr
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

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
    document_id: str
    document_name: str
    school: str
    chunk_index: int
    content: str
    score: float
    metadata: dict[str, str | int | float] | None = None
    is_adjacent: bool = False  # True when fetched as context neighbor, not primary match


class SearchChunksResult(BaseModel):
    """Result of chunk search."""

    matches: list[ChunkMatch]


_ARABIC_TO_ROMAN: dict[str, str] = {
    "1": "I", "2": "II", "3": "III", "4": "IV", "5": "V",
    "6": "VI", "7": "VII", "8": "VIII", "9": "IX", "10": "X",
}

_WORD_TO_ROMAN: dict[str, str] = {
    "primer": "I", "primero": "I", "primera": "I",
    "segundo": "II", "segunda": "II",
    "tercer": "III", "tercero": "III", "tercera": "III",
    "cuarto": "IV", "cuarta": "IV",
    "quinto": "V", "quinta": "V",
    "sexto": "VI", "sexta": "VI",
    "septimo": "VII", "séptimo": "VII", "septima": "VII", "séptima": "VII",
    "octavo": "VIII", "octava": "VIII",
    "noveno": "IX", "novena": "IX",
    "decimo": "X", "décimo": "X", "decima": "X", "décima": "X",
}

# Matches cycle mentions like "I ciclo", "ciclo I", "primer ciclo", "ciclo 2", "3er ciclo"
_CYCLE_RE = re.compile(
    r"(?:"
    r"(i{1,3}v?|vi{0,3}|ix|x)\s+ciclo"           # Roman + ciclo
    r"|ciclo\s+(i{1,3}v?|vi{0,3}|ix|x)\b"         # ciclo + Roman
    r"|(\d{1,2})\s*(?:er|ro|do|to|vo|mo|°)?\s*ciclo"  # digit + ciclo
    r"|ciclo\s+(\d{1,2})\b"                         # ciclo + digit
    r"|(" + "|".join(_WORD_TO_ROMAN) + r")\s+ciclo" # ordinal word + ciclo
    r")",
    re.IGNORECASE,
)


def detect_cycle_from_query(query: str) -> str | None:
    """Detect a cycle mention in a query and return Roman numeral heading text.

    Examples:
        "cursos del I ciclo"     → "I CICLO"
        "materias 3er ciclo"     → "III CICLO"
        "que hay en ciclo 2"     → "II CICLO"
        "cursos del primer ciclo" → "I CICLO"
    """
    m = _CYCLE_RE.search(query.lower())
    if not m:
        return None

    roman_direct, roman_after, digit_before, digit_after, word = m.groups()

    if roman_direct:
        return roman_direct.upper() + " CICLO"
    if roman_after:
        return roman_after.upper() + " CICLO"
    if digit_before:
        roman = _ARABIC_TO_ROMAN.get(digit_before)
        return (roman + " CICLO") if roman else None
    if digit_after:
        roman = _ARABIC_TO_ROMAN.get(digit_after)
        return (roman + " CICLO") if roman else None
    if word:
        roman = _WORD_TO_ROMAN.get(word.lower())
        return (roman + " CICLO") if roman else None

    return None


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
                    document_id=str(chunk.document_id),
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

    @logfire.instrument("PostgresService.get_adjacent_chunks")
    async def get_adjacent_chunks(
        self,
        chunk_refs: list[tuple[str, int]],  # list of (document_id, chunk_index)
    ) -> list[ChunkMatch]:
        """Fetch adjacent chunks (index ± 1) for the given document/chunk pairs.

        Used to expand context around vector-search matches so that HTML tables
        split across chunk boundaries are reconstructed.

        Args:
            chunk_refs: List of (document_id, chunk_index) from primary matches.

        Returns:
            List of adjacent ChunkMatch objects (is_adjacent=True).
        """
        if self.session is None:
            raise ValueError("Database not connected. Call connect_db() first.")

        if not chunk_refs:
            return []

        # Build conditions: for each (doc_id, idx) fetch idx-1 and idx+1
        adjacent_conditions: list[ColumnElement[bool]] = []
        for doc_id, chunk_idx in chunk_refs:
            adjacent_indices = [chunk_idx - 1, chunk_idx + 1]
            adjacent_conditions.append(
                and_(
                    DocumentChunk.document_id == UUID(doc_id),
                    DocumentChunk.chunk_index.in_(adjacent_indices),
                )
            )

        stmt = (
            select(DocumentChunk, Document.nombre, Document.school)
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(or_(*adjacent_conditions))
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        matches: list[ChunkMatch] = []
        for chunk, doc_nombre, doc_school in rows:
            metadata = None
            if chunk.chunk_metadata:
                try:
                    metadata = json.loads(chunk.chunk_metadata) if isinstance(chunk.chunk_metadata, str) else chunk.chunk_metadata
                except Exception:
                    metadata = None

            matches.append(
                ChunkMatch(
                    id=str(chunk.id),
                    document_id=str(chunk.document_id),
                    document_name=doc_nombre,
                    school=doc_school,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    score=0.0,  # Adjacent chunks have no vector score
                    metadata=metadata,
                    is_adjacent=True,
                )
            )

        logfire.info(
            "Adjacent chunks fetched",
            requested_refs=len(chunk_refs),
            adjacent_found=len(matches),
        )

        return matches

    @logfire.instrument("PostgresService.get_chunks_by_cycle_heading")
    async def get_chunks_by_cycle_heading(
        self,
        cycle_heading: str,
        school: str,
    ) -> list[ChunkMatch]:
        """Fetch chunks that contain a specific cycle heading (keyword / LIKE search).

        Used as a hybrid-search supplement when vector similarity alone fails to
        surface the actual cycle table (HTML-heavy chunks have low cosine scores).

        Args:
            cycle_heading: Heading text to look for, e.g. "### I CICLO" or "I CICLO".
            school: User's school; searches school + 'Información General'.

        Returns:
            List of ChunkMatch objects (is_adjacent=False, score=1.0 as a sentinel).
        """
        if self.session is None:
            raise ValueError("Database not connected. Call connect_db() first.")

        # Search specifically for the Markdown heading form "### N CICLO"
        # (not just any mention of "I CICLO" which would match mermaid diagrams etc.)
        heading_text = cycle_heading.lstrip("#").strip()
        # Match ### I CICLO or ## I CICLO or #### I CICLO
        search_pattern = f"%### {heading_text}%"

        stmt = (
            select(DocumentChunk, Document.nombre, Document.school)
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(
                Document.is_active == True,  # noqa: E712
                Document.school.in_([school, "Información General"]),
                DocumentChunk.content.ilike(search_pattern),
            )
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        # Pattern: heading must appear AND be followed by a <table> tag within 600 chars
        # This filters out chunks that merely END with the heading (original split boundary)
        _heading_followed_by_table = re.compile(
            rf"###\s+{re.escape(heading_text)}\s[\s\S]{{0,600}}<table",
            re.IGNORECASE,
        )

        matches: list[ChunkMatch] = []
        for chunk, doc_nombre, doc_school in rows:
            # Skip chunks where the heading is only at the end (not followed by a table)
            if not _heading_followed_by_table.search(chunk.content):
                continue

            metadata = None
            if chunk.chunk_metadata:
                try:
                    metadata = (
                        json.loads(chunk.chunk_metadata)
                        if isinstance(chunk.chunk_metadata, str)
                        else chunk.chunk_metadata
                    )
                except Exception:
                    metadata = None

            matches.append(
                ChunkMatch(
                    id=str(chunk.id),
                    document_id=str(chunk.document_id),
                    document_name=doc_nombre,
                    school=doc_school,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    score=1.0,  # Sentinel: exact keyword match
                    metadata=metadata,
                    is_adjacent=False,
                )
            )

        logfire.info(
            "Cycle heading keyword search",
            cycle_heading=heading_text,
            school=school,
            found=len(matches),
        )

        return matches

    async def close_connection(self) -> None:
        """Close database session."""
        if self.session:
            await self.session.close()
            self.session = None
