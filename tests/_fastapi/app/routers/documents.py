import logging
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Form, Response, UploadFile

from ampf.base.blob_model import BlobCreate
from ampf.fastapi import JsonStreamingResponse

from ..dependencies import AsyncFactoryDep
from ..features.documents.document_model import Document, DocumentCreate, DocumentPatch
from ..features.documents.document_service import DocumentService

router = APIRouter(tags=["Documents"])
ITEM_PATH = "/{document_id}"

_log = logging.getLogger(__name__)


def get_document_service(async_factory: AsyncFactoryDep):
    return DocumentService(async_factory)


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
    document = await service.post(document_create, blob_create)
    return document


@router.get("")
async def get_all_documents(service: DocumentServiceDep) -> List[Document]:
    return JsonStreamingResponse(service.get_all())  # type: ignore


@router.get(ITEM_PATH)
async def get(service: DocumentServiceDep, document_id: UUID) -> Response:
    blob = await service.get(document_id)
    return Response(
        content=blob.content,
        media_type=blob.content_type,
        headers={"Content-Disposition": f'attachment; filename="{blob.name}"'},
    )


@router.get(f"{ITEM_PATH}/metadata")
async def get_metadata(service: DocumentServiceDep, document_id: UUID) -> Document:
    return await service.get_meta(document_id)


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


@router.patch(ITEM_PATH)
async def patch(
    service: DocumentServiceDep,
    document_id: UUID,
    document_patch: DocumentPatch,
) -> Document:
    return await service.patch(document_id, document_patch)


@router.delete(ITEM_PATH)
async def delete(service: DocumentServiceDep, document_id: UUID) -> None:
    await service.delete(document_id)
