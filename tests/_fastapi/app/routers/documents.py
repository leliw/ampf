import logging
import mimetypes
import os
from datetime import datetime
from pathlib import Path
from typing import Annotated, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ampf.base import Blob
from ampf.base.blob_model import BlobCreate
from ampf.fastapi import JsonStreamingResponse

from ..dependencies import AsyncFactoryDep, FactoryDep
from ..features.documents.document_model import Document, DocumentCreate, DocumentHeader
from ..features.documents.document_service import DocumentService

router = APIRouter(tags=["Documents"])
ITEM_PATH = "/{document_id}"

_log = logging.getLogger(__name__)

def get_document_service(factory: FactoryDep, async_factory: AsyncFactoryDep):
    return DocumentService(factory, async_factory)


DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]


@router.post("")
async def upload_document(
    service: DocumentServiceDep,
    file: UploadFile,
    name: Annotated[str, Form()],
    content_type: Annotated[Optional[str], Form()] = None,
) -> Document:
    _log.warning(file)
    
    document_create = DocumentCreate(name=name, content_type=content_type)
    blob_create = BlobCreate(name=file.filename, data=file.file, content_type=file.content_type)
    document = await service.post(blob_create, document_create)
    return document


@router.get("")
async def get_all_documents(service: DocumentServiceDep) -> List[DocumentHeader]:
    return JsonStreamingResponse(service.get_all())  # type: ignore


@router.get(ITEM_PATH)
async def get_document(service: DocumentServiceDep, document_id: UUID) -> Document:
    return service.get(document_id)


@router.put(ITEM_PATH)
async def update_document(
    service: DocumentServiceDep,
    document_id: UUID,
    file: UploadFile = File(...),
) -> DocumentHeader:
    existing_document = service.get(document_id)
    if not existing_document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete old file
    old_file_path = Path(existing_document.storage_path)
    if old_file_path.exists():
        os.remove(old_file_path)

    # Determine new file type and content type
    file_type = "unknown"
    content_type = file.content_type or "application/octet-stream"

    if "word" in content_type or file.filename.endswith((".doc", ".docx")):
        file_type = "word"
    elif "pdf" in content_type or file.filename.endswith(".pdf"):
        file_type = "pdf"
    elif "markdown" in content_type or file.filename.endswith((".md", ".markdown")):
        file_type = "markdown"
    elif "text" in content_type:
        file_type = "text"
    else:
        mime_type, _ = mimetypes.guess_type(file.filename)
        if mime_type:
            content_type = mime_type
            if "word" in mime_type:
                file_type = "word"
            elif "pdf" in mime_type:
                file_type = "pdf"
            elif "markdown" in mime_type:
                file_type = "markdown"
            elif "text" in mime_type:
                file_type = "text"

    # Update document metadata
    existing_document.filename = file.filename
    existing_document.file_type = file_type
    existing_document.content_type = content_type
    existing_document.updated_at = datetime.now()

    # Define new storage path
    storage_filename = f"{existing_document.id}_{file.filename}"
    new_storage_path = STORAGE_DIR / storage_filename
    existing_document.storage_path = str(new_storage_path)

    # Save the new file to disk
    try:
        with open(new_storage_path, "wb") as buffer:
            while contents := file.file.read(1024 * 1024):
                buffer.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save new file: {e}")

    # Update document metadata in storage
    service.put(document_id, Document(**existing_document.model_dump()))

    return existing_document


@router.delete(ITEM_PATH)
async def delete_document(service: DocumentServiceDep, document_id: UUID) -> None:
    document = service.get(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete file from disk
    file_path = Path(document.storage_path)
    if file_path.exists():
        os.remove(file_path)

    # Delete document metadata
    service.delete(document_id)
