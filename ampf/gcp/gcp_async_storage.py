from __future__ import annotations

from typing import Any, AsyncIterator, Callable, Dict, List, Literal, Optional, Type, override

from google.cloud import exceptions, firestore
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from google.cloud.firestore_v1.vector import Vector
from pydantic import BaseModel

from ampf.base import BaseAsyncQueryStorage, KeyNotExistsException
from ampf.base.base_async_query import BaseAsyncQuery
from ampf.base.base_decorator import BaseDecorator

from .gcp_storage import convert_uuids


class GcpAsyncQuery[T: BaseModel](BaseDecorator[firestore.AsyncQuery], BaseAsyncQuery[T]):
    def __init__(self, decorated: firestore.AsyncQuery, clazz: Type[T]):
        """Initialize the decorator with a decorated object.

        Args:
            decorated (T): The object to be decorated.
        """
        super().__init__(decorated)
        self.clazz = clazz

    @override
    def where(self, field: str, op: Literal["==", "!=", "<", "<=", ">", ">="], value: Any) -> GcpAsyncQuery[T]:
        coll_ref = self.decorated
        coll_ref = coll_ref.where(field, op, convert_uuids(value))
        return GcpAsyncQuery(coll_ref, self.clazz)

    @override
    async def get_all(self, order_by: Optional[List[str | tuple[str, Any]]] = None) -> AsyncIterator[T]:
        """Get all documents from the collection."""
        coll_ref = self.decorated
        if order_by:
            for o in order_by:
                if isinstance(o, tuple):
                    coll_ref = coll_ref.order_by(o[0], direction=o[1])
                else:
                    coll_ref = coll_ref.order_by(o)
        async for doc in coll_ref.stream():
            yield self.clazz.model_validate(doc.to_dict())


class GcpAsyncStorage[T: BaseModel](BaseAsyncQueryStorage[T]):
    """A simple wrapper around Google Cloud Firestore."""

    def __init__(
        self,
        collection: str,
        clazz: Type[T],
        db: Optional[firestore.AsyncClient] = None,
        project: Optional[str] = None,
        database: Optional[str] = None,
        key: Optional[str | Callable[[T], str]] = None,
        embedding_field_name: str = "embedding",
        embedding_search_limit: int = 5,
        root_storage: Optional[str] = None,
    ):
        super().__init__(collection, clazz, key, embedding_field_name, embedding_search_limit)
        self._db = db or firestore.AsyncClient(project=project, database=database)
        self.root_storage = root_storage
        self._collection = f"{root_storage}/{collection}" if root_storage else collection
        self._coll_ref = self._db.collection(self._collection)

    def on_before_save(self, data: Dict[str, Any]) -> dict:
        """Converts the embedding field to a Vector object.

        Args:
            data: The data to be saved.
        Returns:
            The preprocessed data.
        """
        data = convert_uuids(data)  # type: ignore
        if self.embedding_field_name in data:
            data[self.embedding_field_name] = Vector(data[self.embedding_field_name])
        return data

    async def put(self, key: Any, data: T) -> None:
        """Put a document in the collection."""
        data_dict = data.model_dump(by_alias=True, exclude_none=True)
        data_dict = self.on_before_save(data_dict)  # Preprocess data
        await self._coll_ref.document(str(key)).set(data_dict)

    async def get(self, key: Any) -> T:
        """Get a document from the collection."""
        doc = await self._coll_ref.document(str(key)).get()
        data = doc.to_dict()
        return self.clazz.model_validate(data)

    async def keys(self) -> AsyncIterator[str]:
        """Return a list of keys in the collection."""
        async for doc in self._coll_ref.stream():
            yield doc.id

    async def delete(self, key: Any) -> bool:
        """Delete a document from the collection."""
        try:
            await self._coll_ref.document(str(key)).delete()
            return True
        except exceptions.NotFound:
            raise KeyNotExistsException(key)

    async def drop(self) -> None:
        """Delete all documents from the collection."""
        async for doc in self._coll_ref.stream():
            await doc.reference.delete()

    async def get_all(self, order_by: Optional[List[str | tuple[str, Any]]] = None) -> AsyncIterator[T]:
        """Get all documents from the collection."""
        coll_ref = self._coll_ref
        if order_by:
            for o in order_by:
                if isinstance(o, tuple):
                    coll_ref = coll_ref.order_by(o[0], direction=o[1])
                else:
                    coll_ref = coll_ref.order_by(o)
        async for doc in coll_ref.stream():
            yield self.clazz.model_validate(doc.to_dict())

    async def find_nearest(self, embedding: List[float], limit: Optional[int] = None) -> AsyncIterator[T]:
        """Finds the nearest knowledge base items to the given vector."

        Args:
            embedding: The vector to search for.
            limit: The maximum number of results to return.
        Returns:
            An iterator of the nearest items.
        """
        async for ds in self._coll_ref.find_nearest(
            vector_field=self.embedding_field_name,
            query_vector=Vector(embedding),
            distance_measure=DistanceMeasure.COSINE,
            limit=limit or self.embedding_search_limit,
        ).stream():  # type: ignore
            yield self.clazz(**ds.to_dict())

    @override
    def where(self, field: str, op: Literal["==", "!=", "<", "<=", ">", ">="], value: Any) -> GcpAsyncQuery[T]:
        """Apply a filter to the query"""
        coll_ref = self._coll_ref
        coll_ref = coll_ref.where(field, op, convert_uuids(value))
        return GcpAsyncQuery(coll_ref, self.clazz)
