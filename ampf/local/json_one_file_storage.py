"""Stores data on disk in json files"""

import logging
import json
from typing import Any, Callable, Dict, Iterator, Optional, Type

from pydantic import BaseModel

from ..base import BaseStorage, KeyNotExistsException
from .file_storage import FileStorage, StrPath

DEF_EXT = "json"


class JsonOneFileStorage[T: BaseModel](BaseStorage[T], FileStorage):
    """Stores data on disk in one json file as a dictionary.
    
    If key_name is set then key value isn't stored in dictionary
    value, it's simply dictionary key
    """
    def __init__(
        self,
        collection_name: str,
        clazz: Type[T],
        key_name: Optional[str] = None,
        key: Optional[Callable[[T], str]] = None,
        root_path: Optional[StrPath] = None,
    ):
        BaseStorage.__init__(self, collection_name, clazz, key_name, key)
        FileStorage.__init__(self, default_ext=DEF_EXT, root_path=root_path)

        if "." not in collection_name:
            self.file_name = f"{collection_name}.{DEF_EXT}"
        else:
            self.file_name = collection_name
        self.file_path = self.folder_path.joinpath(self.file_name)
        self._log = logging.getLogger(__name__)

    def _load_data(self) -> Dict[str, Dict[str, Any]]:
        try:
            return json.load(open(self.file_path, "r", encoding="utf-8"))
        except FileNotFoundError:
            return {}

    def _save_data(self, data: Dict[str, Dict[str, Any]]) -> None:
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
        # Remove key from value
        if self.key_name:
            dv.pop(self.key_name)
        data = self._load_data()
        data[key] = dv
        self._save_data(data)

    def get(self, key: str) -> T:
        try:
            data = self._load_data()
            dv = data[key]
            # Add key back
            if self.key_name:
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
