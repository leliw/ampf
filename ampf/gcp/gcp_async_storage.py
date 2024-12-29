from typing import AsyncIterator, Type

from google.cloud import firestore, exceptions
from pydantic import BaseModel

from ampf.base import BaseAsyncStorage, KeyNotExistsException


class GcpAsyncStorage[T: BaseModel](BaseAsyncStorage[T]):
    """A simple wrapper around Google Cloud Firestore."""

    def __init__(
        self,
        collection: str,
        clazz: Type[T],
        db: firestore.AsyncClient = None,
        project: str = None,
        database: str = None,
        key_name: str = None,
    ):
        super().__init__(collection, clazz, key_name)
        self._db = db or firestore.AsyncClient(project=project, database=database)
        self._coll_ref = self._db.collection(self.collection_name)

    def on_before_save(self, data: dict) -> dict:
        """
        This method is called before saving data to Firestore.
        You can use it to modify the data dictionary before saving it.
        For example, you can add a timestamp or remove sensitive data.
        """
        return data

    async def put(self, key: str, data: T) -> None:
        """Put a document in the collection."""
        data_dict = data.model_dump(by_alias=True, exclude_none=True)
        data_dict = self.on_before_save(data_dict)  # Preprocess data
        await self._coll_ref.document(key).set(data_dict)

    async def get(self, key: str) -> T:
        """Get a document from the collection."""
        doc = await self._coll_ref.document(key).get()
        data = doc.to_dict()
        return self.clazz.model_validate(data)

    async def keys(self) -> AsyncIterator[str]:
        """Return a list of keys in the collection."""
        async for doc in self._coll_ref.stream():
            yield doc.id

    async def delete(self, key: str) -> bool:
        """Delete a document from the collection."""
        try:
            await self._coll_ref.document(key).delete()
            return True
        except exceptions.NotFound:
            raise KeyNotExistsException(key)

    async def drop(self) -> None:
        """Delete all documents from the collection."""
        async for doc in self._coll_ref.stream():
            await doc.reference.delete()