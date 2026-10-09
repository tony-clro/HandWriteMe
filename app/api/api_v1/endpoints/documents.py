import io
import os
import uuid
from pathlib import Path
import pypdf
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlmodel import Session, select

from app import actions, models
from app.api import deps
from app.core.config import settings
from app.services.storage import StorageService

router = APIRouter()

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post(
    "/",
    response_model=models.DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
def upload_document(
    file: UploadFile = File(...),
    profile_id: int | None = Form(None),
    db: Session = Depends(deps.get_session),
) -> models.DocumentRead:
    """
    Upload a PDF document, validate it, extract text, and persist metadata.
    """
    # Check optional profile_id
    if profile_id is not None:
        profile = actions.handwriting_profile_action.get(session=db, id=profile_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Handwriting profile not found",
            )

    contents = file.file.read()
    if len(contents) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds maximum allowed limit of 10MB",
        )

    # Validate PDF content header and structure
    if not (contents[:1024].find(b"%PDF-") != -1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. File is not a valid PDF document.",
        )

    try:
        pdf_stream = io.BytesIO(contents)
        reader = pypdf.PdfReader(pdf_stream)
        page_count = len(reader.pages)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or corrupted PDF document",
        )

    # Save via StorageService
    unique_filename = f"doc_{uuid.uuid4().hex}.pdf"
    file_path_str, _ = StorageService.save_file(contents, "documents", unique_filename)

    # Text extraction
    extracted_pages = []
    try:
        for page in reader.pages:
            txt = page.extract_text()
            if txt:
                extracted_pages.append(txt.strip())
    except Exception:
        pass

    full_text = "\n\n".join(extracted_pages).strip()
    doc_status = "completed" if full_text else "no_text"

    try:
        doc_in = models.DocumentCreate(
            filename=file.filename or "document.pdf",
            stored_filename=unique_filename,
            file_path=file_path_str,
            file_size=len(contents),
            status=doc_status,
            page_count=page_count,
            extracted_text=full_text,
            profile_id=profile_id,
        )
        document = actions.document_action.create(session=db, data=doc_in)
        return document
    except Exception:
        StorageService.delete_file(file_path_str)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not store document in database",
        )


@router.get(
    "/",
    response_model=list[models.DocumentRead],
)
def list_documents(
    skip: int = 0,
    limit: int = 100,
    profile_id: int | None = None,
    status: str | None = None,
    db: Session = Depends(deps.get_session),
) -> list[models.DocumentRead]:
    """
    List uploaded documents (without long extracted text).
    Supports optional filtering by profile_id and status.
    """
    statement = select(models.Document)
    if profile_id is not None:
        statement = statement.where(models.Document.profile_id == profile_id)
    if status is not None:
        statement = statement.where(models.Document.status == status)
    statement = statement.offset(skip).limit(limit)
    return db.exec(statement).all()


@router.get(
    "/{document_id}",
    response_model=models.DocumentDetailRead,
)
def get_document(
    document_id: int,
    db: Session = Depends(deps.get_session),
) -> models.DocumentDetailRead:
    """
    Retrieve document metadata and details.
    """
    document = actions.document_action.get(session=db, id=document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return document


@router.get(
    "/{document_id}/text",
    response_model=models.DocumentTextResponse,
)
def get_document_text(
    document_id: int,
    db: Session = Depends(deps.get_session),
) -> models.DocumentTextResponse:
    """
    Retrieve extracted text for a specific document.
    """
    document = actions.document_action.get(session=db, id=document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return models.DocumentTextResponse(
        id=document.id,
        status=document.status,
        page_count=document.page_count,
        extracted_text=document.extracted_text,
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_document(
    document_id: int,
    db: Session = Depends(deps.get_session),
) -> None:
    """
    Delete a document record and remove its stored file.
    """
    document = actions.document_action.get(session=db, id=document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    StorageService.delete_file(document.file_path)
    actions.document_action.delete(session=db, id=document_id)


