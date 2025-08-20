from __future__ import annotations

from typing import Callable, Optional, Type

from pydantic import BaseModel

from ampf.base.base_decorator import BaseDecorator

from .base_storage import BaseStorage
from .collection_def import CollectionDef


class BaseCollectionStorage[T: BaseModel](BaseDecorator[BaseStorage[T]]):
    """Base class for stored collections.
    Each element of collection can have its own subcollections
    """

    def __init__(
        self,
        create_storage: Callable[[str, Type[T], Optional[str | Callable[[T], str]]], BaseStorage[T]],
        definition: CollectionDef[T],
    ):
        self.create_storage = create_storage
        storage = self.create_storage(definition.collection_name, definition.clazz, definition.key)
        super().__init__(storage)
        subcollections_list = definition.subcollections or []
        self.subcollections = {sc.collection_name: sc for sc in subcollections_list}
        self.sub_classes = {sc.clazz: sc.collection_name for sc in subcollections_list}


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
        ret: BaseCollectionStorage = BaseCollectionStorage(
            self.create_storage,
            CollectionDef(
                collection_name=f"{self.decorated.collection_name}/{parent_key}/{sub.collection_name}",
                clazz=sub.clazz,
                key=sub.key,
                subcollections=sub.subcollections,
            ),
        )
        return ret
