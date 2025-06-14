import os
from pathlib import Path
from typing import Callable, Optional, Type

from pydantic import BaseModel

from ..base import BaseBlobStorage, BaseFactory, BaseStorage
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

    def create_blob_storage[T: BaseModel](
        self, collection_name: str, clazz: Optional[Type[T]] = None, content_type: Optional[str] = None
    ) -> BaseBlobStorage[T]:
        return LocalBlobStorage(
            collection_name, clazz, content_type, root_path=self._root_path
        )
