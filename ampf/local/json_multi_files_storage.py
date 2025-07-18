"""Stores data on disk in json files"""

import logging
import os
from pathlib import Path
from typing import Any, Callable, Iterator, Optional, Self, Type

from pydantic import BaseModel

from ..base import BaseCollectionStorage, KeyNotExistsException
from .file_storage import FileStorage


class JsonMultiFilesStorage[T: BaseModel](BaseCollectionStorage[T], FileStorage):
    """Stores data on disk in json files. Each item is stored in its own file"""

    def __init__(
        self,
        collection_name: str,
        clazz: Type[T],
        key_name: Optional[str] = None,
        key: Optional[Callable[[T], str]] = None,
        subfolder_characters: Optional[int] = None,
        root_path: Optional[Path] = None,
    ):
        BaseCollectionStorage.__init__(self, collection_name, clazz, key_name, key)
        FileStorage.__init__(
            self,
            folder_name=collection_name,
            default_ext="json",
            subfolder_characters=subfolder_characters,
            root_path=root_path,
        )
        self._log = logging.getLogger(__name__)

    def put(self, key: Any, value: T) -> None:
        full_path = self._key_to_full_path(str(key))
        self._log.debug("put: %s (%s)", key, full_path)
        json_str = value.model_dump_json(by_alias=True, indent=2, exclude_none=True)
        self._write_to_file(full_path, json_str)

    def get(self, key: Any) -> T:
        self._log.debug("get %s", key)
        full_path = self._key_to_full_path(str(key))
        try:
            data = self._read_from_file(full_path)
            return self.clazz.model_validate_json(data)
        except FileNotFoundError:
            raise KeyNotExistsException(self.collection_name, self.clazz, key)

    def keys(self) -> Iterator[str]:
        self._log.debug("keys -> start %s", self.folder_path)
        start_index = len(str(self.folder_path)) + 1
        if self.subfolder_characters:
            end_index = self.subfolder_characters + 1
        else:
            end_index = None
        for root, _, files in os.walk(self.folder_path):
            self._log.debug("keys -> walk %s %d", root, len(files))
            if Path(f"{root}.json").is_file() and root != str(self.folder_path):
                # If exists json file wtith the same name as directory
                # and it's not root folder
                # - skip it - it's subcollection
                pass
            else:
                folder = root[start_index:-end_index] if end_index else root[start_index:]
                for file in files:
                    k = f"{folder}/{file}" if folder else file
                    self._log.debug("keys: %s", k)
                    yield k[:-5] if k.endswith(".json") else k
        self._log.debug("keys <- end")

    def delete(self, key: Any) -> None:
        self._log.debug("delete %s", key)
        full_path = self._key_to_full_path(str(key))
        os.remove(full_path)

    def _key_to_full_path(self, key: str) -> Path:
        return self._create_file_path(key)

    def create_collection(
        self,
        parent_key: str,
        collection_name: str,
        clazz: Type[T],
        key_name: Optional[str] = None,
        key: Optional[Callable[[T], str]] = None,
    ) -> Self:
        new_collection_name = f"{self.collection_name}/{parent_key}/{collection_name}"
        return self.__class__(new_collection_name, clazz, key_name=key_name, key=key, root_path=self._root_path)
