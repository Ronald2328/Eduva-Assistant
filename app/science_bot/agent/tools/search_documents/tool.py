from enum import Enum

import logfire
from langchain_core.tools import tool  # type: ignore
from langchain_core.tools.base import BaseTool
from pydantic import BaseModel

from app.science_bot.agent.tools.search_documents.service import (
    SearchDocumentsService,
    SearchDocumentsServiceResponse,
)
from app.science_bot.agent.tools.thinking_planning import THINKING_TOOL

class SchoolEnum(str, Enum):
    ADMINISTRACION = "Ciencias Administrativas"
    AGRONOMIA = "Agronomía"
    AGRICOLA = "Ingeniería Agrícola"
    CONTABILIDAD = "Ciencias Contables y Financieras"
    ECONOMIA = "Economía"
    INDUSTRIAL = "Ingeniería Industrial"
    INFORMATICA = "Ingeniería Informática"
    AGROINDUSTRIAL = "Ingeniería Agroindustrial e Industrias Alimentarias"
    MECATRONICA = "Ingeniería Mecatrónica"
    MINAS = "Ingeniería de Minas"
    GEOLOGICA = "Ingeniería Geológica"
    PETROLEO = "Ingeniería de Petróleo"
    QUIMICA = "Ingeniería Química"
    AMBIENTAL = "Ingeniería Ambiental y Seguridad Industrial"
    PESQUERA = "Ingeniería Pesquera"
    ZOOTECNIA = "Ingeniería Zootecnia"
    VETERINARIA = "Medicina Veterinaria"
    MEDICINA = "Medicina Humana"
    ENFERMERIA = "Enfermería"
    OBSTETRICIA = "Obstetricia"
    PSICOLOGIA = "Psicología"
    ESTOMATOLOGIA = "Estomatología"
    HISTORIA = "Historia y Geografía"
    LENGUA_LITERATURA = "Lengua y Literatura"
    EDUCACION_INICIAL = "Educación Inicial"
    EDUCACION_PRIMARIA = "Educación Primaria"
    COMUNICACION = "Ciencias de la Comunicación Social"
    DERECHO = "Derecho y Ciencias Políticas"
    MATEMATICA = "Matemática"
    FISICA = "Física"
    BIOLOGIA = "Ciencias Biológicas"
    ELECTRONICA = "Ingeniería Electrónica y Telecomunicaciones"
    ESTADISTICA = "Estadística"
    CIVIL = "Ingeniería Civil"
    ARQUITECTURA = "Arquitectura y Urbanismo"


class SearchDocumentsResponse(BaseModel):
    success: bool
    message: str


@tool
async def search_documents(
    query: str,
    school: SchoolEnum | None = None,
) -> SearchDocumentsResponse:
    """
    Searches for information in academic documents from the National University of Piura.

    SMART SEARCH STRATEGY:
    1. ALWAYS try general search first (no school specified) for any query
    2. ONLY use school parameter if:
       - User explicitly mentions their school (ONE TIME: remember it for rest of conversation)
       - Tool response says "need to ask the user which school" → ASK USER FOR SCHOOL
       - Question is clearly school-specific (curriculum, degree requirements)
    3. MAINTAIN SCHOOL CONTEXT: Once user mentions school, use it for all subsequent queries unless they explicitly change it
    4. DO NOT RE-ASK: Never ask for school twice in conversation
    5. ANSWER CONCISELY: No unnecessary extensions or offers of additional details

    CRITICAL FLOW WHEN INFORMATION NOT FOUND:
    - If search result message contains "need to ask the user which school" → This means:
      1. Information exists but requires school context
      2. You MUST ask user: "¿De qué escuela eres?" (in user's language)
      3. Once user provides school, search again WITH school parameter
      4. Remember school for all future queries

    Pipeline:
    1. Query optimization for better semantic search
    2. Vector similarity search on chunks
    3. Retrieves top-10 most relevant document chunks (filtered by school if in context, or general info only)
    4. Generates answer based on retrieved content - INCLUDES ALL relevant information from documents
       - No preambles or padding, but COMPLETE information (all requirements, all conditions, all steps)

    Args:
        query: The user's search question, optimized for document search.
               IMPORTANT - NORMALIZE ACADEMIC TERMS BEFORE SEARCHING:
               - Cycle numbers MUST use Roman numerals: "segundo ciclo" → "II ciclo", "tercer ciclo" → "III ciclo",
                 "primer ciclo" → "I ciclo", "cuarto" → "IV", "quinto" → "V", "sexto" → "VI",
                 "séptimo" → "VII", "octavo" → "VIII", "noveno" → "IX", "décimo" → "X"
               - Arabic numbers also convert: "ciclo 2" → "II ciclo", "2do ciclo" → "II ciclo"
               - Keep the rest of the query natural and specific.
               Example: "cursos del II ciclo" (not "cursos del segundo ciclo" or "cursos del ciclo 2")
        school: (Optional) The user's school or faculty FROM CONVERSATION CONTEXT.
                Use when: 1) user mentioned school (remember it), 2) tool said to ask for school, 3) question is school-specific
                Searches results include content from that school AND general information.

    Returns:
        SearchDocumentsResponse containing success status and AI-generated answer.
        IMPORTANT: If message contains "need to ask the user which school" → ASK USER FOR SCHOOL

    Behavior examples:
        - User: "How much does it cost to validate a course?"
          → Search WITHOUT school → return cost only → DONE
        - User: "¿Qué cursos hay en el segundo ciclo?" / "ciclo 2" / "2do ciclo"
          → Normalize query to "cursos del II ciclo" → search with that query
        - User: "What is the academic code for basic mathematics?"
          → Search WITHOUT school → tool says "need to ask user which school" → ask "¿De qué escuela eres?"
          → User: "Matemática" → Search WITH school=MATEMATICA → return code
        - Next message: "What about 5th semester?"
          → Use MATEMATICA from context → search with school → answer
        - User: "Actually I switched to Engineering"
          → Update school to INDUSTRIAL → search with new school
    """
    try:
        school_name = school.value if school else "Información General"
        logfire.info("Tool invoked", tool="search_documents", school=school_name, query_length=len(query))

        async with SearchDocumentsService() as service:
            result: SearchDocumentsServiceResponse = await service.search_and_answer(
                query=query, school=school_name
            )

            logfire.info(
                "Tool execution completed",
                success=result.success,
                document_used=result.document_used,
                chunks_count=result.chunks_count,
            )

            return SearchDocumentsResponse(
                success=result.success,
                message=result.message,
            )
    except Exception as e:
        logfire.error("Tool execution failed", error=str(e), exc_info=e)
        return SearchDocumentsResponse(
            success=False,
            message=f"Error searching documents: {str(e)}",
        )


TOOLS: list[BaseTool] = [THINKING_TOOL, search_documents]
