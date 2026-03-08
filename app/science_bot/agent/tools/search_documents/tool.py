from enum import Enum

import logfire
from langchain_core.tools import tool  # type: ignore
from langchain_core.tools.base import BaseTool
from pydantic import BaseModel

from app.science_bot.agent.tools.search_documents.service import (
    SearchDocumentsService,
    SearchDocumentsServiceResponse,
)


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
       - General search returns no relevant results
       - Question is clearly school-specific (curriculum, degree requirements)
    3. MAINTAIN SCHOOL CONTEXT: Once user mentions school, use it for all subsequent queries unless they explicitly change it
    4. DO NOT RE-ASK: Never ask for school twice in conversation
    5. ANSWER CONCISELY: No unnecessary extensions or offers of additional details

    Pipeline:
    1. Vector similarity search on chunks
    2. Retrieves top-8 most relevant document chunks (filtered by school if in context, or general info only)
    3. Generates answer based on retrieved content - INCLUDES ALL relevant information from documents
       - No preambles or padding, but COMPLETE information (all requirements, all conditions, all steps)

    Args:
        query: The user's search question, clear and specific.
               Example: "What is the cost to validate a course?" or "How much does it cost to graduate?"
        school: (Optional) The user's school or faculty FROM CONVERSATION CONTEXT.
                Use when: 1) user mentioned school (remember it), 2) question is school-specific, 3) first search had no results
                Searches results include content from that school AND general information.

    Returns:
        SearchDocumentsResponse containing success status and concise AI-generated answer (no padding).

    Behavior examples:
        - User: "How much does it cost to validate a course?"
          → Search WITHOUT school → return cost only → DONE
        - User: "What courses are in 4th semester?" → "I'm in Computer Science"
          → First search general → no match → ask "Which school?" (once) → store INFORMATICA → search with it
        - Next message: "What about 5th semester?"
          → Use INFORMATICA from context → search with school → answer
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


TOOLS: list[BaseTool] = [search_documents]
