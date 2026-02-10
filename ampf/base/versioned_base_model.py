from abc import ABC, abstractmethod
from typing import Any, Dict

from pydantic import BaseModel


class VersionedBaseModel(BaseModel, ABC):
    _v: int

    @classmethod
    @abstractmethod
    def from_storage(cls, data: Dict[str, Any]):
        return cls.model_validate(data)

    @abstractmethod
    def to_storage(self) -> Dict[str, Any]:
        return self.model_dump(by_alias=True, exclude_none=True)
