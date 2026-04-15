"""Document processing pipeline: OCR, Chunking, and Embeddings."""

from __future__ import annotations

import asyncio
import json
import re
import time
from collections.abc import Mapping
from functools import partial
from itertools import batched
from pathlib import Path
from typing import cast
from uuid import UUID

import logfire
from langchain_core.documents.base import Document as LCDocument
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_text_splitters.markdown import (
    ExperimentalMarkdownSyntaxTextSplitter,
)
from pydantic import BaseModel, SecretStr
from sqlalchemy.ext.asyncio import AsyncSession
from tiktoken import Encoding, encoding_for_model

from app.core.config import settings
from app.core.database.models import DocumentChunk
from app.core.llama_cloud_service import extract_text_from_file, extract_text_from_pdf


def _count_tokens(text: str, tokenizer: Encoding) -> int:
    return len(tokenizer.encode(text))


MetadataValue = str | int | float
MetadataDict = dict[str, MetadataValue]


class Chunk(BaseModel):
    """A processed chunk ready for storage."""

    index: int
    content: str
    embedding: list[float]
    metadata: MetadataDict


class PreprocessingResult(BaseModel):
    """Result of document preprocessing pipeline."""

    content: str
    chunks: list[Chunk]
    processing_time: float


class ChunkingService:
    """Splits markdown text into chunks using a 3-level strategy."""

    PAGE_SEPARATOR = "\n\f\n"
    TABLE_BLOCK_RE = re.compile(
        r"<table[\s\S]*?</table>",
        re.IGNORECASE,
    )
    CYCLE_IN_TABLE_RE = re.compile(
        r"<(?:th|td)[^>]*>\s*([IVX]{1,4})\s+CICLO\s*</(?:th|td)>",
        re.IGNORECASE,
    )
    COURSE_CODE_IN_CELL_RE = re.compile(
        r"<(?:th|td)[^>]*>\s*[A-Z]{1,3}\s*\d{3,4}\s*</(?:th|td)>",
        re.IGNORECASE,
    )
    PAGE_NUMBER_ONLY_RE = re.compile(r"^\d{1,4}$")
    CYCLE_MARKER_START_THRESHOLD = 300

    def __init__(
        self,
        max_tokens_per_chunk: int = settings.CHUNK_SIZE_TOKENS,
        chunk_overlap: int = settings.CHUNK_OVERLAP_TOKENS,
        encoding_name: str = "gpt-4o",
    ):
        self.max_tokens_per_chunk = max_tokens_per_chunk
        self.chunk_overlap = chunk_overlap
        self._count_tokens = partial(
            _count_tokens,
            tokenizer=encoding_for_model(encoding_name),
        )
        self.main_splitter = ExperimentalMarkdownSyntaxTextSplitter(
            headers_to_split_on=[("#", "header_1")],
            strip_headers=True,
        )
        self.secondary_splitter = ExperimentalMarkdownSyntaxTextSplitter(
            headers_to_split_on=[("##", "header_2")],
            strip_headers=True,
        )
        self.recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.max_tokens_per_chunk,
            chunk_overlap=self.chunk_overlap,
            length_function=self._count_tokens,
        )

    def _metadata_copy(self, metadata: object) -> dict[str, object]:
        """Create a string-keyed metadata copy from loosely typed LangChain metadata."""
        if not isinstance(metadata, Mapping):
            return {}
        typed_metadata = cast(Mapping[object, object], metadata)
        return {str(k): v for k, v in typed_metadata.items()}

    def _extract_cycle_heading(self, table_html: str) -> str | None:
        """Extract cycle heading (e.g., 'V CICLO') from table headers/cells."""
        match = self.CYCLE_IN_TABLE_RE.search(table_html)
        if not match:
            return None
        return f"{match.group(1).upper()} CICLO"

    def _is_table_continuation(
        self,
        table_html: str,
        inherited_cycle_heading: str | None,
        text_between_tables: str,
    ) -> bool:
        """Heuristic to detect a page-split continuation of the previous cycle table."""
        if not inherited_cycle_heading:
            return False

        between = text_between_tables.strip(self.PAGE_SEPARATOR).strip()
        if between and not self.PAGE_NUMBER_ONLY_RE.fullmatch(between):
            return False

        return bool(self.COURSE_CODE_IN_CELL_RE.search(table_html))

    def _split_multi_cycle_table(
        self,
        table_html: str,
        inherited_cycle_heading: str | None,
    ) -> list[tuple[str, str | None]]:
        """Split malformed OCR tables that mix cycle boundaries in one <table> block."""
        markers = list(self.CYCLE_IN_TABLE_RE.finditer(table_html))
        if not markers:
            return [(table_html, None)]

        first_marker = markers[0]
        prefix = table_html[:first_marker.start()]
        has_course_prefix = bool(self.COURSE_CODE_IN_CELL_RE.search(prefix))

        # Typical OCR failure: continuation rows (with course codes) then a new
        # cycle marker appears later in the same table block.
        if not (
            inherited_cycle_heading
            and has_course_prefix
            and first_marker.start() > self.CYCLE_MARKER_START_THRESHOLD
        ):
            return [(table_html, None)]

        parts: list[tuple[str, str | None]] = []
        prefix_content = prefix.strip(self.PAGE_SEPARATOR).strip()
        if prefix_content:
            parts.append((prefix_content, inherited_cycle_heading))

        for i, marker in enumerate(markers):
            start = marker.start()
            end = markers[i + 1].start() if i + 1 < len(markers) else len(table_html)
            section = table_html[start:end].strip(self.PAGE_SEPARATOR).strip()
            if not section:
                continue
            cycle = f"{marker.group(1).upper()} CICLO"
            parts.append((section, cycle))

        return parts if parts else [(table_html, None)]

    def _split_table_aware(self, doc: LCDocument) -> list[LCDocument]:
        """Split one markdown document into text/table units without crossing tables.

        This avoids chunks that mix the end of one cycle table with the beginning
        of the next one.
        """
        content = doc.page_content
        matches = list(self.TABLE_BLOCK_RE.finditer(content))
        if not matches:
            return [doc]

        split_docs: list[LCDocument] = []
        last_end = 0
        last_cycle_heading: str | None = None

        for match in matches:
            raw_before = content[last_end:match.start()]
            before = raw_before.strip(self.PAGE_SEPARATOR).strip()
            if before:
                split_docs.append(
                    LCDocument(
                        page_content=before,
                        metadata=self._metadata_copy(getattr(doc, "metadata", {})),
                    )
                )

            table_html = match.group(0).strip(self.PAGE_SEPARATOR).strip()
            table_sections = self._split_multi_cycle_table(
                table_html=table_html,
                inherited_cycle_heading=last_cycle_heading,
            )

            for section_html, forced_cycle_heading in table_sections:
                cycle_heading = forced_cycle_heading or self._extract_cycle_heading(
                    section_html
                )
                if not cycle_heading and self._is_table_continuation(
                    table_html=section_html,
                    inherited_cycle_heading=last_cycle_heading,
                    text_between_tables=raw_before,
                ):
                    cycle_heading = last_cycle_heading

                table_text = (
                    f"### {cycle_heading}\n{section_html}"
                    if cycle_heading
                    else section_html
                )
                table_metadata = self._metadata_copy(getattr(doc, "metadata", {}))
                if cycle_heading:
                    table_metadata["table_cycle_heading"] = cycle_heading
                    last_cycle_heading = cycle_heading

                split_docs.append(
                    LCDocument(
                        page_content=table_text,
                        metadata=table_metadata,
                    )
                )
            last_end = match.end()

        after = content[last_end:].strip(self.PAGE_SEPARATOR).strip()
        if after:
            split_docs.append(
                LCDocument(
                    page_content=after,
                    metadata=self._metadata_copy(getattr(doc, "metadata", {})),
                )
            )

        return split_docs

    def _fit_document_size(self, doc: LCDocument) -> list[LCDocument]:
        """Ensure a document fits max token size using recursive fallback."""
        if self._count_tokens(doc.page_content) <= self.max_tokens_per_chunk:
            return [doc]
        return self.recursive_splitter.split_documents([doc])

    @logfire.instrument("ChunkingService.split")
    def split(self, markdown_text: str) -> list[LCDocument]:
        """Split markdown text into chunks using 3-level strategy.

        Level 1: Split by # headers
        Level 2: If chunk > max_tokens, split by ## headers
        Level 3: If still > max_tokens, recursive character split

        Args:
            markdown_text: The markdown text to split

        Returns:
            List of LangChain Document objects with metadata
        """
        if not markdown_text:
            return []

        all_documents: list[LCDocument] = []

        main_documents = self.main_splitter.split_text(markdown_text)
        for main_doc in main_documents:
            main_tokens = self._count_tokens(main_doc.page_content)
            main_doc.metadata = {
                **self._metadata_copy(getattr(main_doc, "metadata", {})),
                "main_chunk_tokens": main_tokens,
            }
            if main_tokens <= self.max_tokens_per_chunk:
                all_documents.extend(self._split_table_aware(main_doc))
                continue

            secondary_documents = self.secondary_splitter.split_text(
                main_doc.page_content
            )
            for sec_doc in secondary_documents:
                sec_tokens = self._count_tokens(sec_doc.page_content)
                sec_doc.metadata = {
                    **self._metadata_copy(getattr(main_doc, "metadata", {})),
                    **self._metadata_copy(getattr(sec_doc, "metadata", {})),
                    "secondary_chunk_tokens": sec_tokens,
                }
                if sec_tokens <= self.max_tokens_per_chunk:
                    all_documents.extend(self._split_table_aware(sec_doc))
                    continue

                table_aware_documents = self._split_table_aware(sec_doc)
                for table_doc in table_aware_documents:
                    all_documents.extend(self._fit_document_size(table_doc))

        # Prepend headers to chunk content for context
        for doc in all_documents:
            metadata = self._metadata_copy(getattr(doc, "metadata", {}))
            header_1 = metadata.get("header_1")
            header_2 = metadata.get("header_2")

            header_text = ""
            if header_1 and isinstance(header_1, str):
                header_text += f"# {header_1.strip(self.PAGE_SEPARATOR).strip()}\n"
            if header_2 and isinstance(header_2, str):
                header_text += f"## {header_2.strip(self.PAGE_SEPARATOR).strip()}\n"

            doc.page_content = f"{header_text}{doc.page_content.strip(self.PAGE_SEPARATOR).strip()}"

        return all_documents


