from collections.abc import Iterator
from copy import copy, deepcopy
from typing import override

from ampf.base import BaseBlobStorage, KeyNotExistsException
from ampf.base.base_blob_storage import FileNameMimeType
from ampf.base.blob_model import BaseBlobMetadata, Blob, BlobLocation


class InMemoryBlobStorage[T: BaseBlobMetadata](BaseBlobStorage):
    """In memory blob storage implementation"""

    def __init__(
        self,
        bucket_name: str,
        bucket: dict[str, Blob[T]],
        collection_name: str,
        clazz: type[T] = BaseBlobMetadata,
        content_type: str | None = None,
    ):
        self.bucket_name = bucket_name
        self.bucket = bucket
        self.collection_name = collection_name.rstrip("/") + "/" if collection_name else ""
        self.clazz = clazz
        self.content_type = content_type

    def _full_path(self, blob_name: str) -> str:
        return f"{self.collection_name}{blob_name}"

    def upload(self, blob: Blob[T]) -> None:
        _ = blob.content  # Reads data from file and stores in content property
        self.bucket[self._full_path(blob.name)] = blob

    def upload_blob(self, key: str, data: bytes, metadata: T | None = None, content_type: str = "") -> None:
        metadata = metadata or self.clazz(content_type=content_type)
        blob = Blob(name=key, content=data, metadata=metadata)
        self.upload(blob)

    def download(self, key: str) -> Blob[T]:
        try:
            return deepcopy(self.bucket[self._full_path(key)])
        except KeyError:
            raise KeyNotExistsException(collection_name=self.collection_name, key=key, clazz=self.clazz)

    def download_blob(self, key: str) -> bytes:
        return copy(self.download(key).content)

    def put_metadata(self, key: str, metadata: T) -> None:
        self.download(key).metadata = metadata.model_copy(deep=True)

    def get_metadata(self, key: str) -> T:
        return copy(self.download(key).metadata)

    @override
    def exists(self, key: str) -> bool:
        full_path = self._full_path(key)
        return full_path in self.bucket

    def delete(self, key: str) -> None:
        full_path = self._full_path(key)
        if full_path not in self.bucket:
            raise KeyNotExistsException(self.collection_name, self.clazz, key)
        self.bucket.pop(full_path, None)

    def keys(self) -> Iterator[str]:
        yield from self

    def __iter__(self) -> Iterator[str]:
        i = len(self.collection_name)
        for k in self.bucket:
            if k.startswith(self.collection_name):
                yield k[i:]

    def drop(self) -> None:
        keys = list(self.keys())
        for k in keys:
            self.delete(k)

    def list_blobs(self, folder_name: str | None = None) -> Iterator[FileNameMimeType]:
        folder_name = folder_name.rstrip("/") + "/" if folder_name else ""
        i = len(folder_name)
        for k in self.keys():
            if k.startswith(folder_name):
                blob = self.bucket[self._full_path(k)]
                yield FileNameMimeType(
                    name=blob.name[i:],
                    mime_type=blob.content_type,
                )

    def move_blob(self, source_key: str, dest_key: str):
        self.bucket[self._full_path(dest_key)] = self.bucket.pop(self._full_path(source_key))

    def delete_folder(self, folder_name: str):
        folder_name = folder_name.rstrip("/") + "/" if folder_name else ""
        deletable = []
        for k in self.keys():
            if k.startswith(folder_name):
                deletable.append(k)
        for k in deletable:
            self.delete(k)

    @override
    def create_blob_location(self, name: str) -> BlobLocation:
        return BlobLocation(name=self._full_path(name), bucket=self.bucket_name)
