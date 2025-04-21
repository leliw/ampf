"""Stores data on disk in json files"""

import logging
import os
from pathlib import Path
from typing import AsyncIterator, Callable, Type

import aiofiles
import aiofiles.os

from ampf.base import BaseAsyncStorage

from .file_async_storage import FileAsyncStorage, StrPath


class JsonMultiFilesAsyncStorage[T](BaseAsyncStorage[T], FileAsyncStorage):
    """Stores data on disk in json files. Each item is stored in its own file"""

    def __init__(
        self,
        collection_name: str,
        clazz: Type[T],
        key_name: str = None,
        key: Callable[[T], str] = None,
        subfolder_characters: int = None,
        root_path: StrPath = None,
    ):
        BaseAsyncStorage.__init__(self, collection_name, clazz, key_name, key)
        FileAsyncStorage.__init__(
            self,
            folder_name=collection_name,
            default_ext="json",
            subfolder_characters=subfolder_characters,
            root_path=root_path,
        )
        self._log = logging.getLogger(__name__)

    async def put(self, key: str, value: T) -> None:
        full_path = self._key_to_full_path(key)
        json_str = value.model_dump_json(by_alias=True, indent=2, exclude_none=True)
        await self._async_write_to_file(full_path, json_str)

    async def get(self, key: str) -> T:
        full_path = self._key_to_full_path(key)
        try:
            data = await self._async_read_from_file(full_path)
            return self.clazz.model_validate_json(data)
        except FileNotFoundError:
            return None

    async def keys(self) -> AsyncIterator[str]:
        start_index = len(str(self.folder_path)) + 1
        if self.subfolder_characters:
            end_index = self.subfolder_characters + 1
        else:
            end_index = None
        for root, _, files in os.walk(self.folder_path):
            if Path(f"{root}.json").is_file() and root != str(self.folder_path):
                # If exists json file wtith the same name as directory
                # and it's not root folder
                # - skip it - it's subcollection
                pass
            else:
                folder = (
                    root[start_index:-end_index] if end_index else root[start_index:]
                )
                for file in files:
                    k = f"{folder}/{file}" if folder else file
                    yield k[:-5] if k.endswith(".json") else k

    async def delete(self, key: str) -> None:
        full_path = self._key_to_full_path(key)
        await aiofiles.os.remove(full_path)

    def _key_to_full_path(self, key: str) -> str:
        return self._create_file_path(key)
