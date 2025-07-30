from typing import Callable, Optional, Type

from google.cloud import firestore
from pydantic import BaseModel

from ..base import BaseAsyncStorage, BaseBlobStorage, BaseFactory, BaseStorage
from .gcp_async_storage import GcpAsyncStorage
from .gcp_blob_storage import GcpBlobStorage
from .gcp_storage import GcpStorage


class GcpFactory(BaseFactory):
    _db = None

    @classmethod
    def init_client(cls, default_bucket: Optional[str] = None):
        if not cls._db:
            cls._db = firestore.Client()
            cls._async_db = firestore.AsyncClient()
        if default_bucket:
            GcpBlobStorage.init_client(default_bucket)

    @classmethod
    def get_db(cls) -> firestore.Client:
        if not cls._db:
            cls._db = firestore.Client()
        return cls._db

    @classmethod
    def get_async_db(cls) -> firestore.AsyncClient:
        if not cls._async_db:
            cls._async_db = firestore.AsyncClient()
        return cls._async_db

    def __init__(self, root_storage: Optional[str] = None, bucket_name: Optional[str] = None):
        self.root_storage = root_storage[:-1] if root_storage and root_storage.endswith("/") else root_storage
        if not self._db:
            self.init_client(default_bucket=bucket_name)

    def create_storage[T: BaseModel](
        self,
        collection_name: str,
        clazz: Type[T],
        key_name: Optional[str] = None,
        key: Optional[Callable[[T], str]] = None,
    ) -> BaseStorage[T]:
        return GcpStorage(
            collection_name,
            clazz,
            db=self.get_db(),
            key_name=key_name,
            key=key,
            root_storage=self.root_storage,
        )

    def create_blob_storage[T: BaseModel](
        self, collection_name: str, clazz: Optional[Type[T]] = None, content_type: str = "text/plain"
    ) -> BaseBlobStorage[T]:
        return GcpBlobStorage(collection_name, clazz, content_type)

    def create_async_storage[T: BaseModel](
        self,
        collection_name: str,
        clazz: Type[T],
        key_name: Optional[str] = None,
        key: Optional[Callable[[T], str]] = None,
    ) -> BaseAsyncStorage[T]:
        return GcpAsyncStorage(
            f"{self.root_storage}/{collection_name}" if self.root_storage else collection_name,
            clazz,
            db=self.get_async_db(),
            key_name=key_name,
            key=key,
        )
