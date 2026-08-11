import logging
from collections.abc import Callable
from typing import override

from google.cloud import firestore, storage
from pydantic import BaseModel

from ampf.base.blob_model import BaseBlobMetadata

from ..base import BaseBlobStorage, BaseFactory, BaseStorage
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
        otel: bool | None = None,
    ):
        super().__init__(root_storage, bucket_name, otel=otel or False)
        BaseFactory.__init__(self)
        self._db = firestore.Client(project=project_id, database=database)
        self._storage_client: storage.Client | None = None
        self.project_id = project_id or self._db.project
        self.database = database

    def get_storage_client(self) -> storage.Client:
        if not self._storage_client:
            self._storage_client = storage.Client(project=self.project_id)
        return self._storage_client


    @override
    def get_project_id(self) -> str:
        return self.project_id

    def create_storage[T: BaseModel](
        self,
        collection_name: str,
        clazz: type[T],
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
        clazz: type[T] = BaseBlobMetadata,
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
            storage_client=self.get_storage_client(),
        )
