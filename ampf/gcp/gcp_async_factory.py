from typing import Callable, Optional, Type

from google.cloud import firestore
from pydantic import BaseModel

from ampf.base import BaseAsyncFactory, BaseAsyncStorage, BaseBlobStorage
from ampf.gcp.gcp_async_storage import GcpAsyncStorage

from .gcp_blob_storage import GcpBlobStorage


class GcpAsyncFactory(BaseAsyncFactory):
    _db = None

    @classmethod
    def init_client(cls, default_bucket: Optional[str] = None):
        if not GcpAsyncFactory._db:
            GcpAsyncFactory._db = firestore.AsyncClient()
        if default_bucket:
            GcpBlobStorage.init_client(default_bucket)

    def __init__(self, root_storage: Optional[str] = None, bucket_name: Optional[str] = None):
        self.root_storage = root_storage[:-1] if root_storage and root_storage.endswith("/") else root_storage
        self.bucket_name = bucket_name
        if not self._db:
            self.init_client(default_bucket=bucket_name)

    def create_storage[T: BaseModel](
        self,
        collection_name: str,
        clazz: Type[T],
        key_name: Optional[str] = None,
        key: Optional[Callable[[T], str]] = None,
    ) -> BaseAsyncStorage[T]:
        return GcpAsyncStorage(collection_name, clazz, db=GcpAsyncFactory._db, key_name=key_name, key=key)

    def create_blob_storage[T: BaseModel](
        self, collection_name: str, clazz: Optional[Type[T]] = None, content_type: str = "text/plain"
    ) -> BaseBlobStorage[T]:
        return GcpBlobStorage(collection_name, clazz, content_type, bucket_name=self.bucket_name)
