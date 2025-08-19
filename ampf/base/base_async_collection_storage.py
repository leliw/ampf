from __future__ import annotations

from typing import List, Optional, Type

from pydantic import BaseModel

from ampf.base.base_async_storage import BaseAsyncStorage
from ampf.base.base_decorator import BaseDecorator


class BaseAsyncCollectionStorage[T: BaseModel](BaseDecorator[BaseAsyncStorage[T]]):
    """Base class for stored collections.
    Each element of collection can have its own subcollections
    """

    def __init__(
        self,
        storage: BaseAsyncStorage[T],
        collections: Optional[List[BaseAsyncCollectionStorage]] = None,
    ):
        super().__init__(storage)
        self.subcollections: dict[str, BaseAsyncCollectionStorage] = {}
        self.sub_classes: dict[Type, str] = {}
        if collections:
            for sc in collections:
                self.add_collection(sc)

    def add_collection[Y: BaseModel](self, subcollection: BaseAsyncCollectionStorage[Y]):
        """Adds subcollection definition

        Args:
            subcollection (BaseCollectionStorage[Y]): subcollectiondefinition
        """
        self.subcollections[subcollection.collection_name] = subcollection
        self.sub_classes[subcollection.clazz] = subcollection.collection_name

    def get_collection[Y: BaseModel](
        self, parent_key: str, subcollection_name_or_class: str | Type[Y]
    ) -> BaseAsyncCollectionStorage[Y]:
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
        ret = BaseAsyncCollectionStorage(
            self.create_collection(
                parent_key=parent_key, collection_name=sub.collection_name, clazz=sub.clazz, key=sub.key
            )
        )
        for c in sub.subcollections.values():
            ret.add_collection(c)
        return ret