class EmbeddingsService:
    """Generates embeddings using OpenAI."""

    def __init__(
        self,
        model: str = settings.OPENAI_EMBEDDING_MODEL,
        dimensions: int = settings.OPENAI_EMBEDDING_DIMENSIONS,
        batch_size: int = 10,  # Reduced from 100 to avoid token limits
        max_concurrent_batches: int = 3,  # Reduced from 5 for better rate limit control
    ):
        self.model = model
        self.dimensions = dimensions
        self.batch_size = batch_size
        self.max_concurrent_batches = max_concurrent_batches
        self._client = OpenAIEmbeddings(
            api_key=SecretStr(settings.OPENAI_API_KEY),
            model=model,
        )

    @logfire.instrument("EmbeddingsService.embed_texts")
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts.

        Processes in batches with concurrency control.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        semaphore = asyncio.Semaphore(self.max_concurrent_batches)
        batches = list(batched(texts, self.batch_size, strict=False))

        tasks = [self._embed_batch(list(batch), semaphore) for batch in batches]
        results = await asyncio.gather(*tasks)

        all_embeddings: list[list[float]] = []
        for result in results:
            all_embeddings.extend(result)
        return all_embeddings

    async def embed_query(self, text: str) -> list[float]:
        """Generate embedding for a single query text.

        Args:
            text: Query text

        Returns:
            Embedding vector
        """
        return await self._client.aembed_query(text)

    async def _embed_batch(
        self,
        texts: list[str],
        semaphore: asyncio.Semaphore,
    ) -> list[list[float]]:
        async with semaphore:
            return await self._client.aembed_documents(texts)


