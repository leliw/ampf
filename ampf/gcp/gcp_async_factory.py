from typing import Callable, Optional, Type, override

from google.cloud import firestore, storage
from pydantic import BaseModel

from ampf.base import BaseAsyncBlobStorage, BaseAsyncFactory, BaseAsyncStorage
from ampf.base.blob_model import BaseBlobMetadata, BlobLocation

from .gcp_async_blob_storage import GcpAsyncBlobStorage
from .gcp_async_storage import GcpAsyncStorage
from .gcp_base_factory import GcpBaseFactory


class GcpAsyncFactory(GcpBaseFactory, BaseAsyncFactory):
    def __init__(self, root_storage: Optional[str] = None, bucket_name: Optional[str] = None):
        super().__init__(root_storage, bucket_name)
        self._async_db = firestore.AsyncClient()
        self._storage_client = storage.Client()

    @override
    def get_project_id(self) -> str:
        return self._async_db.project

    def create_storage[T: BaseModel](
        self, collection_name: str, clazz: Type[T], key: Optional[Callable[[T], str]] = None
    ) -> BaseAsyncStorage[T]:
        return GcpAsyncStorage(
            collection_name,
            clazz,
            db=self._async_db,
            key=key,
            root_storage=self.root_storage,
        )

    def create_blob_storage[T: BaseBlobMetadata](
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

    def create_blob_location(self, name: str, bucket: Optional[str] = None) -> BlobLocation:
        """Creates a BlobLocation object.

        Args:
            name: The name of the blob.
            bucket: The name of the bucket.
        Returns:
            The created BlobLocation object.
        """
        return BlobLocation(name=name, bucket=bucket or self.bucket_name)
