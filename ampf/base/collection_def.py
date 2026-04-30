from dataclasses import dataclass, field
from typing import Any, Callable, Type

from pydantic import BaseModel


@dataclass
class CollectionDef[T: BaseModel]:
    """Parameters defining CollectionStorage"""

    collection_name: str
    clazz: Type[T] | Any
    key: str | Callable[[T], str] | None = None
    subcollections: list["CollectionDef"] = field(default_factory=list)
