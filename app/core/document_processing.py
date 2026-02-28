"""Document processing pipeline: OCR, Chunking, and Embeddings."""

from __future__ import annotations

import asyncio
import json
import time
from functools import partial
from itertools import batched
from typing import Any
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


class Chunk(BaseModel):
    """A processed chunk ready for storage."""

    index: int
    content: str
    embedding: list[float]
    metadata: dict[str, Any]


class PreprocessingResult(BaseModel):
    """Result of document preprocessing pipeline."""

    content: str
    chunks: list[Chunk]
    processing_time: float


class ChunkingService:
    """Splits markdown text into chunks using a 3-level strategy."""

    PAGE_SEPARATOR = "\n\f\n"

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
                **main_doc.metadata,  # type: ignore
                "main_chunk_tokens": main_tokens,
            }
            if main_tokens <= self.max_tokens_per_chunk:
                all_documents.append(main_doc)
                continue

            secondary_documents = self.secondary_splitter.split_text(
                main_doc.page_content
            )
            for sec_doc in secondary_documents:
                sec_tokens = self._count_tokens(sec_doc.page_content)
                sec_doc.metadata = {
                    **main_doc.metadata,  # type: ignore
                    **sec_doc.metadata,  # type: ignore
                    "secondary_chunk_tokens": sec_tokens,
                }
                if sec_tokens <= self.max_tokens_per_chunk:
                    all_documents.append(sec_doc)
                    continue

                recursive_documents = self.recursive_splitter.split_documents(
                    [sec_doc]
                )
                all_documents.extend(recursive_documents)

        # Prepend headers to chunk content for context
        for doc in all_documents:
            header_1 = doc.metadata.get("header_1")  # type: ignore
            header_2 = doc.metadata.get("header_2")  # type: ignore

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
        batch_size: int = 100,
        max_concurrent_batches: int = 5,
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

    @logfire.instrument("DocumentProcessingService.process_from_url")
    async def process_from_url(
        self,
        pdf_url: str,
        document_id: UUID,
        document_metadata: dict[str, Any] | None = None,
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
        document_metadata: dict[str, Any] | None = None,
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
        document_metadata: dict[str, Any] | None,
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
        base_metadata = document_metadata or {}
        chunks = [
            Chunk(
                index=i,
                content=lc_chunk.page_content,
                embedding=embedding,
                metadata={
                    **base_metadata,
                    **{k: v for k, v in lc_chunk.metadata.items() if isinstance(v, (str, int, float))},  # type: ignore
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

        # Batch insert
        for batch in batched(chunks_data, 100, strict=False):
            session.add_all(batch)
            await session.flush()

        logfire.info(
            "Chunks saved to database",
            document_id=str(document_id),
            chunks_saved=len(chunks_data),
        )

        return len(chunks_data)
