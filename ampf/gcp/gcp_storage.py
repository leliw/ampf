from typing import Iterator, List, Type, override

from google.cloud import exceptions, firestore
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from google.cloud.firestore_v1.vector import Vector
from google.cloud.firestore_v1.vector_query import VectorQuery

from ampf.base import BaseStorage, KeyNotExistsException


class GcpStorage[T](BaseStorage[T]):
    """A simple wrapper around Google Cloud Firestore."""

    def __init__(
        self,
        collection: str,
        clazz: Type[T],
        db: firestore.Client = None,
        project: str = None,
        database: str = None,
        key_name: str = None,
        embedding_field_name: str = "embedding",
        embedding_search_limit: int = 5,
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
        super().__init__(collection, clazz, key_name=key_name)
        self._db = db or firestore.Client(project=project, database=database)
        self._collection = collection
        self._coll_ref = self._db.collection(self._collection)
        self.embedding_field_name = embedding_field_name
        self.embedding_search_limit = embedding_search_limit

    @override
    def on_before_save(self, data: dict) -> dict:
        """Converts the embedding field to a Vector object.
        
        Args:
            data: The data to be saved.
        Returns:
            The preprocessed data.
        """
        if self.embedding_field_name in data:
            data[self.embedding_field_name] = Vector(data[self.embedding_field_name])
        return data

    def put(self, key: str, data: T) -> None:
        """Put a document in the collection."""
        data_dict = data.model_dump(by_alias=True, exclude_none=True)
        data_dict = self.on_before_save(data_dict)  # Preprocess data
        self._coll_ref.document(key).set(data_dict)

    def get(self, key: str) -> T:
        """Get a document from the collection."""
        data = self._coll_ref.document(key).get().to_dict()
        if not data:
            raise KeyNotExistsException(self.collection_name, self.clazz, key)
        return self.clazz.model_validate(data)

    def get_all(self, order_by: list[str | tuple[str, any]] = None) -> Iterator[T]:
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

    def delete(self, key: str) -> bool:
        """Delete a document from the collection."""
        try:
            self._coll_ref.document(key).delete()
            return True
        except exceptions.NotFound:
            raise KeyNotExistsException(key)

    def drop(self) -> None:
        """Delete all documents from the collection."""
        for doc in self._coll_ref.stream():
            doc.reference.delete()

    def find_nearest(self, embedding: List[float], limit: int = None) -> Iterator[T]:
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
        ).get()
        for ds in vq:
            yield self.clazz(**ds.to_dict())
