"""Stores data on disk in json files"""

import logging
import json
from typing import Callable, Iterator, Type

from pydantic import BaseModel

from ..base import BaseStorage, KeyNotExistsException
from .file_storage import FileStorage

DEF_EXT = "json"


class JsonOneFileStorage[T: BaseModel](BaseStorage[T], FileStorage):
    def __init__(
        self,
        collection_name: str,
        clazz: Type[T],
        key_name: str = None,
        key: Callable[[T], str] = None,
    ):
        BaseStorage.__init__(self, collection_name, clazz, key_name, key)
        FileStorage.__init__(self, default_ext=DEF_EXT)

        if "." not in collection_name:
            self.file_name = f"{collection_name}.{DEF_EXT}"
        else:
            self.file_name = collection_name
        self.file_path = self.folder_path.joinpath(self.file_name)
        self._log = logging.getLogger(__name__)

    def _load_data(self) -> dict[str, T]:
        try:
            return json.load(open(self.file_path, "r", encoding="utf-8"))
        except FileNotFoundError:
            return {}

    def _save_data(self, data: dict[str, T]) -> None:
        json.dump(
            data,
            open(self.file_path, "w", encoding="utf-8"),
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )

    def put(self, key: str, value: T) -> None:
        dv = value.model_dump()
        dv.pop(self.key_name, None)
        data = self._load_data()
        data[key] = dv
        self._save_data(data)

    def get(self, key: str) -> T:
        try:
            data = self._load_data()
            dv = data[key]
            dv[self.key_name] = key
            return self.clazz.model_validate(dv)
        except KeyError:
            raise KeyNotExistsException(self.collection_name, self.clazz, key)

    def keys(self) -> Iterator[str]:
        data = self._load_data()
        for k in data.keys():
            yield k

    def delete(self, key: str) -> None:
        data = self._load_data()
        data.pop(key, None)
        self._save_data(data)
