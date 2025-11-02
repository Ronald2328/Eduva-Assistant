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
    school: SchoolEnum,
) -> SearchDocumentsResponse:
    """
    Searches for information in academic documents from the National University of Piura.

    IMPORTANT: Only use this tool AFTER you have confirmed which school/faculty the user is asking about.
    If the user hasn't specified their school, ask them first before calling this tool.

    This tool performs a complete processing pipeline:
    1. Retrieves relevant documents from the specified school and general information sources.
    2. Selects the most appropriate document using AI.
    3. Searches for the most relevant pages within that document.
    4. Generates a comprehensive response based on the retrieved content.

    Args:
        query: The user's search question, written as a well-formulated query to find relevant information in the documents.
        school: The specific school or faculty where the search should be performed. Must match one of the available schools in the SchoolEnum. This is REQUIRED — do not guess the school.

    Returns:
        SearchDocumentsResponse containing the success status and the generated answer based on the documents.

    Example usage:
        - User: "How much is the tuition?"
        - Assistant: "Which school/faculty are you in?"
        - User: "Computer Engineering"
        - Assistant: [calls search_documents with school=INFORMATICA and query about tuition cost]
    """
    try:
        logfire.info("Tool invoked", tool="search_documents", school=school.value, query_length=len(query))

        async with SearchDocumentsService() as service:
            result: SearchDocumentsServiceResponse = await service.search_and_answer(
                query=query, school=school.value
            )

            logfire.info(
                "Tool execution completed",
                success=result.success,
                document_used=result.document_used,
                pages_count=result.pages_count,
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
