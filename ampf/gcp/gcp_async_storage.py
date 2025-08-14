from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Type
import uuid

from google.cloud import exceptions, firestore
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from google.cloud.firestore_v1.vector import Vector
from pydantic import BaseModel

from ampf.base import BaseAsyncStorage, KeyNotExistsException


class GcpAsyncStorage[T: BaseModel](BaseAsyncStorage[T]):
    """A simple wrapper around Google Cloud Firestore."""

    def __init__(
        self,
        collection: str,
        clazz: Type[T],
        db: Optional[firestore.AsyncClient] = None,
        project: Optional[str] = None,
        database: Optional[str] = None,
        key_name: Optional[str] = None,
        key: Optional[Callable[[T], str]] = None,
        embedding_field_name: str = "embedding",
        embedding_search_limit: int = 5,
        root_storage: Optional[str] = None,

    ):
        super().__init__(collection, clazz, key_name, key)
        self._db = db or firestore.AsyncClient(project=project, database=database)
        self.root_storage = root_storage
        self._collection = (
            f"{root_storage}/{collection}" if root_storage else collection
        )
        self._coll_ref = self._db.collection(self._collection)
        self.embedding_field_name = embedding_field_name
        self.embedding_search_limit = embedding_search_limit

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

    async def find_nearest(
        self, embedding: List[float], limit: Optional[int] = None
    ) -> AsyncIterator[T]:
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
        ).stream(): # type: ignore
            yield self.clazz(**ds.to_dict())
