import logging
from typing import Callable, Optional, Type, override

from google.cloud import firestore, storage
from pydantic import BaseModel

from ..base import BaseAsyncStorage, BaseBlobStorage, BaseFactory, BaseStorage
from .gcp_async_storage import GcpAsyncStorage
from .gcp_base_factory import GcpBaseFactory
from .gcp_blob_storage import GcpBlobStorage
from .gcp_storage import GcpStorage


class GcpFactory(GcpBaseFactory, BaseFactory):
    _log = logging.getLogger(__name__)

    def __init__(self, root_storage: Optional[str] = None, bucket_name: Optional[str] = None):
        super().__init__(root_storage, bucket_name)
        self._db = firestore.Client()
        self._async_db = firestore.AsyncClient()
        self._storage_client = storage.Client()

    @override
    def get_project_id(self) -> str:
        return self._db.project

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
        self,
        collection_name: str,
        clazz: Optional[Type[T]] = None,
        content_type: str = "text/plain",
        bucket_name: Optional[str] = None,
    ) -> BaseBlobStorage[T]:
        bucket_name = bucket_name or self.bucket_name
        if not bucket_name:
            raise ValueError(
                "Bucket name must be provided either during factory initialization or when calling create_blob_async_storage."
            )
        return GcpBlobStorage(
            bucket_name=bucket_name,
            collection_name=collection_name,
            clazz=clazz,
            content_type=content_type,
            storage_client=self._storage_client,
        )

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
            key=key or key_name,
        )
