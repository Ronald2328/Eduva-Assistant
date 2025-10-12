from enum import Enum

from langchain_core.tools import tool  # type: ignore
from langchain_core.tools.base import BaseTool
from pydantic import BaseModel, Field

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


class SearchDocumentsRequest(BaseModel):
    query: str = Field(
        description="The user's search question, written as a well-formulated query to find relevant information in the documents."
    )
    school: SchoolEnum = Field(
        description="The specific school or faculty where the search should be performed. This field is mandatory."
    )


class SearchDocumentsResponse(BaseModel):
    success: bool
    message: str


@tool
async def search_documents(
    request: SearchDocumentsRequest,
) -> SearchDocumentsResponse:
    """
    Searches for information in academic documents from the National University of Piura.

    This tool performs a complete processing pipeline:
    1. Retrieves relevant documents from the specified school and general information sources.
    2. Selects the most appropriate document using AI.
    3. Searches for the most relevant pages within that document.
    4. Generates a comprehensive response based on the retrieved content.

    Args:
        request: Request object containing the user's query and the target school.

    Returns:
        SearchDocumentsResponse containing the generated answer.
    """
    async with SearchDocumentsService() as service:
        result: SearchDocumentsServiceResponse = await service.search_and_answer(
            query=request.query, school=request.school.value
        )

        return SearchDocumentsResponse(
            success=result.success,
            message=result.message,
        )


TOOLS: list[BaseTool] = [search_documents]
