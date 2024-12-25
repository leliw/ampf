"""A simple wrapper around Google Cloud Firestore."""

from typing import Iterator, Type
from google.cloud import firestore, exceptions

from ampf.base import BaseStorage


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
    ):
        super().__init__(collection,clazz, key_name=key_name)
        self._db = db or firestore.Client(project=project, database=database)
        self._collection = collection
        self._coll_ref = self._db.collection(self._collection)

    def on_before_save(self, data: dict) -> dict:
        """
        This method is called before saving data to Firestore.
        You can use it to modify the data dictionary before saving it.
        For example, you can add a timestamp or remove sensitive data.
        """
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
            return
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
            return False

    def drop(self) -> None:
        """Delete all documents from the collection."""
        for doc in self._coll_ref.stream():
            doc.reference.delete()
