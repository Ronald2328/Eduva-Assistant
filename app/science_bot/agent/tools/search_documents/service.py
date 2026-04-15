"""Service for document search and answer generation using chunks."""

from __future__ import annotations

import html
import re
from enum import Enum

import logfire
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, SecretStr

from app.core.config import settings
from app.core.database.postgres_db import (
    ChunkMatch,
    PostgresService,
    detect_cycle_from_query,
)
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

    @staticmethod
    def _recompute_cycle_total_from_codes(answer: str) -> str:
        """Correct 'Total del ciclo' using D2 digit from listed course codes.

        Code convention: [PREFIX][D1][D2][D3][D4], so D2 is total credits.
        """
        if "Total del ciclo" not in answer:
            return answer

        # Extract 4-digit payload from course codes in list lines.
        # Examples matched: "CB 3347", "CB3347", "(CB 3347)".
        digit_blocks = re.findall(r"\b[A-Z]{1,4}\s?(\d{4})\b", answer, flags=re.IGNORECASE)
        if not digit_blocks:
            return answer

        recomputed_total = sum(int(block[1]) for block in digit_blocks)
        total_line_re = re.compile(
            r"(Total del ciclo(?:\s*\(según tabla\))?\s*:\s*\*?)(\d+)(\s*créditos\*?)",
            flags=re.IGNORECASE,
        )
        match = total_line_re.search(answer)
        if not match:
            return answer

        reported_total = int(match.group(2))
        if reported_total == recomputed_total:
            return answer

        corrected = total_line_re.sub(
            rf"\g<1>{recomputed_total}\g<3>",
            answer,
            count=1,
        )
        return corrected

    @staticmethod
    def _apply_single_elective_policy(answer: str) -> str:
        """When an Electivos section exists, count only one elective in cycle total.

        Policy requested by business rules:
        - Student chooses only 1 elective course.
        - Total cycle credits = mandatory credits + credits of 1 elective.
        - Credits are derived from D2 in course code.
        """
        elective_marker_re = re.compile(
            r"\(\s*e(?:lectivo)?\s*\)",
            flags=re.IGNORECASE,
        )
        if "electiv" not in answer.lower() and not elective_marker_re.search(answer):
            return answer

        lines = answer.splitlines()
        in_electives = False
        elective_heading_idx: int | None = None
        mandatory_credits: list[int] = []
        elective_credits: list[int] = []
        mandatory_items: list[str] = []
        elective_items: list[str] = []

        code_re = re.compile(r"\b[A-Z]{1,4}\s?(\d{4})\b", flags=re.IGNORECASE)
        credits_re = re.compile(r"(\d+)\s*créditos?", flags=re.IGNORECASE)
        item_re = re.compile(r"^\s*(?:\d+\.\s+|-\s+)")
        total_re = re.compile(r"Total del ciclo", flags=re.IGNORECASE)

        def credits_from_line(line: str) -> int | None:
            m = code_re.search(line)
            if m:
                return int(m.group(1)[1])

            cm = credits_re.search(line)
            if cm:
                return int(cm.group(1))

            return None

        for idx, line in enumerate(lines):
            lower = line.lower().strip()
            if not lower:
                continue
            if "electivos" in lower:
                in_electives = True
                elective_heading_idx = idx
                continue
            if total_re.search(line):
                in_electives = False
                continue
            if not item_re.match(line):
                continue

            credits = credits_from_line(line)
            if credits is None:
                continue
            if in_electives or elective_marker_re.search(line):
                elective_credits.append(credits)
                elective_items.append(line)
            else:
                mandatory_credits.append(credits)
                mandatory_items.append(line)

        if not elective_credits:
            return answer

        chosen_elective_credits = elective_credits[0]
        corrected_total = sum(mandatory_credits) + chosen_elective_credits

        # Normalize presentation: keep electives in their own section.
        if elective_items and mandatory_items:
            rebuilt_lines: list[str] = []
            course_header_written = False
            for line in lines:
                stripped = line.strip()
                if item_re.match(line):
                    # We rebuild list items below.
                    continue
                if stripped.lower().startswith("electivos"):
                    # Rebuild with normalized heading below.
                    continue
                if total_re.search(line):
                    # Keep total at the end after rebuilt sections.
                    continue
                if stripped:
                    rebuilt_lines.append(line)
                    if "ciclo" in stripped.lower() and not course_header_written:
                        course_header_written = True

            # Add mandatory numbered list
            if rebuilt_lines and rebuilt_lines[-1].strip():
                rebuilt_lines.append("")
            for idx, item in enumerate(mandatory_items, start=1):
                clean_item = re.sub(r"^\s*(?:\d+\.\s+|-\s+)", "", item).strip()
                rebuilt_lines.append(f"{idx}. {clean_item}")

            rebuilt_lines.append("")
            rebuilt_lines.append(
                f"Electivos (solo se puede elegir 1 curso de {chosen_elective_credits} créditos):"
            )
            for item in elective_items:
                clean_item = re.sub(r"^\s*(?:\d+\.\s+|-\s+)", "", item).strip()
                rebuilt_lines.append(f"- {clean_item}")

            rebuilt_lines.append("")
            rebuilt_lines.append(f"Total del ciclo (según tabla): *{corrected_total} créditos*")
            answer = "\n".join(rebuilt_lines).strip()
            return answer

        total_line_re = re.compile(
            r"(Total del ciclo(?:\s*\(según tabla\))?\s*:\s*\*?)(\d+)(\s*créditos\*?)",
            flags=re.IGNORECASE,
        )
        if total_line_re.search(answer):
            answer = total_line_re.sub(
                rf"\g<1>{corrected_total}\g<3>",
                answer,
                count=1,
            )
        else:
            answer = f"{answer.rstrip()}\n\nTotal del ciclo: *{corrected_total} créditos*"

        note_text = f"Nota: En electivos, solo se puede elegir *1 curso* ({chosen_elective_credits} créditos)."
        if "solo se puede elegir" not in answer.lower():
            lines = answer.splitlines()
            if elective_heading_idx is not None:
                insert_at = min(elective_heading_idx + 1, len(lines))
            else:
                insert_at = len(lines)
            lines.insert(insert_at, note_text)
            answer = "\n".join(lines)

        return answer

    @staticmethod
    def _replace_generic_elective_row_with_options(
        answer: str,
        chunks: list[ChunkMatch],
        cycle_heading: str | None = None,
    ) -> str:
        """Replace generic 'Curso Electivo' row with real options from chunks."""
        if not re.search(r"curso\s+electivo", answer, flags=re.IGNORECASE):
            return answer

        sorted_chunks = sorted(chunks, key=lambda c: (c.document_id, c.chunk_index))
        section_blob = ""
        anchor_indices: list[int] = []
        if cycle_heading:
            for idx, chunk in enumerate(sorted_chunks):
                if cycle_heading.upper() in chunk.content.upper():
                    anchor_indices.append(idx)

        electivo_candidates: list[int] = [
            idx
            for idx, chunk in enumerate(sorted_chunks)
            if "CURSOS ELECTIVOS" in chunk.content.upper()
        ]

        if not electivo_candidates:
            return answer

        if anchor_indices:
            # Prefer CURSOS ELECTIVOS sections that appear AFTER the queried cycle.
            anchor_idx = min(anchor_indices)
            forward_candidates = [i for i in electivo_candidates if i >= anchor_idx]
            if forward_candidates:
                target_idx = min(forward_candidates, key=lambda i: i - anchor_idx)
            else:
                target_idx = min(
                    electivo_candidates,
                    key=lambda i: min(abs(i - a) for a in anchor_indices),
                )
        else:
            target_idx = electivo_candidates[0]

        section_blob += sorted_chunks[target_idx].content + "\n"
        # Include a couple of neighbor chunks where the elective table may continue.
        for j in range(target_idx + 1, min(target_idx + 3, len(sorted_chunks))):
            if sorted_chunks[j].document_id != sorted_chunks[target_idx].document_id:
                break
            section_blob += sorted_chunks[j].content + "\n"

        if not section_blob:
            return answer

        section_upper = section_blob.upper()
        marker_pos = section_upper.find("CURSOS ELECTIVOS")
        if marker_pos != -1:
            table_start = section_upper.find("<TABLE", marker_pos)
            table_end = section_upper.find("</TABLE>", table_start) if table_start != -1 else -1
            if table_start != -1 and table_end != -1:
                section_blob = section_blob[table_start:table_end + len("</table>")]

        row_re = re.compile(r"<tr[^>]*>([\s\S]*?)</tr>", flags=re.IGNORECASE)
        cell_re = re.compile(r"<t[dh][^>]*>([\s\S]*?)</t[dh]>", flags=re.IGNORECASE)
        tag_re = re.compile(r"<[^>]+>")
        code_re = re.compile(r"^[A-Z]{1,4}\s?\d{4}$", flags=re.IGNORECASE)

        elective_options: list[tuple[str, str, int]] = []
        seen_codes: set[str] = set()

        for row_html in row_re.findall(section_blob):
            raw_cells = cell_re.findall(row_html)
            if len(raw_cells) < 2:
                continue
            cells = [
                html.unescape(tag_re.sub(" ", cell)).replace("\n", " ").strip()
                for cell in raw_cells
            ]
            cells = [re.sub(r"\s{2,}", " ", c) for c in cells]
            code = cells[0].upper()
            if not code_re.match(code):
                continue
            if code in seen_codes:
                continue
            name = cells[1].strip()
            if not name or "NOMBRE DEL CURSO" in name.upper():
                continue

            credits: int | None = None
            if len(cells) >= 6 and re.fullmatch(r"\d{1,2}", cells[5] or ""):
                credits = int(cells[5])
            if credits is None:
                digits = re.sub(r"\D", "", code)
                if len(digits) == 4:
                    credits = int(digits[1])
            if credits is None:
                continue

            seen_codes.add(code)
            elective_options.append((name, code, credits))

        if not elective_options:
            return answer

        lines = answer.splitlines()
        item_re = re.compile(r"^\s*(?:\d+\.\s+|-\s+)")
        total_re = re.compile(r"Total del ciclo", flags=re.IGNORECASE)

        cleaned_lines: list[str] = []
        for line in lines:
            if re.search(r"curso\s+electivo", line, flags=re.IGNORECASE):
                continue
            if line.strip().lower().startswith("electivos"):
                continue
            if item_re.match(line) and "(E)" in line.upper():
                continue
            cleaned_lines.append(line)

        insert_idx = next(
            (idx for idx, line in enumerate(cleaned_lines) if total_re.search(line)),
            len(cleaned_lines),
        )

        elective_credits = elective_options[0][2]
        elective_block = [
            "",
            f"Electivos (solo se puede elegir 1 curso de {elective_credits} créditos):",
        ]
        elective_block.extend(
            [f"- {name} ({code}) — {credits} créditos" for name, code, credits in elective_options]
        )
        elective_block.append("")

        rebuilt = (
            cleaned_lines[:insert_idx] + elective_block + cleaned_lines[insert_idx:]
        )
        return "\n".join(rebuilt).strip()

    @logfire.instrument("search_and_answer")
    async def search_and_answer(
        self, query: str, school: str, max_chunks: int = 5
    ) -> SearchDocumentsServiceResponse:
        """Complete pipeline: query optimization → chunk search → answer generation.

        1. Optimize query for better semantic search
        2. Vector search: top-5 most relevant chunks (filtered by school + "Información General")
        3. Expand with nearby chunks (index ± 2) to reconstruct split HTML tables
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
                    # Also fetch elective catalog sections when user asks cycle course lists.
                    # Some plans use a generic "CURSO ELECTIVO" row inside the cycle table
                    # and list real elective options in a nearby "CURSOS ELECTIVOS" section.
                    if re.search(r"\bcursos?\b|\bmaterias?\b", query, flags=re.IGNORECASE):
                        elective_heading_matches = await self.db_service.get_chunks_by_cycle_heading(
                            "CURSOS ELECTIVOS",
                            school,
                        )
                        keyword_matches.extend(elective_heading_matches)
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
                neighbor_radius = 4 if cycle_heading else 2
                adjacent_chunks = await self.db_service.get_adjacent_chunks(
                    chunk_refs, radius=neighbor_radius
                )

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
                answer = self._replace_generic_elective_row_with_options(
                    answer,
                    relevant_matches,
                    cycle_heading=cycle_heading,
                )
                answer = self._recompute_cycle_total_from_codes(answer)
                answer = self._apply_single_elective_policy(answer)

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
