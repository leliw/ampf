"""Stores data on disk in json files"""

import json
import logging
from typing import Any, AsyncIterator, Callable, Optional, Type

from pydantic import BaseModel

from ampf.base.exceptions import KeyNotExistsException

from ..base import BaseAsyncStorage
from .file_async_storage import FileAsyncStorage, StrPath

DEF_EXT = "json"


class JsonOneFileAsyncStorage[T: BaseModel](BaseAsyncStorage[T], FileAsyncStorage):
    def __init__(
        self,
        collection_name: str,
        clazz: Type[T],
        key: Optional[str | Callable[[T], str]] = None,
        embedding_field_name: str = "embedding",
        embedding_search_limit: int = 5,        
        root_path: Optional[StrPath] = None,
    ):
        BaseAsyncStorage.__init__(self, collection_name, clazz, key, embedding_field_name, embedding_search_limit)
        FileAsyncStorage.__init__(self, default_ext=DEF_EXT, root_path=root_path)

        if "." not in collection_name:
            self.file_name = f"{collection_name}.{DEF_EXT}"
        else:
            self.file_name = collection_name
        self.file_path = self.folder_path.joinpath(self.file_name)
        self._log = logging.getLogger(__name__)

    async def _load_data(self) -> dict[str, Any]:
        try:
            data = await self._async_read_from_file(self.file_path)
            return json.loads(data)
        except FileNotFoundError:
            return {}

    async def _save_data(self, data: dict[str, Any]) -> None:
        jdata = json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )
        await self._async_write_to_file(self.file_path, jdata)

    async def put(self, key: Any, value: T) -> None:
        key = str(key)
        dv = value.model_dump()
        if isinstance(self.key, str):
            dv.pop(self.key, None)
        data = await self._load_data()
        data[key] = dv
        await self._save_data(data)

    async def get(self, key: Any) -> T:
        key = str(key)
        try:
            data = await self._load_data()
            dv = data[key]
            if isinstance(self.key, str):
                dv[self.key] = key
            return self.clazz.model_validate(dv)
        except KeyError:
            raise KeyNotExistsException(self.collection_name, self.clazz, key)

    async def keys(self) -> AsyncIterator[str]:
        data = await self._load_data()
        for k in data.keys():
            yield k

    async def delete(self, key: Any) -> None:
        key = str(key)
        data = await self._load_data()
        data.pop(key, None)
        await self._save_data(data)
