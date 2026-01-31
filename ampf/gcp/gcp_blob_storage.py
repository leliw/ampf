import logging
from pathlib import Path
from typing import Iterator, Optional, Type

from google.cloud import storage

from ampf.base import BaseBlobStorage, KeyNotExistsException
from ampf.base.base_blob_storage import FileNameMimeType
from ampf.base.blob_model import Blob, BaseBlobMetadata


class GcpBlobStorage[T: BaseBlobMetadata](BaseBlobStorage[T]):
    """A simple wrapper around Google Cloud Storage."""

    _storage_client = None
    _default_bucket = None

    @classmethod
    def init_client(cls, bucket_name: Optional[str] = None):
        if not cls._storage_client:
            cls._storage_client = storage.Client()
        if bucket_name:
            cls._default_bucket = cls._storage_client.bucket(bucket_name)

    def __init__(
        self,
        collection_name: str,
        clazz: Type[T] = BaseBlobMetadata,
        content_type: str = "text/plain",
        bucket_name: Optional[str] = None,
        storage_client: Optional[storage.Client] = None,
    ):
        super().__init__(collection_name, clazz, content_type)
        self._log = logging.getLogger(__name__)
        self._storage_client = storage_client or storage.Client()
        if bucket_name:
            self._bucket = self._storage_client.bucket(bucket_name)
            if not self._default_bucket:
                self._default_bucket = self._bucket
        elif self._default_bucket:
            self._bucket = self._default_bucket
        else:
            raise ValueError(
                f"No bucket specified or found for collection '{collection_name}'. Please provide a valid bucket_name."
            )

    def _get_blob(self, key: str) -> storage.Blob:
        return self._bucket.blob(f"{self.collection_name}/{key}" if self.collection_name else key)

    def _get_prefix(self, folder_name: Optional[str] = None) -> str:
        prefix = self.collection_name + "/"
        if folder_name:
            prefix += folder_name if folder_name[-1] == "/" else folder_name + "/"
        return prefix

    def upload(self, blob: Blob[T]) -> None:
        g_blob = self._get_blob(blob.name)
        if blob.metadata:
            g_blob.metadata = blob.metadata.model_dump(exclude_none=True)

        g_blob.upload_from_string(blob.content, content_type=blob.content_type or self.content_type)

    def upload_blob(
        self, key: str, data: bytes, metadata: Optional[T] = None, content_type: Optional[str] = None
    ) -> None:
        blob = self._get_blob(key)
        if metadata:
            blob.metadata = metadata.model_dump(exclude_none=True)
        blob.upload_from_string(data, content_type=content_type or self.content_type)

    def download(self, key: str) -> Blob[T]:
        g_blob = self._get_blob(key)
        if not g_blob.exists():
            raise KeyNotExistsException(self.collection_name, self.clazz, key)
        return Blob(
            name=key,
            content=g_blob.download_as_string(),
            metadata=self.get_metadata(key),
        )

    def download_blob(self, key: str) -> bytes:
        blob = self._get_blob(key)
        if not blob.exists():
            raise KeyNotExistsException(self.collection_name, self.clazz, key)
        return blob.download_as_bytes()

    def put_metadata(self, key: str, metadata: T) -> None:
        blob = self._get_blob(key)
        blob.metadata = metadata.dict()
        blob.patch()

    def get_metadata(self, key: str) -> T:
        blob = self._get_blob(key)
        if not blob.exists():
            raise KeyNotExistsException(self.collection_name, self.clazz, key)
        if not blob.metadata:
            # I don't know why, but sometimes the metadata is None (ML)
            blob.reload()
        if not blob.metadata or not self.clazz:
            raise ValueError(f"No metadata found for blob '{key}'")
        return self.clazz(**blob.metadata)

    def delete(self, key: str):
        blob = self._get_blob(key)
        if not blob.exists():
            raise KeyNotExistsException(self.collection_name, self.clazz, key)
        blob.delete()

    def keys(self) -> Iterator[str]:
        prefix = self._get_prefix()
        i = len(prefix)
        for blob in self._bucket.list_blobs(prefix=prefix):
            if not blob.name.endswith("/"):
                yield blob.name[i:]

    def list_blobs(self, folder_name: Optional[str] = None) -> Iterator[FileNameMimeType]:
        prefix = self._get_prefix(folder_name)
        i = len(prefix)
        for blob in self._bucket.list_blobs(prefix=prefix):
            yield FileNameMimeType(name=blob.name[i:], mime_type=blob.content_type)

    # Additional not tested methods

    def upload_file(self, file_path: Path, metadata: Optional[T] = None, key: Optional[str] = None):
        if not key:
            key = file_path.stem
        blob = self._get_blob(key)
        blob.upload_from_filename(file_path)
        if metadata:
            blob.metadata = metadata.model_dump()
            blob.patch()

    def download_file(self, key: str, dest_path: Path):
        blob = self._get_blob(key)
        blob.download_to_filename(dest_path)

    def get_blob(self, file_name: str):
        return self._bucket.blob(file_name)

    def get_blob_url(self, file_name: str):
        blob = self._bucket.blob(file_name)
        return blob.public_url

    def get_blob_signed_url(self, file_name: str, expiration: int):
        blob = self._bucket.blob(file_name)
        return blob.generate_signed_url(expiration=expiration, method="GET")

    def get_blob_metadata(self, file_name: str):
        blob = self._bucket.blob(file_name)
        return blob.metadata

    def set_blob_metadata(self, file_name: str, metadata: dict):
        blob = self._bucket.blob(file_name)
        blob.metadata = metadata
        blob.patch()

    def copy_blob(self, source_key: str, dest_key: str):
        source_blob = self._bucket.blob(source_key)
        new_blob = self._bucket.copy_blob(source_blob, self._bucket, dest_key)
        return new_blob

    def move_blob(self, source_key: str, dest_key: str):
        source_blob = self._get_blob(source_key)
        new_blob = self._bucket.rename_blob(source_blob, self._get_prefix() + dest_key)
        return new_blob

    def upload_blob_from_file(self, file_name: str, upload_file):  # type: ignore
        """Upload a file from an UploadFile object."""
        from fastapi import UploadFile

        upload_file: UploadFile
        blob = self._bucket.blob(file_name)
        blob.upload_from_file(upload_file.file, content_type=upload_file.content_type)

    def delete_folder(self, folder_name: str):
        prefix = self._get_prefix(folder_name)
        blobs = self._bucket.list_blobs(prefix=prefix)
        for blob in blobs:
            blob.delete()
