from pathlib import Path
from typing import Callable, Optional, Type

from pydantic import BaseModel


from ..base import BaseAsyncFactory, BaseAsyncStorage, BaseAsyncBlobStorage
from ..local import StrPath
from .local_blob_async_storage import LocalBlobAsyncStorage
from .json_multi_files_async_storage import JsonMultiFilesAsyncStorage
from .json_one_file_async_storage import JsonOneFileAsyncStorage


class AsyncLocalFactory(BaseAsyncFactory):
    def __init__(self, root_path: StrPath):
        self._root_path = Path(root_path)

    def create_storage[T: BaseModel](
        self,
        collection_name: str,
        clazz: Type[T],
        key_name: Optional[str] = None,
        key: Optional[Callable[[T], str] | str] = None,
    ) -> BaseAsyncStorage[T]:
        return JsonMultiFilesAsyncStorage(
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
        key: Optional[Callable[[T], str] | str] = None,
    ) -> BaseAsyncStorage[T]:
        return JsonOneFileAsyncStorage(
            collection_name=collection_name,
            clazz=clazz,
            key_name=key_name,
            key=key,
            root_path=self._root_path,
        )

    def create_blob_storage[T: BaseModel](
        self, collection_name: str, clazz: Optional[Type[T]] = None, content_type: Optional[str] = None
    ) -> BaseAsyncBlobStorage[T]:
        return LocalBlobAsyncStorage(collection_name, clazz, content_type, root_path=self._root_path)
