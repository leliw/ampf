import logging
from typing import Annotated, Iterable

from fastapi import APIRouter, Depends, Response, UploadFile
from fastapi.responses import StreamingResponse

from ampf.base.blob_model import Blob, BlobHeader, BlobLocation
from ampf.fastapi import JsonStreamingResponse
from tests._fastapi.app.features.files.file_service import FileService

from ..dependencies import AsyncFactoryDep


router = APIRouter(tags=["Files (only blob and metadata)"])
ITEM_PATH = "/{file_name}"

_log = logging.getLogger(__name__)


def get_file_service(async_factory: AsyncFactoryDep):
    return FileService(async_factory)


FileServiceDep = Annotated[FileService, Depends(get_file_service)]


@router.post("")
async def upload(service: FileServiceDep, file: UploadFile) -> None:
    await service.upload_blob(Blob.create_from_file(file))


@router.get(ITEM_PATH)
async def download(service: FileServiceDep, file_name: str) -> Response:
    blob = await service.download_blob(BlobLocation(name=file_name))
    return StreamingResponse(
        blob.stream(),
        media_type=blob.content_type,
        headers={"Content-Disposition": f'attachment; filename="{blob.name}"'},
    )


@router.get("")
def get_all(service: FileServiceDep) -> Iterable[BlobHeader]:
    return JsonStreamingResponse(service.get_all_files())  # type: ignore


@router.delete(ITEM_PATH)
def delete(service: FileServiceDep, file_name: str):
    service.delete(file_name)
