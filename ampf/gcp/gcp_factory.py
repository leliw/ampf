import logging
from typing import Callable, Type, override

from google.cloud import firestore, storage
from pydantic import BaseModel

from ampf.base.blob_model import BaseBlobMetadata

from ..base import BaseAsyncStorage, BaseBlobStorage, BaseFactory, BaseStorage
from .gcp_async_storage import GcpAsyncStorage
from .gcp_base_factory import GcpBaseFactory
from .gcp_blob_storage import GcpBlobStorage
from .gcp_storage import GcpStorage

_log = logging.getLogger(__name__)


class GcpFactory(GcpBaseFactory, BaseFactory):
    def __init__(
        self,
        root_storage: str | None = None,
        bucket_name: str | None = None,
        project_id: str | None = None,
        database: str | None = None,
    ):
        super().__init__(root_storage, bucket_name)
        BaseFactory.__init__(self)
        self._db = firestore.Client(project=project_id, database=database)
        self._async_db = firestore.AsyncClient(project=project_id, database=database)
        self._storage_client = storage.Client(project=project_id)
        self.project_id = project_id or self._db.project
        self.database = database

    @override
    def get_project_id(self) -> str:
        return self.project_id

    def create_storage[T: BaseModel](
        self,
        collection_name: str,
        clazz: Type[T],
        key_name: str | None = None,
        key: Callable[[T], str] | None = None,
    ) -> BaseStorage[T]:
        return GcpStorage(
            collection_name,
            clazz,
            db=self._db,
            key_name=key_name,
            key=key,
            root_storage=self.root_storage,
        )

    def create_blob_storage[T: BaseBlobMetadata](
        self,
        collection_name: str,
        clazz: Type[T] = BaseBlobMetadata,
        content_type: str = "text/plain",
        bucket_name: str | None = None,
    ) -> BaseBlobStorage[T]:
        bucket_name = bucket_name or self.bucket_name
        if not bucket_name:
            raise ValueError(
                "Bucket name must be provided either during factory initialization or when calling create_blob_storage."
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
        key_name: str | None = None,
        key: Callable[[T], str] | None = None,
    ) -> BaseAsyncStorage[T]:
        _log.debug("Creating async storage with root_storage=%s", self.root_storage)
        return GcpAsyncStorage(
            f"{self.root_storage}/{collection_name}" if self.root_storage else collection_name,
            clazz,
            db=self._async_db,
            key=key or key_name,
        )
