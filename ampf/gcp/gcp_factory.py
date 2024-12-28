from typing import Type
from google.cloud import firestore
from pydantic import BaseModel

from ampf.base import BaseFactory, BaseStorage, BaseBlobStorage
from .gcp_storage import GcpStorage
from .gcp_blob_storage import GcpBlobStorage


class GcpFactory(BaseFactory):
    _db = None

    @classmethod
    def init_client(cls, default_bucket: str = None):
        if not GcpFactory._db:
            GcpFactory._db = firestore.Client()
        if default_bucket:
            GcpBlobStorage.init_client(default_bucket)

    def create_storage[T: BaseModel](
        self, collection_name: str, clazz: Type[T], key_name: str = None
    ) -> BaseStorage[T]:
        return GcpStorage(collection_name, clazz, db=GcpFactory._db, key_name=key_name)

    def create_blob_storage[T: BaseModel](
        self, collection_name: str, clazz: Type[T] = None, content_type: str = None
    ) -> BaseBlobStorage[T]:
        return GcpBlobStorage(collection_name, clazz, content_type)
