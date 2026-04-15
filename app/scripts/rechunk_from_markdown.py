"""Regenerate document chunks from a saved OCR markdown snapshot."""

from __future__ import annotations

import argparse
import asyncio
import time
from pathlib import Path
from uuid import UUID

import logfire

from app.core.database.database import AsyncSessionLocal
from app.core.database.repository import DocumentRepository
from app.core.document_processing import DocumentProcessingService


async def rechunk_document(document_id: UUID, markdown_path: Path) -> None:
    if not markdown_path.exists():
        raise FileNotFoundError(f"Markdown snapshot not found: {markdown_path}")

    markdown_text = markdown_path.read_text(encoding="utf-8")
    processing_service = DocumentProcessingService()

    async with AsyncSessionLocal() as session:
        repo = DocumentRepository(session)
        document = await repo.get_document_by_id(document_id)
        if not document:
            raise ValueError(f"Document not found: {document_id}")

        started_at = time.time()

        # Rebuild chunks + embeddings from saved OCR markdown (skip OCR step).
        preprocessing = await processing_service._process_markdown(
            markdown_text=markdown_text,
            document_id=document_id,
            document_metadata={
                "document_name": document.nombre,
                "school": document.school,
                "filename": document.file_url,
            },
            start_time=started_at,
        )

        deleted = await repo.delete_chunks_by_document(document_id)
        created = await DocumentProcessingService.save_chunks(
            session=session,
            document_id=document_id,
            preprocessing_result=preprocessing,
        )
        await session.commit()

    logfire.info(
        "Rechunk completed from markdown snapshot",
        document_id=str(document_id),
        markdown_path=str(markdown_path),
        deleted_chunks=deleted,
        created_chunks=created,
    )
    print(
        f"Rechunk OK | document_id={document_id} | deleted={deleted} | created={created} | markdown={markdown_path}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Regenerate chunks for a document from OCR markdown."
    )
    parser.add_argument("document_id", type=UUID, help="Document UUID")
    parser.add_argument(
        "--markdown-path",
        type=Path,
        default=None,
        help="Path to markdown snapshot (default: tmp/ocr_markdown/<document_id>.md)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    markdown_path = args.markdown_path or Path("tmp/ocr_markdown") / f"{args.document_id}.md"
    asyncio.run(rechunk_document(args.document_id, markdown_path))


if __name__ == "__main__":
    main()
