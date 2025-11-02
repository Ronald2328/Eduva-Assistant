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

    async def select_top_documents(
        self, query: str, documents: list[DocumentInfo], top_k: int = 2
    ) -> list[str]:
        """Select top K most relevant documents using AI.

        This method requests multiple documents in a single LLM call,
        which is more efficient than making multiple calls.

        Args:
            query: User question
            documents: List of available documents
            top_k: Number of top documents to select (default: 2)

        Returns:
            List of document names ordered by relevance (most relevant first)
        """
        documents_list = "\n\n".join(
            [
                f"Document: {doc.name}\nType: {doc.type}\nDescription: {doc.description}"
                for doc in documents
            ]
        )

        # Modified prompt to request multiple documents
        user_prompt = f"""USER QUESTION:
{query}

AVAILABLE DOCUMENTS:
{documents_list}

Select the TOP {top_k} most relevant documents to answer this question.
Return them in order of relevance (most relevant first).
Return ONLY the exact document names, one per line, without explanations or numbering."""

        messages: list[SystemMessage | HumanMessage] = [
            SystemMessage(content=DOCUMENT_SELECTOR_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]

        response = await self.llm.ainvoke(messages)
        response_text = str(response.content).strip()  # type: ignore

        # Parse response: extract document names (one per line)
        selected_docs = [
            line.strip() for line in response_text.split("\n") if line.strip()
        ]

        # Return only top_k documents
        return selected_docs[:top_k]

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
        """Complete pipeline with optimized document selection and fallback.

        This method implements a smart retry strategy:
        1. Selects TOP 2 most relevant documents in a single LLM call
        2. Tries the first document and validates result quality
        3. If quality is low (avg_score < 0.75), tries the second document
        4. Uses the best results found to generate the final answer

        Cost: Only +5 tokens compared to the original approach, as vector
        search operations don't consume OpenAI tokens.

        Args:
            query: User question
            school: School to search in
            max_pages: Maximum number of pages to consult (default: 5)

        Returns:
            Final service response with quality metrics
        """
        try:
            # Step 1: Get relevant documents
            documents = await self.get_relevant_documents(school)

            if not documents:
                return SearchDocumentsServiceResponse(
                    success=False,
                    message=f"No documents found for school: {school}",
                )

            # Step 2: Select TOP 2 documents in a single LLM call (optimized)
            selected_documents = await self.select_top_documents(
                query, documents, top_k=2
            )

            if not selected_documents:
                return SearchDocumentsServiceResponse(
                    success=False,
                    message="Could not select relevant documents for the query.",
                )

            # Step 3: Try up to 2 documents, keeping the best results
            best_pages: list[PageMatch] = []
            best_document: str | None = None
            best_avg_score = 0.0

            for doc_name in selected_documents[:2]:  # Max 2 attempts
                pages = await self.search_in_document(query, doc_name, limit=max_pages)

                if not pages:
                    continue  # Try next document

                # Calculate average relevance score
                avg_score = sum(p.score for p in pages) / len(pages)

                # If we found excellent results (>= 0.75), use immediately
                if avg_score >= 0.75:
                    best_pages = pages
                    best_document = doc_name
                    best_avg_score = avg_score
                    break  # No need to try second document

                # Keep track of the best results so far
                if avg_score > best_avg_score:
                    best_pages = pages
                    best_document = doc_name
                    best_avg_score = avg_score

            # Check if we found any valid results
            if not best_pages or best_document is None:
                return SearchDocumentsServiceResponse(
                    success=False,
                    message=f"No relevant information found in available documents for: {school}",
                    document_used=selected_documents[0] if selected_documents else None,
                )

            # Step 4: Generate final answer with the best pages found
            answer_response = await self.generate_answer(
                query, best_document, best_pages
            )

            return SearchDocumentsServiceResponse(
                success=True,
                message=answer_response.answer,
                document_used=answer_response.document_used,
                pages_count=len(best_pages),
            )

        except Exception as e:
            return SearchDocumentsServiceResponse(
                success=False, message=f"Search error: {str(e)}"
            )