class DocumentProcessingService:
    """Orchestrates the full document processing pipeline.

    Pipeline: PDF → OCR (LlamaCloud) → Markdown → Chunking → Embeddings → DB
    """

    def __init__(self) -> None:
        self.chunking_service = ChunkingService()
        self.embeddings_service = EmbeddingsService()

    @staticmethod
    def _metadata_copy(metadata: object) -> dict[str, object]:
        """Create a string-keyed metadata copy from loosely typed LangChain metadata."""
        if not isinstance(metadata, Mapping):
            return {}
        typed_metadata = cast(Mapping[object, object], metadata)
        return {str(k): v for k, v in typed_metadata.items()}

    @logfire.instrument("DocumentProcessingService.process_from_url")
    async def process_from_url(
        self,
        pdf_url: str,
        document_id: UUID,
        document_metadata: Mapping[str, MetadataValue] | None = None,
    ) -> PreprocessingResult:
        """Process a PDF from URL: OCR → Chunks → Embeddings.

        Args:
            pdf_url: URL of the PDF to process
            document_id: UUID of the document record in DB
            document_metadata: Extra metadata to attach to chunks

        Returns:
            PreprocessingResult with content and chunks
        """
        start_time = time.time()

        logfire.info("Starting OCR from URL", document_id=str(document_id))
        markdown_text = await extract_text_from_pdf(source_url=pdf_url)

        return await self._process_markdown(
            markdown_text=markdown_text,
            document_id=document_id,
            document_metadata=document_metadata,
            start_time=start_time,
        )

    @logfire.instrument("DocumentProcessingService.process_from_file")
    async def process_from_file(
        self,
        file_content: bytes,
        document_id: UUID,
        document_metadata: Mapping[str, MetadataValue] | None = None,
    ) -> PreprocessingResult:
        """Process a PDF from file bytes: OCR → Chunks → Embeddings.

        Args:
            file_content: Raw PDF bytes
            document_id: UUID of the document record in DB
            document_metadata: Extra metadata to attach to chunks

        Returns:
            PreprocessingResult with content and chunks
        """
        start_time = time.time()

        logfire.info("Starting OCR from file", document_id=str(document_id))
        markdown_text = await extract_text_from_file(file_content=file_content)

        return await self._process_markdown(
            markdown_text=markdown_text,
            document_id=document_id,
            document_metadata=document_metadata,
            start_time=start_time,
        )

    async def _process_markdown(
        self,
        markdown_text: str,
        document_id: UUID,
        document_metadata: Mapping[str, MetadataValue] | None,
        start_time: float,
    ) -> PreprocessingResult:
        """Process markdown text into chunks with embeddings."""
        logfire.info(
            "OCR complete, starting chunking",
            document_id=str(document_id),
            text_length=len(markdown_text),
        )

        # Chunk in thread (CPU-bound)
        lc_chunks = await asyncio.to_thread(
            self.chunking_service.split, markdown_text
        )

        logfire.info(
            "Chunking complete, generating embeddings",
            document_id=str(document_id),
            chunks_count=len(lc_chunks),
        )

        # Generate embeddings
        texts = [chunk.page_content for chunk in lc_chunks]
        embeddings = await self.embeddings_service.embed_texts(texts)

        # Build Chunk objects
        base_metadata: MetadataDict = dict(document_metadata or {})
        chunks = [
            Chunk(
                index=i,
                content=lc_chunk.page_content,
                embedding=embedding,
                metadata={
                    **base_metadata,
                    **{
                        k: v
                        for k, v in self._metadata_copy(
                            getattr(lc_chunk, "metadata", {})
                        ).items()
                        if isinstance(v, (str, int, float))
                    },
                    "embedding_model": self.embeddings_service.model,
                },
            )
            for i, (lc_chunk, embedding) in enumerate(
                zip(lc_chunks, embeddings, strict=True)
            )
        ]

        processing_time = time.time() - start_time
        logfire.info(
            "Document processing complete",
            document_id=str(document_id),
            chunks_count=len(chunks),
            processing_time=round(processing_time, 2),
        )

        return PreprocessingResult(
            content=markdown_text,
            chunks=chunks,
            processing_time=processing_time,
        )

    @staticmethod
    async def save_markdown_snapshot(
        markdown_text: str,
        document_id: UUID,
        output_dir: str = "tmp/ocr_markdown",
    ) -> str:
        """Persist OCR markdown to disk for debugging chunking strategies.

        Args:
            markdown_text: OCR output in markdown format
            document_id: Document ID used for file naming
            output_dir: Directory where markdown snapshots are stored

        Returns:
            Absolute path to the saved markdown file
        """
        base_dir = Path(output_dir)
        await asyncio.to_thread(base_dir.mkdir, parents=True, exist_ok=True)

        file_path = base_dir / f"{document_id}.md"
        await asyncio.to_thread(file_path.write_text, markdown_text, "utf-8")

        logfire.info(
            "OCR markdown snapshot saved",
            document_id=str(document_id),
            path=str(file_path.resolve()),
            chars=len(markdown_text),
        )

        return str(file_path.resolve())

    @staticmethod
    async def save_chunks(
        session: AsyncSession,
        document_id: UUID,
        preprocessing_result: PreprocessingResult,
    ) -> int:
        """Save processed chunks to the database.

        Args:
            session: Async database session
            document_id: Document ID to associate chunks with
            preprocessing_result: Result from processing pipeline

        Returns:
            Number of chunks saved
        """
        chunks_data = [
            DocumentChunk(
                document_id=document_id,
                chunk_index=chunk.index,
                content=chunk.content,
                embedding=chunk.embedding,
                chunk_metadata=json.dumps(chunk.metadata),
            )
            for chunk in preprocessing_result.chunks
        ]

        # Batch insert in small batches — large embeddings make huge queries
        for batch in batched(chunks_data, 10, strict=False):
            session.add_all(batch)
            await session.flush()

        logfire.info(
            "Chunks saved to database",
            document_id=str(document_id),
            chunks_saved=len(chunks_data),
        )

        return len(chunks_data)
