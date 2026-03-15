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

    async def optimize_query_for_search(self, query: str) -> str:
        """Optimize user query for better semantic search.

        Reformulates the query to be more effective for embedding-based search
        by expanding keywords and making it more semantically rich.

        Args:
            query: Original user question

        Returns:
            Optimized query for semantic search
        """
        optimization_prompt = f"""Given this user question, reformulate it to be optimal for semantic/embedding search in academic documents.

Original question: "{query}"

Rules:
- Expand abbreviations and informal terms to formal academic language
- Add relevant synonyms and related terms
- Keep it concise (max 15 words)
- Focus on key concepts and keywords
- Remove filler words (cuanto, como, que, etc.)
- Use formal Spanish academic terminology

Examples:
- "cuanto cuesta la matricula?" → "costo matrícula pago derechos universidad ingresante"
- "codigo de matematica basica" → "código académico curso matemática básica plan estudios"
- "requisitos para graduarme" → "requisitos documentos graduación egresado bachiller título"
- "como hago el traslado" → "procedimiento proceso trámite traslado interno externo"

Optimized query:"""

        messages = [HumanMessage(content=optimization_prompt)]
        response = await self.llm.ainvoke(messages)
        optimized = str(response.content).strip()  # type: ignore

        logfire.info(
            "Query optimized for search",
            original_query=query,
            optimized_query=optimized,
        )

        return optimized

    async def generate_answer(
        self, query: str, chunks: list[ChunkMatch], max_chunks_for_context: int = 10
    ) -> str:
        """Generate final answer using AI from chunk context.

        Args:
            query: User question
            chunks: Relevant chunks found
            max_chunks_for_context: Maximum chunks to include in LLM context (default: 10)

        Returns:
            Generated answer text
        """
        # SAFETY: Limit chunks to prevent token overflow
        if len(chunks) > max_chunks_for_context:
            logfire.warn(
                "Truncating chunks for answer generation",
                total_chunks=len(chunks),
                max_chunks=max_chunks_for_context,
                truncated=len(chunks) - max_chunks_for_context,
            )
            chunks = chunks[:max_chunks_for_context]

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
        self, query: str, school: str, max_chunks: int = 10
    ) -> SearchDocumentsServiceResponse:
        """Complete pipeline: query optimization → chunk search → answer generation.

        1. Optimize query for better semantic search
        2. Vector search chunks filtered by school + "Información General"
        3. If good results found, generate answer
        4. Return response

        Args:
            query: User question
            school: School to search in
            max_chunks: Maximum number of chunks to retrieve (default: 10, reduced to prevent token overflow)

        Returns:
            Final service response
        """
        try:
            # Step 0: Optimize query for semantic search
            with logfire.span("optimize_query"):
                optimized_query = await self.optimize_query_for_search(query)

            # Step 1: Vector search on chunks with optimized query
            with logfire.span("search_chunks"):
                result = await self.db_service.search_chunks_by_school(
                    query=optimized_query,
                    school=school,
                    limit=max_chunks,
                )

                relevant_matches = result.matches

                logfire.info(
                    "Chunks retrieved",
                    school=school,
                    chunks_found=len(result.matches),
                )

                print(f"\n{'='*60}")
                print(f"[SEARCH] School: {school} | Query: {optimized_query}")
                print(f"[SEARCH] Chunks found: {len(relevant_matches)}")
                for i, chunk in enumerate(relevant_matches):
                    print(f"  [{i+1}] doc='{chunk.document_name}' chunk_idx={chunk.chunk_index} score={chunk.score:.4f}")
                    print(f"       preview: {chunk.content[:120].replace(chr(10), ' ')!r}")
                print(f"{'='*60}\n")

                if not relevant_matches:
                    # Special message when searching in general info without school context
                    if school == "Información General":
                        return SearchDocumentsServiceResponse(
                            success=False,
                            message="No information found in general documents. This information may be available in school-specific documents. You need to ask the user which school they belong to in order to search more specifically.",
                        )
                    return SearchDocumentsServiceResponse(
                        success=False,
                        message=f"No relevant information found for school: {school}",
                    )

            # Step 2: Generate answer from relevant chunks only
            with logfire.span("generate_answer"):
                logfire.info(
                    "Generating answer",
                    chunks_count=len(relevant_matches),
                )

                answer = await self.generate_answer(query, relevant_matches)

                # Check if answer generator couldn't find the information in chunks
                if answer.strip() == "INSUFFICIENT_CONTEXT":
                    logfire.info(
                        "Answer generator could not find information in chunks",
                        school=school,
                        chunks_used=len(relevant_matches),
                    )
                    # Treat as if no relevant information found
                    if school == "Información General":
                        return SearchDocumentsServiceResponse(
                            success=False,
                            message="No information found in general documents. This information may be available in school-specific documents. You need to ask the user which school they belong to in order to search more specifically.",
                        )
                    return SearchDocumentsServiceResponse(
                        success=False,
                        message=f"No relevant information found for school: {school}",
                    )

                # Get primary document used
                document_used = relevant_matches[0].document_name

                logfire.info(
                    "Answer generated successfully",
                    document=document_used,
                    chunks_used=len(relevant_matches),
                )

            return SearchDocumentsServiceResponse(
                success=True,
                message=answer,
                document_used=document_used,
                chunks_count=len(relevant_matches),
            )

        except Exception as e:
            logfire.error("Search and answer pipeline failed", error=str(e), exc_info=e)
            return SearchDocumentsServiceResponse(
                success=False, message=f"Search error: {str(e)}"
            )
