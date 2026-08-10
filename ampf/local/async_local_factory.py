from collections.abc import Callable
from pathlib import Path
from typing import override
from warnings import deprecated

from pydantic import BaseModel

from ..base import BaseAsyncBlobStorage, BaseAsyncFactory, BaseAsyncStorage, BaseBlobMetadata
from .file_storage import StrPath
from .json_multi_files_async_storage import JsonMultiFilesAsyncStorage
from .json_one_file_async_storage import JsonOneFileAsyncStorage
from .local_blob_async_storage import LocalAsyncBlobStorage
from .local_factory import LocalFactory


class LocalAsyncFactory(BaseAsyncFactory):
    def __init__(self, root_path: StrPath):
        super().__init__()
        self._root_path = Path(root_path)
        self.sync_factory: LocalFactory | None = None

    @override
    def get_sync_factory(self) -> LocalFactory:
        if not self.sync_factory:
            self.sync_factory = LocalFactory(self._root_path)
            self.sync_factory._collection_defs = self._collection_defs
            self.sync_factory._type_to_collection_defs = self._type_to_collection_defs
        return self.sync_factory

    def create_storage[T: BaseModel](
        self,
        collection_name: str,
        clazz: type[T],
        key: str | Callable[[T], str] | None = None,
    ) -> BaseAsyncStorage[T]:
        return JsonMultiFilesAsyncStorage(
            collection_name=collection_name,
            clazz=clazz,
            key=key,
            root_path=self._root_path,
        )

    def create_compact_storage[T: BaseModel](
        self,
        collection_name: str,
        clazz: type[T],
        key: str | Callable[[T], str] | None = None,
    ) -> BaseAsyncStorage[T]:
        return JsonOneFileAsyncStorage(
            collection_name=collection_name,
            clazz=clazz,
            key=key,
            root_path=self._root_path,
        )

    def create_blob_storage[T: BaseBlobMetadata](
        self,
        collection_name: str,
        clazz: type[T] = BaseBlobMetadata,
        content_type: str = "text/plain",
        bucket_name: str | None = None,
    ) -> BaseAsyncBlobStorage[T]:
        root_path = Path(bucket_name) if bucket_name else self._root_path
        return LocalAsyncBlobStorage[T](collection_name, clazz, content_type, root_path=root_path / "blobs")


@deprecated("Use LocalAsyncFactory")
class AsyncLocalFactory(LocalAsyncFactory):
    pass
