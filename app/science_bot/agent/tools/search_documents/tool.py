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

    This tool intelligently searches your documents and generates comprehensive answers:
    - If the user mentions their school/faculty, include it in the search for more targeted results
    - If no school is mentioned, the tool searches general information ("Información General") automatically
    - The tool combines results from the specific school + general information for complete answers

    Pipeline:
    1. Embeds the query and performs vector similarity search
    2. Retrieves the most relevant document chunks (filtered by school if provided, or general info only)
    3. Generates a comprehensive answer based on the retrieved content

    Args:
        query: The user's search question, written as a clear, specific query that will help find relevant information.
               Example: "What are the admission requirements?" or "What is the tuition cost?"
        school: (Optional) The user's school or faculty. If provided, search results will include content from both
                that school AND general information. If not provided, only general information will be searched.
                Examples: INFORMATICA, MEDICINA, INGENIERIA_INDUSTRIAL, etc.

    Returns:
        SearchDocumentsResponse containing the success status and the AI-generated answer based on documents.

    Smart behavior examples:
        - User: "What documents do I need to enroll?"
          → Tool: Uses "Información General" (no school specified) to find enrollment requirements
        - User: "I'm in Engineering and need to know about specializations"
          → Tool: If school is known from context, searches Engineering + General; if not, searches General only
        - User: "How do I register for classes?"
          → Tool: Searches general information since this applies to all schools
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
