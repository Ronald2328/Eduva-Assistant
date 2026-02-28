"""Service for document search and answer generation using chunks."""

from __future__ import annotations

import logfire
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, SecretStr

from app.core.config import settings
from app.core.database.postgres_db import ChunkMatch, PostgresService
from app.science_bot.agent.prompts.answer_generator_prompt import (
    ANSWER_GENERATOR_SYSTEM_PROMPT,
    ANSWER_GENERATOR_USER_PROMPT_TEMPLATE,
)


class SearchDocumentsServiceResponse(BaseModel):
    """Final service response."""

    success: bool = Field(description="Indicates if search was successful")
    message: str = Field(description="Generated response or error message")
    document_used: str | None = Field(
        default=None, description="Document used (if applicable)"
    )
    chunks_count: int = Field(default=0, description="Number of chunks consulted")


class SearchDocumentsService:
    """Service for document search and answer generation.

    Simplified pipeline:
    1. Embed query → vector search chunks (school + "Información General")
    2. Generate answer from top-K chunks
    """

    def __init__(self) -> None:
        self.db_service = PostgresService()
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=SecretStr(secret_value=settings.OPENAI_API_KEY),
            temperature=settings.OPENAI_TEMPERATURE,
        )

    async def __aenter__(self) -> SearchDocumentsService:
        """Context manager entry."""
        await self.db_service.connect_db()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Context manager exit."""
        await self.db_service.close_connection()

    async def generate_answer(
        self, query: str, chunks: list[ChunkMatch]
    ) -> str:
        """Generate final answer using AI from chunk context.

        Args:
            query: User question
            chunks: Relevant chunks found

        Returns:
            Generated answer text
        """
        # Build context from chunks
        chunks_content = "\n\n---\n\n".join(
            [
                f"[Document: {chunk.document_name} | Chunk {chunk.chunk_index}]\n{chunk.content}\n(Relevance: {chunk.score:.4f})"
                for chunk in chunks
            ]
        )

        # Use the primary document name for context
        document_name = chunks[0].document_name if chunks else "Unknown"

        messages: list[SystemMessage | HumanMessage] = [
            SystemMessage(content=ANSWER_GENERATOR_SYSTEM_PROMPT),
            HumanMessage(
                content=ANSWER_GENERATOR_USER_PROMPT_TEMPLATE.format(
                    query=query,
                    document_name=document_name,
                    pages_content=chunks_content,
                )
            ),
        ]

        response = await self.llm.ainvoke(messages)
        return str(response.content).strip()  # type: ignore

    @logfire.instrument("search_and_answer")
    async def search_and_answer(
        self, query: str, school: str, max_chunks: int = 5
    ) -> SearchDocumentsServiceResponse:
        """Complete pipeline: direct chunk search → answer generation.

        1. Vector search chunks filtered by school + "Información General"
        2. If good results found, generate answer
        3. Return response

        Args:
            query: User question
            school: School to search in
            max_chunks: Maximum number of chunks to retrieve (default: 5)

        Returns:
            Final service response
        """
        try:
            # Step 1: Direct vector search on chunks
            with logfire.span("search_chunks"):
                result = await self.db_service.search_chunks_by_school(
                    query=query,
                    school=school,
                    limit=max_chunks,
                )

                logfire.info(
                    "Chunks retrieved",
                    school=school,
                    chunks_found=len(result.matches),
                )

                if not result.matches:
                    return SearchDocumentsServiceResponse(
                        success=False,
                        message=f"No relevant information found for school: {school}",
                    )

            # Step 2: Generate answer from chunks
            with logfire.span("generate_answer"):
                avg_score = sum(m.score for m in result.matches) / len(result.matches)
                logfire.info(
                    "Generating answer",
                    chunks_count=len(result.matches),
                    avg_score=round(avg_score, 4),
                )

                answer = await self.generate_answer(query, result.matches)

                # Get primary document used
                document_used = result.matches[0].document_name

                logfire.info(
                    "Answer generated successfully",
                    document=document_used,
                    chunks_used=len(result.matches),
                    avg_score=round(avg_score, 4),
                )

            return SearchDocumentsServiceResponse(
                success=True,
                message=answer,
                document_used=document_used,
                chunks_count=len(result.matches),
            )

        except Exception as e:
            logfire.error("Search and answer pipeline failed", error=str(e), exc_info=e)
            return SearchDocumentsServiceResponse(
                success=False, message=f"Search error: {str(e)}"
            )
