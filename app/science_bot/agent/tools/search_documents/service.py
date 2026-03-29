"""Service for document search and answer generation using chunks."""

from __future__ import annotations

from enum import Enum

import logfire
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, SecretStr

from app.core.config import settings
from app.core.database.postgres_db import ChunkMatch, PostgresService, detect_cycle_from_query
from app.science_bot.agent.prompts.answer_generator_prompt import (
    ANSWER_GENERATOR_SYSTEM_PROMPT,
    ANSWER_GENERATOR_USER_PROMPT_TEMPLATE,
)


class SearchDocumentsServiceResponse(BaseModel):
    """Final service response."""

    success: bool = Field(description="Indicates if search was successful")
    message: str = Field(description="Generated response or error message")
    reason_code: str = Field(
        default="OK",
        description="Structured reason code: OK, NEEDS_SCHOOL, NO_RESULTS, ERROR",
    )
    requires_school: bool = Field(
        default=False,
        description="Whether the assistant must ask the user for school context.",
    )
    document_used: str | None = Field(
        default=None, description="Document used (if applicable)"
    )
    chunks_count: int = Field(default=0, description="Number of chunks consulted")


class SearchReasonCode(str, Enum):
    OK = "OK"
    NEEDS_SCHOOL = "NEEDS_SCHOOL"
    NO_RESULTS = "NO_RESULTS"
    ERROR = "ERROR"


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
- CRITICAL: If the query is about courses, cycles, credits, or study plan (plan de estudios),
  do NOT add graduation-related terms like "requisitos", "graduación", "bachiller", "titulación".
  Keep the query focused on the specific cycle/semester and course content only.
Examples:
- "cuanto cuesta la matricula?" → "costo matrícula pago derechos universidad ingresante"
- "codigo de matematica basica" → "código académico curso matemática básica plan estudios"
- "requisitos para graduarme" → "requisitos documentos graduación egresado bachiller título"
- "como hago el traslado" → "procedimiento proceso trámite traslado interno externo"
- "cursos del v ciclo" → "cursos V ciclo plan estudios asignaturas semestre"
- "materias del tercer semestre" → "cursos III ciclo asignaturas semestre plan estudios"
- "que cursos hay en el 4to ciclo" → "cursos IV ciclo asignaturas plan estudios carrera"
- "cursos del i ciclo biologia" → "cursos I ciclo asignaturas plan estudios biología"

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
        self, query: str, chunks: list[ChunkMatch], max_chunks_for_context: int = 15
    ) -> str:
        """Generate final answer using AI from chunk context.

        Chunks are sorted by (document_id, chunk_index) so that adjacent chunks
        appear in reading order, which helps the LLM reconstruct split HTML tables.

        Args:
            query: User question
            chunks: Relevant chunks (primary + adjacent) found
            max_chunks_for_context: Maximum chunks to include in LLM context (default: 15)

        Returns:
            Generated answer text
        """
        # Sort by document + position so tables read in order
        sorted_chunks = sorted(chunks, key=lambda c: (c.document_id, c.chunk_index))

        # SAFETY: Limit chunks to prevent token overflow
        if len(sorted_chunks) > max_chunks_for_context:
            logfire.warn(
                "Truncating chunks for answer generation",
                total_chunks=len(sorted_chunks),
                max_chunks=max_chunks_for_context,
                truncated=len(sorted_chunks) - max_chunks_for_context,
            )
            sorted_chunks = sorted_chunks[:max_chunks_for_context]

        # Build context from chunks; mark adjacent ones clearly
        def chunk_label(chunk: ChunkMatch) -> str:
            if chunk.is_adjacent:
                tag = "context"
            elif chunk.score == 1.0:
                tag = "keyword-match"
            else:
                tag = f"score={chunk.score:.4f}"
            return f"[Document: {chunk.document_name} | Chunk {chunk.chunk_index} | {tag}]\n{chunk.content}"

        chunks_content = "\n\n---\n\n".join([chunk_label(c) for c in sorted_chunks])

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
        """Complete pipeline: query optimization → chunk search → answer generation.

        1. Optimize query for better semantic search
        2. Vector search: top-5 most relevant chunks (filtered by school + "Información General")
        3. Expand with adjacent chunks (index ± 1) to reconstruct split HTML tables
        4. Generate answer from merged context
        5. Return response

        Args:
            query: User question
            school: School to search in
            max_chunks: Top-K vector search results (default: 5). Adjacent chunks are added on top.

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

                primary_matches = result.matches

                logfire.info(
                    "Primary chunks retrieved",
                    school=school,
                    chunks_found=len(primary_matches),
                )

            # Step 1b: Cycle heading keyword lookup (hybrid search)
            # HTML-heavy table chunks have low vector similarity even when they
            # are the exact answer. We detect cycle mentions in the original
            # query and fetch those chunks by keyword so they are never missed.
            cycle_heading = detect_cycle_from_query(query)
            keyword_matches: list[ChunkMatch] = []
            if cycle_heading:
                with logfire.span("cycle_heading_keyword_search"):
                    keyword_matches = await self.db_service.get_chunks_by_cycle_heading(
                        cycle_heading, school
                    )
                    logfire.info(
                        "Cycle keyword matches",
                        cycle_heading=cycle_heading,
                        found=len(keyword_matches),
                    )

            # Step 1c: Expand with adjacent chunks to reconstruct split tables
            with logfire.span("expand_adjacent_chunks"):
                # When we have keyword matches (exact cycle table chunks), prioritize
                # them and reduce vector noise: keep only top-2 vector results instead of 5.
                if keyword_matches:
                    effective_primary = primary_matches[:2] + keyword_matches
                else:
                    effective_primary = primary_matches

                all_primary = effective_primary
                primary_keys = {(m.document_id, m.chunk_index) for m in all_primary}

                chunk_refs = [(m.document_id, m.chunk_index) for m in all_primary]
                adjacent_chunks = await self.db_service.get_adjacent_chunks(chunk_refs)

                new_adjacent = [
                    c for c in adjacent_chunks
                    if (c.document_id, c.chunk_index) not in primary_keys
                ]

                relevant_matches = all_primary + new_adjacent

                logfire.info(
                    "Chunks after adjacent expansion",
                    primary=len(primary_matches),
                    keyword=len(keyword_matches),
                    adjacent_added=len(new_adjacent),
                    total=len(relevant_matches),
                )

                if not relevant_matches:
                    # Special message when searching in general info without school context
                    if school == "Información General":
                        return SearchDocumentsServiceResponse(
                            success=False,
                            message="No information found in general documents. This information may be available in school-specific documents. You need to ask the user which school they belong to in order to search more specifically.",
                            reason_code=SearchReasonCode.NEEDS_SCHOOL.value,
                            requires_school=True,
                        )
                    return SearchDocumentsServiceResponse(
                        success=False,
                        message=f"No relevant information found for school: {school}",
                        reason_code=SearchReasonCode.NO_RESULTS.value,
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
                            reason_code=SearchReasonCode.NEEDS_SCHOOL.value,
                            requires_school=True,
                        )
                    return SearchDocumentsServiceResponse(
                        success=False,
                        message=f"No relevant information found for school: {school}",
                        reason_code=SearchReasonCode.NO_RESULTS.value,
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
                reason_code=SearchReasonCode.OK.value,
                document_used=document_used,
                chunks_count=len(relevant_matches),
            )

        except Exception as e:
            logfire.error("Search and answer pipeline failed", error=str(e), exc_info=e)
            return SearchDocumentsServiceResponse(
                success=False,
                message=f"Search error: {str(e)}",
                reason_code=SearchReasonCode.ERROR.value,
            )
