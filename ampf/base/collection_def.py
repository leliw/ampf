from __future__ import annotations

from typing import Callable, List, Optional, Type

from pydantic import BaseModel, Field


class CollectionDef[T: BaseModel](BaseModel):
    """Parameters defining CollectionStorage"""

    collection_name: str
    clazz: Type[T]
    key: Optional[str | Callable[[T], str]] = None
    subcollections: Optional[List[CollectionDef]] = Field(default_factory=list)

    def __init__(
        self,
        collection_name: str,
        clazz: Type,
        key: Optional[str | Callable[[T], str]] = None,
        subcollections: Optional[List[CollectionDef]] = None,
    ):
        """It is required to initialise class without parameter names."""
        super().__init__(
            collection_name=collection_name,
            clazz=clazz,
            key=key,
            subcollections=subcollections or list(),
        )
