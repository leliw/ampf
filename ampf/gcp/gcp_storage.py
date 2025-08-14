from __future__ import annotations

from typing import Any, Callable, Dict, Iterator, List, Optional, Type
import uuid

from google.cloud import exceptions, firestore
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from google.cloud.firestore_v1.vector import Vector
from google.cloud.firestore_v1.vector_query import VectorQuery
from pydantic import BaseModel

from ..base import BaseCollectionStorage, KeyNotExistsException


class GcpStorage[T: BaseModel](BaseCollectionStorage[T]):
    """A simple wrapper around Google Cloud Firestore."""

    def __init__(
        self,
        collection: str,
        clazz: Type[T],
        db: Optional[firestore.Client] = None,
        project: Optional[str] = None,
        database: Optional[str] = None,
        key_name: Optional[str] = None,
        key: Optional[str | Callable[[T], str]] = None,
        embedding_field_name: str = "embedding",
        embedding_search_limit: int = 5,
        root_storage: Optional[str] = None,
    ):
        """Initializes the storage.

        Args:
            collection: The name of the collection.
            clazz: The class of the objects.
            db: The Firestore client.
            project: The project ID.
            database: The database ID.
            key_name: The name of the key field.
            embedding_field_name: The name of the embedding field.
            embedding_search_limit: The maximum number of results to return when vector searching.
        """
        super().__init__(
            collection,
            clazz,
            key_name=key_name,
            key=key,
            embedding_field_name=embedding_field_name,
            embedding_search_limit=embedding_search_limit,
        )
        self._db = db or firestore.Client(project=project, database=database)
        self.root_storage = root_storage
        self._collection = (
            f"{root_storage}/{collection}" if root_storage else collection
        )
        self._coll_ref = self._db.collection(self._collection)

    def on_before_save(self, data: Dict[str, Any]) -> dict:
        """Converts the embedding field to a Vector object.

        Args:
            data: The data to be saved.
        Returns:
            The preprocessed data.
        """
        def convert_uuids(obj):
            if isinstance(obj, dict):
                return {convert_uuids(k): convert_uuids(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_uuids(item) for item in obj]
            elif isinstance(obj, uuid.UUID):
                return str(obj)
            else:
                return obj

        data = convert_uuids(data) # type: ignore
        if self.embedding_field_name in data:
            data[self.embedding_field_name] = Vector(data[self.embedding_field_name])
        return data

    def put(self, key: Any, data: T) -> None:
        """Put a document in the collection."""
        data_dict = data.model_dump(by_alias=True, exclude_none=True)
        data_dict = self.on_before_save(data_dict)  # Preprocess data
        self._coll_ref.document(str(key)).set(data_dict)

    def get(self, key: Any) -> T:
        """Get a document from the collection."""
        data = self._coll_ref.document(str(key)).get().to_dict()
        if not data:
            raise KeyNotExistsException(self.collection_name, self.clazz, key)
        return self.clazz.model_validate(data)

    def get_all(self, order_by: Optional[List[str | tuple[str, Any]]] = None) -> Iterator[T]:
        """Get all documents from the collection."""
        coll_ref = self._coll_ref
        if order_by:
            for o in order_by:
                if isinstance(o, tuple):
                    coll_ref = coll_ref.order_by(o[0], direction=o[1])
                else:
                    coll_ref = coll_ref.order_by(o)
        for doc in coll_ref.stream():
            yield self.clazz.model_validate(doc.to_dict())

    def keys(self) -> Iterator[str]:
        """Return a list of keys in the collection."""
        for doc in self._coll_ref.stream():
            yield doc.id

    def delete(self, key: Any) -> bool:
        """Delete a document from the collection."""
        try:
            self._coll_ref.document(str(key)).delete()
            return True
        except exceptions.NotFound:
            raise KeyNotExistsException(key)

    def drop(self) -> None:
        """Delete all documents from the collection."""
        for doc in self._coll_ref.stream():
            doc.reference.delete()

    def find_nearest(self, embedding: List[float], limit: Optional[int] = None) -> Iterator[T]:
        """Finds the nearest knowledge base items to the given vector."

        Args:
            embedding: The vector to search for.
            limit: The maximum number of results to return.
        Returns:
            An iterator of the nearest items.
        """
        vq: VectorQuery = self._coll_ref.find_nearest(
            vector_field=self.embedding_field_name,
            query_vector=Vector(embedding),
            distance_measure=DistanceMeasure.COSINE,
            limit=limit or self.embedding_search_limit,
        ).get() # type: ignore
        for ds in vq: # type: ignore
            yield self.clazz(**ds.to_dict())

    def create_collection[C: BaseModel](
        self,
        parent_key: str,
        collection_name: str,
        clazz: Type[C],
        key_name: Optional[str] = None,
        key: Optional[str | Callable[[C], str]] = None,
    ) -> GcpStorage[C]:
        new_collection_name = f"{self.collection_name}/{parent_key}/{collection_name}"
        return GcpStorage(new_collection_name, clazz, key_name=key_name, key=key, root_storage=self.root_storage)
