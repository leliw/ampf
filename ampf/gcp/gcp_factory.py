import logging
from typing import Callable, Optional, Type

from google.cloud import firestore, storage
from pydantic import BaseModel

from ..base import BaseAsyncStorage, BaseBlobStorage, BaseFactory, BaseStorage
from .gcp_async_storage import GcpAsyncStorage
from .gcp_blob_storage import GcpBlobStorage
from .gcp_storage import GcpStorage


class GcpFactory(BaseFactory):
    _log = logging.getLogger(__name__)

    def __init__(self, root_storage: Optional[str] = None, bucket_name: Optional[str] = None):
        self.root_storage = root_storage[:-1] if root_storage and root_storage.endswith("/") else root_storage
        self.bucket_name = bucket_name
        self._log.debug("Using GcpFactory with root_storage=%s and bucket_name=%s", self.root_storage, self.bucket_name)
        self._db = firestore.Client()
        self._async_db = firestore.AsyncClient()
        self._storage_client = storage.Client()

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
            db=self._db,
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
        self._log.debug("Creating async storage with root_storage=%s", self.root_storage)
        return GcpAsyncStorage(
            f"{self.root_storage}/{collection_name}" if self.root_storage else collection_name,
            clazz,
            db=self._async_db,
            key_name=key_name,
            key=key,
        )
