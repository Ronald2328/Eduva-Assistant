from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, SecretStr

from app.core.config import settings
from app.core.mongo_db import DocumentInfo, MongoDBService, PageMatch
from app.science_bot.agent.prompts.answer_generator_prompt import (
    ANSWER_GENERATOR_SYSTEM_PROMPT,
    ANSWER_GENERATOR_USER_PROMPT_TEMPLATE,
)
from app.science_bot.agent.prompts.document_selector_prompt import (
    DOCUMENT_SELECTOR_SYSTEM_PROMPT,
    DOCUMENT_SELECTOR_USER_PROMPT_TEMPLATE,
)


class AnswerGenerationResponse(BaseModel):
    """Response from answer generation."""

    answer: str = Field(description="Generated answer")
    document_used: str = Field(description="Source document used")
    pages_referenced: list[int] = Field(description="Referenced page numbers")


class SearchDocumentsServiceResponse(BaseModel):
    """Final service response."""

    success: bool = Field(description="Indicates if search was successful")
    message: str = Field(description="Generated response or error message")
    document_used: str | None = Field(
        default=None, description="Document used (if applicable)"
    )
    pages_count: int = Field(default=0, description="Number of pages consulted")


class SearchDocumentsService:
    """Service for document search and answer generation."""

    def __init__(self):
        self.mongo_service = MongoDBService()
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=SecretStr(secret_value=settings.OPENAI_API_KEY),
            temperature=settings.OPENAI_TEMPERATURE,
        )

    async def __aenter__(self) -> SearchDocumentsService:
        """Context manager entry."""
        await self.mongo_service.connect_db()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Context manager exit."""
        await self.mongo_service.close_connection()

    async def get_relevant_documents(self, school: str) -> list[DocumentInfo]:
        """Get relevant documents from school and General Information.

        Args:
            school: School name

        Returns:
            List of documents with their descriptions
        """
        school_docs = await self.mongo_service.get_documents_by_school(school)
        general_docs = await self.mongo_service.get_documents_by_school(
            "Información General"
        )

        all_documents = school_docs.documents + general_docs.documents
        return all_documents

    async def select_best_document(
        self, query: str, documents: list[DocumentInfo]
    ) -> str:
        """Select best document using AI.

        Args:
            query: User question
            documents: List of available documents

        Returns:
            Name of selected document
        """
        documents_list = "\n\n".join(
            [
                f"Document: {doc.name}\nType: {doc.type}\nDescription: {doc.description}"
                for doc in documents
            ]
        )

        messages: list[SystemMessage | HumanMessage] = [
            SystemMessage(content=DOCUMENT_SELECTOR_SYSTEM_PROMPT),
            HumanMessage(
                content=DOCUMENT_SELECTOR_USER_PROMPT_TEMPLATE.format(
                    query=query, documents_list=documents_list
                )
            ),
        ]

        response = await self.llm.ainvoke(messages)
        selected_document = str(response.content).strip()  # type: ignore
        return selected_document

    async def search_in_document(
        self, query: str, document_name: str, limit: int = 10
    ) -> list[PageMatch]:
        """Search in selected document.

        Args:
            query: User question
            document_name: Document name to search in
            limit: Maximum number of pages to return

        Returns:
            List of relevant pages
        """
        result = await self.mongo_service.search_best_matches(
            query=query, document_name=document_name, limit=limit
        )
        return result.matches

    async def generate_answer(
        self, query: str, document_name: str, pages: list[PageMatch]
    ) -> AnswerGenerationResponse:
        """Generate final answer using AI.

        Args:
            query: User question
            document_name: Document name used
            pages: Relevant pages found

        Returns:
            Generated response
        """
        pages_content = "\n\n---\n\n".join(
            [
                f"[Page {page.page}]\n{page.text}\n(Relevance: {page.score:.4f})"
                for page in pages
            ]
        )

        messages: list[SystemMessage | HumanMessage] = [
            SystemMessage(content=ANSWER_GENERATOR_SYSTEM_PROMPT),
            HumanMessage(
                content=ANSWER_GENERATOR_USER_PROMPT_TEMPLATE.format(
                    query=query,
                    document_name=document_name,
                    pages_content=pages_content,
                )
            ),
        ]

        response = await self.llm.ainvoke(messages)
        pages_referenced = [page.page for page in pages]

        return AnswerGenerationResponse(
            answer=str(response.content).strip(),  # type: ignore
            document_used=document_name,
            pages_referenced=pages_referenced,
        )

    async def search_and_answer(
        self, query: str, school: str, max_pages: int = 5
    ) -> SearchDocumentsServiceResponse:
        """Complete pipeline: search and answer generation.

        Args:
            query: User question
            school: School to search in
            max_pages: Maximum number of pages to consult

        Returns:
            Final service response
        """
        try:
            # Step 1: Get relevant documents
            documents = await self.get_relevant_documents(school)

            if not documents:
                return SearchDocumentsServiceResponse(
                    success=False,
                    message=f"No documents found for school: {school}",
                )

            # Step 2: Select best document
            selected_document = await self.select_best_document(query, documents)

            # Step 3: Search in selected document
            pages = await self.search_in_document(
                query, selected_document, limit=max_pages
            )

            if not pages:
                return SearchDocumentsServiceResponse(
                    success=False,
                    message=f"No relevant information found in selected document: {selected_document}",
                    document_used=selected_document,
                )

            # Step 4: Generate final answer
            answer_response = await self.generate_answer(
                query, selected_document, pages
            )

            return SearchDocumentsServiceResponse(
                success=True,
                message=answer_response.answer,
                document_used=answer_response.document_used,
                pages_count=len(pages),
            )

        except Exception as e:
            return SearchDocumentsServiceResponse(
                success=False, message=f"Search error: {str(e)}"
            )
