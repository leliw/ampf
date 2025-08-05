import logging
import mimetypes
import os
from datetime import datetime
from pathlib import Path
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile

from ampf.base.blob_model import BlobCreate
from ampf.fastapi import JsonStreamingResponse

from ..dependencies import AsyncFactoryDep, FactoryDep
from ..features.documents.document_model import Document, DocumentCreate, DocumentHeader, DocumentPatch
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
    document_create = DocumentCreate(name=name, content_type=content_type)
    blob_create = BlobCreate(name=file.filename, data=file.file, content_type=file.content_type)
    document = await service.post(blob_create, document_create)
    return document


@router.get("")
async def get_all_documents(service: DocumentServiceDep) -> List[DocumentHeader]:
    return JsonStreamingResponse(service.get_all())  # type: ignore


@router.get(ITEM_PATH)
async def get_document(service: DocumentServiceDep, document_id: UUID) -> Response:
    blob = await service.get(document_id)
    return Response(content=blob.data.read(), media_type=blob.content_type)


@router.get(f"{ITEM_PATH}/metadata")
async def get_metadata(service: DocumentServiceDep, document_id: UUID) -> Document:
    return service.get_meta(document_id)


@router.put(ITEM_PATH)
async def put(
    service: DocumentServiceDep,
    document_id: UUID,
    file: UploadFile,
    name: Annotated[Optional[str], Form()] = None,
    content_type: Annotated[Optional[str], Form()] = None,
) -> Document:
    document_patch = DocumentPatch(name=name, content_type=content_type)
    blob_create = BlobCreate(name=file.filename, data=file.file, content_type=file.content_type)
    document = await service.put(document_id, blob_create, document_patch)
    return document


@router.delete(ITEM_PATH)
async def delete(service: DocumentServiceDep, document_id: UUID) -> None:
    service.delete(document_id)
