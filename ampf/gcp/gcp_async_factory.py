from typing import Callable, Optional, Type

from google.cloud import firestore, storage
from pydantic import BaseModel

from ampf.base import BaseAsyncBlobStorage, BaseAsyncFactory, BaseAsyncStorage
from ampf.gcp.gcp_async_blob_storage import GcpAsyncBlobStorage
from ampf.gcp.gcp_async_storage import GcpAsyncStorage


class GcpAsyncFactory(BaseAsyncFactory):
    def __init__(self, root_storage: Optional[str] = None, bucket_name: Optional[str] = None):
        self.root_storage = root_storage[:-1] if root_storage and root_storage.endswith("/") else root_storage
        self.bucket_name = bucket_name
        self._async_db = firestore.AsyncClient()
        self._storage_client = storage.Client()

    def create_storage[T: BaseModel](
        self,
        collection_name: str,
        clazz: Type[T],
        key_name: Optional[str] = None,
        key: Optional[Callable[[T], str]] = None,
    ) -> BaseAsyncStorage[T]:
        return GcpAsyncStorage(
            collection_name,
            clazz,
            db=self._async_db,
            key_name=key_name,
            key=key,
        )

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
        return GcpAsyncBlobStorage(
            bucket_name=bucket_name,
            collection_name=collection_name,
            clazz=clazz,
            content_type=content_type,
            storage_client=self._storage_client,
        )
