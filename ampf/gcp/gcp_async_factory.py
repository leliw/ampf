from typing import Callable, Type

from google.cloud import firestore
from pydantic import BaseModel

from ampf.base import BaseAsyncFactory, BaseAsyncStorage, BaseBlobStorage

from .gcp_blob_storage import GcpBlobStorage
from .gcp_storage import GcpStorage


class GcpAsyncFactory(BaseAsyncFactory):
    _db = None

    @classmethod
    def init_client(cls, default_bucket: str = None):
        if not GcpAsyncFactory._db:
            GcpAsyncFactory._db = firestore.AsyncClient()
        if default_bucket:
            GcpBlobStorage.init_client(default_bucket)

    def create_storage[T: BaseModel](
        self,
        collection_name: str,
        clazz: Type[T],
        key_name: str = None,
        key: Callable[[T], str] = None,
    ) -> BaseAsyncStorage[T]:
        return GcpStorage(
            collection_name, clazz, db=GcpAsyncFactory._db, key_name=key_name, key=key
        )

    def create_blob_storage[T: BaseModel](
        self, collection_name: str, clazz: Type[T] = None, content_type: str = None
    ) -> BaseBlobStorage[T]:
        return GcpBlobStorage(collection_name, clazz, content_type)
