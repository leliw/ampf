from typing import Type
from google.cloud import firestore
from pydantic import BaseModel

from ampf.base import BaseFactory, BaseStorage
from .gcp_storage import GcpStorage


class GcpFactory(BaseFactory):
    _db = None

    @classmethod
    def init_client(cls):
        if not GcpFactory._db:
            GcpFactory._db = firestore.Client()

    def create_storage[T: BaseModel](
        self, collection_name: str, clazz: Type[T], key_name: str = None
    ) -> BaseStorage[T]:
        return GcpStorage(collection_name, clazz, db=GcpFactory._db, key_name=key_name)
