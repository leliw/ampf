from typing import Callable, Optional, Type

from google.cloud import firestore
from pydantic import BaseModel

from ampf.base import BaseAsyncFactory, BaseAsyncStorage, BaseAsyncBlobStorage
from ampf.gcp.gcp_async_storage import GcpAsyncStorage
from ampf.gcp.gcp_blob_async_storage import GcpBlobAsyncStorage

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
        self,
        collection_name: Optional[str] = None,
        clazz: Optional[Type[T]] = None,
        content_type: str = "text/plain",
        bucket_name: Optional[str] = None,
    ) -> BaseAsyncBlobStorage[T]:
        bucket_name = bucket_name or self.bucket_name
        if not bucket_name:
            raise ValueError(
                "Bucket name must be provided either during factory initialization or when calling create_blob_async_storage."
            )
        return GcpBlobAsyncStorage(
            bucket_name=bucket_name, collection_name=collection_name, clazz=clazz, content_type=content_type
        )
