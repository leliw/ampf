from __future__ import annotations

from typing import Callable, List, Optional, Type

from pydantic import BaseModel

from .base_storage import BaseStorage


class BaseCollectionStorage[T](BaseStorage[T]):
    """Base class for stored collections.
    Each element of collection can have its own subcollections
    """

    def __init__(
        self,
        collection_name: str,
        clazz: Type[T],
        key_name: Optional[str] = None,
        key: Optional[Callable[[T], str]] = None,
        collections: Optional[List[BaseCollectionStorage]] = None,
        embedding_field_name: str = "embedding",
        embedding_search_limit: int = 5,
    ):
        super().__init__(
            collection_name=collection_name,
            clazz=clazz,
            key_name=key_name,
            key=key,
            embedding_field_name=embedding_field_name,
            embedding_search_limit=embedding_search_limit,
        )
        self.collection_name = collection_name
        self.subcollections: dict[str, BaseCollectionStorage] = {}
        self.sub_classes: dict[Type, str] = {}
        if collections:
            for sc in collections:
                self.add_collection(sc)

    def add_collection[Y: BaseModel](self, subcollection: BaseCollectionStorage[Y]):
        """Adds subcollection definition

        Args:
            subcollection (BaseCollectionStorage[Y]): subcollectiondefinition
        """
        self.subcollections[subcollection.collection_name] = subcollection
        self.sub_classes[subcollection.clazz] = subcollection.collection_name

    def get_collection[Y: BaseModel](
        self, parent_key: str, subcollection_name_or_class: str | Type[Y]
    ) -> BaseCollectionStorage[Y]:
        """Returns subcollection for given key.

        Subcollection can be identified by its name or class.

        Args:
            key (str): Main collection key
            subcollection_name_or_class (str | Type[Y]): Subcollection name or its class
        Returns:
            (BaseCollectionStorage[Y]): Subcollection object
        """
        if not isinstance(subcollection_name_or_class, str):
            subcollection_name = self.sub_classes[subcollection_name_or_class]
        else:
            subcollection_name = subcollection_name_or_class
        sub = self.subcollections[subcollection_name]
        ret = self.create_collection(parent_key=parent_key, collection_name=sub.collection_name, clazz=sub.clazz, key_name=sub.key_name)
        for c in sub.subcollections.values():
            ret.add_collection(c)
        return ret
