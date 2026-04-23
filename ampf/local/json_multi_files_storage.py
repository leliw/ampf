"""Stores data on disk in json files"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Callable, Iterator, Optional, Self, Type

from pydantic import BaseModel

from ..base import BaseQueryStorage, KeyNotExistsException
from .file_storage import FileStorage


class JsonMultiFilesStorage[T: BaseModel](BaseQueryStorage[T], FileStorage):
    """Stores data on disk in json files. Each item is stored in its own file"""

    def __init__(
        self,
        collection_name: str,
        clazz: Type[T],
        key: Optional[str | Callable[[T], str]] = None,
        embedding_field_name: str = "embedding",
        embedding_search_limit: int = 5,
        subfolder_characters: Optional[int] = None,
        root_path: Optional[Path] = None,
    ):
        BaseQueryStorage.__init__(
            self,
            collection_name,
            clazz,
            key=key,
            embedding_field_name=embedding_field_name,
            embedding_search_limit=embedding_search_limit,
        )
        FileStorage.__init__(
            self,
            folder_name=collection_name,
            default_ext="json",
            subfolder_characters=subfolder_characters,
            root_path=root_path,
        )
        self._log = logging.getLogger(__name__)

    def put(self, key: Any, value: T) -> None:
        key = str(key)
        new_key = self.get_key(value)
        # If the key of the value has changed, remove the old key
        if key != new_key:
            self.delete(key)
            # Store the value with the new key
            key = new_key

        full_path = self._key_to_full_path(key)
        self._log.debug("put: %s (%s)", key, full_path)
        data = self.to_storage(value)
        json_str = json.dumps(data, indent=2, ensure_ascii=False, default=str)
        self._write_to_file(full_path, json_str)

    def get(self, key: Any) -> T:
        key = str(key)
        self._log.debug("get %s", key)
        full_path = self._key_to_full_path(key)
        try:
            data = self._read_from_file(full_path)
            return self.from_storage(json.loads(data))
        except FileNotFoundError:
            raise KeyNotExistsException(self.collection_name, self.clazz, key)

    def keys(self) -> Iterator[str]:
        self._log.debug("keys -> start %s", self.folder_path)
        start_index = len(str(self.folder_path)) + 1
        if self.subfolder_characters:
            end_index = self.subfolder_characters + 1
        else:
            end_index = None
        subcollections = []
        for root, _, files in os.walk(self.folder_path):
            self._log.debug("keys -> walk %s %d", root, len(files))
            if Path(f"{root}.json").is_file() and root != str(self.folder_path):
                # If exists json file with the same name as directory
                # and it's not root folder
                # - skip it - it's subcollection
                subcollections.append(root)
                continue

            if any(root.startswith(sc) for sc in subcollections):
                # - skip it - it's subcollection
                continue

            folder = root[start_index:-end_index] if end_index else root[start_index:]
            for file in files:
                k = f"{folder}/{file}" if folder else file
                self._log.debug("keys: %s", k)
                yield k[:-5] if k.endswith(".json") else k
        self._log.debug("keys <- end")

    def delete(self, key: Any) -> None:
        self._log.debug("delete %s", key)
        full_path = self._key_to_full_path(str(key))
        try:
            os.remove(full_path)
        except FileNotFoundError:
            raise KeyNotExistsException(self.collection_name, self.clazz, key)

    def _key_to_full_path(self, key: str) -> Path:
        return self._create_file_path(key)

    def create_collection(
        self,
        parent_key: str,
        collection_name: str,
        clazz: Type[T],
        key: Optional[str | Callable[[T], str]] = None,
    ) -> Self:
        new_collection_name = f"{self.collection_name}/{parent_key}/{collection_name}"
        return self.__class__(
            new_collection_name,
            clazz,
            key=key,
            root_path=self._root_path,
            embedding_field_name=self.embedding_field_name,
            embedding_search_limit=self.embedding_search_limit,
        )
