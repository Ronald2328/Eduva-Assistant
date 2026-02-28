"""Admin endpoints for document management."""

from uuid import UUID

import logfire
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import verify_admin
from app.core.database.database import get_db
from app.core.database.repository import DocumentRepository
from app.core.document_processing import DocumentProcessingService
from app.models.documents import (
    DocumentDeleteResponse,
    DocumentInfo,
    DocumentListResponse,
    DocumentUploadResponse,
)

router = APIRouter(prefix="/admin/documents", tags=["admin"])


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    document_name: str = Form(...),
    school: str = Form(...),
    description: str = Form(""),
    pdf_file: UploadFile = File(...),
    admin: str = Depends(verify_admin),
    session: AsyncSession = Depends(get_db),
) -> DocumentUploadResponse:
    """Upload and process a new PDF document.

    Receives a PDF file, processes it with OCR (LlamaCloud),
    splits into chunks, generates embeddings, and stores in DB.

    Args:
        document_name: Name of the document
        school: School/Faculty name
        description: Document description
        pdf_file: PDF file to process
        admin: Verified admin username
        session: Database session

    Returns:
        Upload response with document ID and chunks count
    """
    # Validate file type
    if pdf_file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are accepted",
        )

    try:
        logfire.info(
            "Document upload initiated",
            admin=admin,
            document_name=document_name,
            school=school,
            filename=pdf_file.filename,
        )

        repo = DocumentRepository(session)

        # Create document record
        document = await repo.create_document(
            nombre=document_name,
            descripcion=description,
            file_type="pdf",
            school=school,
            file_url=pdf_file.filename or "uploaded.pdf",
            is_active=True,
        )

        logfire.info(
            "Document record created, starting processing",
            document_id=str(document.id),
        )

        # Read file content
        file_content = await pdf_file.read()

        # Process: OCR → Chunks → Embeddings
        processing_service = DocumentProcessingService()
        result = await processing_service.process_from_file(
            file_content=file_content,
            document_id=document.id,
            document_metadata={
                "document_name": document_name,
                "school": school,
                "filename": pdf_file.filename or "uploaded.pdf",
            },
        )

        # Save chunks to DB
        chunks_count = await DocumentProcessingService.save_chunks(
            session=session,
            document_id=document.id,
            preprocessing_result=result,
        )

        await session.commit()

        logfire.info(
            "Document upload completed",
            document_id=str(document.id),
            chunks_created=chunks_count,
            processing_time=round(result.processing_time, 2),
        )

        return DocumentUploadResponse(
            success=True,
            document_id=document.id,
            chunks_created=chunks_count,
            processing_time_seconds=round(result.processing_time, 2),
            message=f"Document '{document_name}' processed: {chunks_count} chunks created",
        )

    except HTTPException:
        raise
    except Exception as e:
        logfire.error("Document upload failed", error=str(e), exc_info=e)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {str(e)}",
        )


@router.delete("/{document_id}", response_model=DocumentDeleteResponse)
async def delete_document(
    document_id: UUID,
    admin: str = Depends(verify_admin),
    session: AsyncSession = Depends(get_db),
) -> DocumentDeleteResponse:
    """Delete (soft delete) a document.

    Args:
        document_id: Document ID to delete
        admin: Verified admin username
        session: Database session

    Returns:
        Delete response with success status
    """
    try:
        logfire.info(
            "Document deletion initiated",
            admin=admin,
            document_id=str(document_id),
        )

        repo = DocumentRepository(session)
        success = await repo.soft_delete_document(document_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

        await session.commit()

        logfire.info("Document deleted successfully", document_id=str(document_id))

        return DocumentDeleteResponse(
            success=True,
            message="Document marked as inactive",
            document_id=document_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logfire.error("Document deletion failed", error=str(e), exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}",
        )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    admin: str = Depends(verify_admin),
    session: AsyncSession = Depends(get_db),
    school: str | None = None,
) -> DocumentListResponse:
    """List all active documents, optionally filtered by school.

    Args:
        admin: Verified admin username
        session: Database session
        school: Optional school filter

    Returns:
        List of active documents
    """
    try:
        logfire.info("Documents list requested", admin=admin, school=school)

        repo = DocumentRepository(session)
        documents = await repo.get_active_documents(school=school)

        doc_infos = [
            DocumentInfo(
                id=doc.id,
                nombre=doc.nombre,
                descripcion=doc.descripcion,
                school=doc.school,
                file_type=doc.file_type,
                chunks_count=await repo.get_chunks_count(doc.id),
                is_active=doc.is_active,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
            )
            for doc in documents
        ]

        logfire.info(
            "Documents listed successfully",
            total=len(doc_infos),
            school=school,
        )

        return DocumentListResponse(documents=doc_infos, total=len(doc_infos))

    except Exception as e:
        logfire.error("Failed to list documents", error=str(e), exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list documents: {str(e)}",
        )
