"""Stores data on disk in json files"""

import logging
import json
from typing import AsyncIterator, Type

from pydantic import BaseModel

from ..base import BaseAsyncStorage
from .file_async_storage import FileAsyncStorage

DEF_EXT = "json"


class JsonOneFileAsyncStorage[T: BaseModel](BaseAsyncStorage[T], FileAsyncStorage):
    def __init__(self, collection_name: str, clazz: Type[T], key_name: str = None):
        BaseAsyncStorage.__init__(self, collection_name, clazz, key_name)
        FileAsyncStorage.__init__(self, default_ext=DEF_EXT)

        if "." not in collection_name:
            self.file_name = f"{collection_name}.{DEF_EXT}"
        else:
            self.file_name = collection_name
        self.file_path = self.folder_path.joinpath(self.file_name)
        self._log = logging.getLogger(__name__)

    async def _load_data(self) -> dict[str, T]:
        try:
            data = await self._async_read_from_file(self.file_path)
            return json.loads(data)
        except FileNotFoundError:
            return {}

    async def _save_data(self, data: dict[str, T]) -> None:
        data = json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )
        await self._async_write_to_file(self.file_path, data)

    async def put(self, key: str, value: T) -> None:
        dv = value.model_dump()
        dv.pop(self.key_name, None)
        data = await self._load_data()
        data[key] = dv
        await self._save_data(data)

    async def get(self, key: str) -> T:
        try:
            data = await self._load_data()
            dv = data[key]
            dv[self.key_name] = key
            return self.clazz.model_validate(dv)
        except KeyError:
            return None

    async def keys(self) -> AsyncIterator[str]:
        data = await self._load_data()
        for k in data.keys():
            yield k

    async def delete(self, key: str) -> None:
        data = await self._load_data()
        data.pop(key, None)
        await self._save_data(data)
