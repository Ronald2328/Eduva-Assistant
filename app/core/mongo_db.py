from __future__ import annotations

from typing import Any

from langchain_openai import OpenAIEmbeddings
from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorCollection,
    AsyncIOMotorDatabase,
)
from pydantic import BaseModel, SecretStr

from app.core.config import settings


class DocumentInfo(BaseModel):
    """Information about a document."""

    id: str
    name: str
    description: str
    type: str


class DocumentsResult(BaseModel):
    """Result of document search by school."""

    documents: list[DocumentInfo]


class PageMatch(BaseModel):
    """Page that matches the search."""

    id: str
    file_name: str
    page: int
    text: str
    score: float


class SearchPagesResult(BaseModel):
    """Result of page search."""

    matches: list[PageMatch]


class MongoDBService:
    """MongoDB service for document and page search."""

    def __init__(self):
        self.embedding = OpenAIEmbeddings(
            api_key=SecretStr(settings.OPENAI_API_KEY),
            model=settings.OPENAI_EMBEDDING_MODEL,
        )

        self.mongo_client: AsyncIOMotorClient[Any] = AsyncIOMotorClient(
            settings.MONGO_URL
        )
        self.db: AsyncIOMotorDatabase[Any] | None = None

    async def connect_db(self) -> AsyncIOMotorDatabase[Any]:
        """Connect to MongoDB database.

        Args:
            database_name: Name of the database to connect to.

        Returns:
            MongoDB database instance
        """
        await self.mongo_client.admin.command("ping")
        self.db = self.mongo_client[settings.MONGO_DATABASE]
        return self.db

    async def query_to_embedding(self, query: str) -> list[float]:
        """Convert text query to embedding vector.

        Args:
            query: Text to convert to embedding

        Returns:
            List of floats representing the embedding vector
        """
        embedding = await self.embedding.aembed_query(query)
        return embedding

    async def get_documents_by_school(self, school: str) -> DocumentsResult:
        """Get all documents from a school with their description.

        Args:
            school: School name (document type)

        Returns:
            DocumentsResult with list of found documents
        """
        if self.db is None:
            raise ValueError("Database not connected. Call connect_db() first.")

        collection: AsyncIOMotorCollection[dict[str, Any]] = self.db[
            settings.MONGO_DOCUMENTS_COLLECTION
        ]

        cursor = collection.find({"tipo": school})
        documents: list[DocumentInfo] = []

        async for doc in cursor:  # type: ignore[misc]
            documents.append(
                DocumentInfo(
                    id=str(doc["_id"]),  # type: ignore[index]
                    name=doc.get("nombre", ""),  # type: ignore[arg-type]
                    description=doc.get("descripcion", ""),  # type: ignore[arg-type]
                    type=doc.get("tipo", ""),  # type: ignore[arg-type]
                )
            )

        return DocumentsResult(documents=documents)

    async def search_best_matches(
        self,
        query: str,
        document_name: str | None = None,
        limit: int = 10,
    ) -> SearchPagesResult:
        """Search for best matches in pages based on a query.

        Args:
            query: Search text
            document_name: Document name to filter by
            limit: Maximum number of results to return

        Returns:
            SearchPagesResult with best matches found
        """
        if self.db is None:
            raise ValueError("Database not connected. Call connect_db() first.")

        query_embedding = await self.query_to_embedding(query)

        collection: AsyncIOMotorCollection[dict[str, Any]] = self.db[
            settings.MONGO_PAGES_COLLECTION
        ]

        # Build $vectorSearch with filter
        vector_search: dict[str, Any] = {
            "index": "default",
            "queryVector": query_embedding,
            "path": "embedding",
            "numCandidates": limit * 10,
            "limit": limit,
        }

        # Add filter for document name if provided
        if document_name:
            vector_search["filter"] = {"nombre_archivo": document_name}

        pipeline: list[dict[str, Any]] = [
            {"$vectorSearch": vector_search},
            {
                "$project": {
                    "_id": 1,
                    "nombre_archivo": 1,
                    "pagina": 1,
                    "text": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]

        cursor = collection.aggregate(pipeline)
        results: list[PageMatch] = []

        async for doc in cursor:  # type: ignore[misc]
            results.append(
                PageMatch(
                    id=str(doc["_id"]),  # type: ignore[index]
                    file_name=doc.get("nombre_archivo", ""),  # type: ignore[arg-type]
                    page=doc.get("pagina", 0),  # type: ignore[arg-type]
                    text=doc.get("text", ""),  # type: ignore[arg-type]
                    score=doc.get("score", 0.0),  # type: ignore[arg-type]
                )
            )

        return SearchPagesResult(matches=results)

    async def close_connection(self) -> None:
        """Close MongoDB connection."""
        if self.mongo_client:
            self.mongo_client.close()
