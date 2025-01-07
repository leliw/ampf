import os
from pathlib import Path
from typing import Type
from pydantic import BaseModel

from ..base import BaseFactory, BaseStorage, BaseBlobStorage
from .file_storage import FileStorage, StrPath
from .json_multi_files_storage import JsonMultiFilesStorage
from .json_one_file_storage import JsonOneFileStorage
from .local_blob_storage import LocalBlobStorage


class LocalFactory(BaseFactory):
    def __init__(self, root_dir_path: StrPath):
        FileStorage._root_dir_path = Path(os.path.abspath(root_dir_path))

    def create_storage[T: BaseModel](
        self, collection_name: str, clazz: Type[T], key_name: str = None
    ) -> BaseStorage[T]:
        return JsonMultiFilesStorage(
            collection_name=collection_name, clazz=clazz, key_name=key_name
        )

    def create_compact_storage[T: BaseModel](
        self, collection_name: str, clazz: Type[T], key_name: str = None
    ) -> BaseStorage[T]:
        return JsonOneFileStorage(
            collection_name=collection_name, clazz=clazz, key_name=key_name
        )

    def create_blob_storage[T: BaseModel](
        self, collection_name: str, clazz: Type[T] = None, content_type: str = None
    ) -> BaseBlobStorage[T]:
        return LocalBlobStorage(collection_name, clazz, content_type)