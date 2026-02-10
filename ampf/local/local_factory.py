import os
from pathlib import Path
from typing import Callable, Optional, Type, override

from pydantic import BaseModel

from ampf.base.blob_model import BaseBlobMetadata, BlobLocation

from ..base import BaseFactory, BaseStorage
from .file_storage import StrPath
from .json_multi_files_storage import JsonMultiFilesStorage
from .json_one_file_storage import JsonOneFileStorage
from .local_blob_storage import LocalBlobStorage


class LocalFactory(BaseFactory):
    def __init__(self, root_path: StrPath):
        self._root_path = Path(os.path.abspath(root_path))

    def create_storage[T: BaseModel](
        self,
        collection_name: str,
        clazz: Type[T],
        key_name: Optional[str] = None,
        key: Optional[Callable[[T], str]] = None,
    ) -> BaseStorage[T]:
        return JsonMultiFilesStorage(
            collection_name=collection_name,
            clazz=clazz,
            key_name=key_name,
            key=key,
            root_path=self._root_path,
        )

    def create_compact_storage[T: BaseModel](
        self,
        collection_name: str,
        clazz: Type[T],
        key_name: Optional[str] = None,
        key: Optional[Callable[[T], str]] = None,
    ) -> BaseStorage[T]:
        return JsonOneFileStorage(
            collection_name=collection_name,
            clazz=clazz,
            key_name=key_name,
            key=key,
            root_path=self._root_path,
        )

    def create_blob_storage[T: BaseBlobMetadata](
        self,
        collection_name: str,
        clazz: Type[T] = BaseBlobMetadata,
        content_type: Optional[str] = None,
        bucket_name: Optional[str] = None,
    ) -> LocalBlobStorage[T]:
        root_path = Path(bucket_name) if bucket_name else self._root_path
        return LocalBlobStorage(
            collection_name, clazz, content_type, root_path=root_path / "blobs"
        )

    @override
    def create_blob_location(self, name: str, bucket: Optional[str] = None) -> BlobLocation:
        """Creates a BlobLocation object.

        Args:
            name: The name of the blob.
            bucket: The name of the bucket.
        Returns:
            The created BlobLocation object.
        """
        return BlobLocation(name=name, bucket=bucket or self._root_path.as_posix())