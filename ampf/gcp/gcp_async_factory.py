import logging
from collections.abc import Callable
from typing import Any, override

import httpx2
from google.cloud import firestore, storage
from pydantic import BaseModel

from ampf.base import BaseAsyncBlobStorage, BaseAsyncFactory, BaseAsyncStorage
from ampf.base.blob_model import BaseBlobMetadata, BlobLocation
from ampf.base.collection_def import CollectionDef
from ampf.gcp.gcp_factory import GcpFactory

from .gcp_async_blob_storage import GcpAsyncBlobStorage
from .gcp_async_storage import GcpAsyncStorage
from .gcp_base_factory import GcpBaseFactory

_log = logging.getLogger(__name__)


class GcpAsyncFactory(GcpBaseFactory, BaseAsyncFactory):
    def __init__(
        self,
        root_storage: str | None = None,
        bucket_name: str | None = None,
        project_id: str | None = None,
        database: str | None = None,
        httpx_async_client: httpx2.AsyncClient | None = None,
        otel: bool | None = None,
        collection_defs: list[CollectionDef[Any]] | None = None,
    ):
        if otel is None:
            _log.warning("Add otel parameter to constructor!")
        super().__init__(root_storage, bucket_name, otel or False)
        BaseAsyncFactory.__init__(self, collection_defs)
        self._async_db: firestore.AsyncClient | None = None
        self._storage_client: storage.Client | None = None
        self._httpx_async_client = httpx_async_client
        self.project_id = project_id
        self.database = database
        self.sync_factory: GcpFactory | None = None

    def get_async_client(self) -> firestore.AsyncClient:
        if not self._async_db:
            self._async_db = firestore.AsyncClient(project=self.project_id, database=self.database)
        return self._async_db

    def get_storage_client(self) -> storage.Client:
        if not self._storage_client:
            self._storage_client = storage.Client(project=self.project_id)
        return self._storage_client

    @override
    def get_sync_factory(self) -> GcpFactory:
        if not self.sync_factory:
            self.sync_factory = GcpFactory(
                root_storage=self.root_storage,
                bucket_name=self.bucket_name,
                project_id=self.project_id,
                database=self.database,
                otel=self._otel,
                collection_defs=list(self._collection_defs.values()),
            )
            self.sync_factory._collection_defs = self._collection_defs
            self.sync_factory._type_to_collection_defs = self._type_to_collection_defs
        return self.sync_factory

    @override
    def get_project_id(self) -> str:
        if not self.project_id:
            self.project_id = self.get_async_client().project
        return self.project_id

    def create_storage[T: BaseModel](
        self, collection_name: str, clazz: type[T], key: Callable[[T], str] | None = None
    ) -> BaseAsyncStorage[T]:
        return GcpAsyncStorage(
            collection_name,
            clazz,
            db=self.get_async_client(),
            key=key,
            root_storage=self.root_storage,
        )

    def create_blob_storage[T: BaseBlobMetadata](
        self,
        collection_name: str,
        clazz: type[T] | None = None,
        content_type: str = "text/plain",
        bucket_name: str | None = None,
    ) -> BaseAsyncBlobStorage[T]:
        bucket_name = bucket_name or self.bucket_name
        if not bucket_name:
            raise ValueError(
                "Bucket name must be provided either during factory initialization or when calling create_blob_storage."
            )
        return GcpAsyncBlobStorage(
            bucket_name=bucket_name,
            collection_name=collection_name,
            clazz=clazz or BaseBlobMetadata,
            content_type=content_type,
            storage_client=self.get_storage_client(),
            httpx_async_client=self._httpx_async_client,
        )

    def create_blob_location(self, name: str, bucket: str | None = None) -> BlobLocation:
        """Creates a BlobLocation object.

        Args:
            name: The name of the blob.
            bucket: The name of the bucket.
        Returns:
            The created BlobLocation object.
        """
        return BlobLocation(name=name, bucket=bucket or self.bucket_name)
