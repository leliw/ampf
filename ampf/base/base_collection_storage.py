from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Optional, Type, TypeVar, get_origin

from pydantic import BaseModel

from .base_decorator import BaseDecorator
from .base_query_storage import BaseQueryStorage
from .collection_def import CollectionDef

TModel = TypeVar("TModel", bound=BaseModel)

if TYPE_CHECKING:
    # Only for IDE
    class _StorageProxy(BaseDecorator, BaseQueryStorage[TModel]): 
        pass
else:
    # For Runtime 
    class _StorageProxy(BaseDecorator[BaseQueryStorage[TModel]]): 
        pass
    
class BaseCollectionStorage(_StorageProxy[TModel]):
    """Base class for stored collections.
    Each element of collection can have its own subcollections
    """

    def __init__(
        self,
        create_storage: Callable[[str, Type[TModel], Optional[str | Callable[[TModel], str]]], BaseQueryStorage[TModel]],
        definition: CollectionDef[TModel],
    ):
        self.create_storage = create_storage
        storage = self.create_storage(definition.collection_name, definition.clazz, definition.key)
        super().__init__(storage)
        subcollections_list = definition.subcollections or []
        self.subcollections = {sc.collection_name: sc for sc in subcollections_list}
        self.sub_classes = {sc.clazz: sc.collection_name for sc in subcollections_list}

    def get_collection[Y: BaseModel](
        self, parent_key: Any, subcollection_name_or_class: str | Type[Y] | Any
    ) -> BaseCollectionStorage[Y]:
        """Returns subcollection for given key.

        Subcollection can be identified by its name or class.

        Args:
            parent_key (Any): Main collection key
            subcollection_name_or_class (str | Type[Y] | Any): Subcollection name or its class
        Returns:
            (BaseCollectionStorage[Y]): Subcollection object
        """
        if isinstance(subcollection_name_or_class, str):
            subcollection_name = subcollection_name_or_class
        else:
            try:
                subcollection_name = self.sub_classes[subcollection_name_or_class]
            except KeyError:
                # Fallback: if it's Annotated, try to look up by the origin type (e.g. Union)
                origin = get_origin(subcollection_name_or_class)
                if origin is not None:
                    subcollection_name = self.sub_classes[origin]
                else:
                    raise

        sub = self.subcollections[subcollection_name]

        return BaseCollectionStorage(
            self.create_storage,
            CollectionDef(
                collection_name=f"{self.decorated.collection_name}/{parent_key}/{sub.collection_name}",
                clazz=sub.clazz,
                key=sub.key,
                subcollections=sub.subcollections,
            ),
        )  # type: ignore
