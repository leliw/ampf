from typing import Any, Iterator, Optional, Type
from pydantic import BaseModel

from ampf.base import BaseBlobStorage, KeyNotExistsException
from ampf.base.base_blob_storage import FileNameMimeType
from ampf.base.blob_model import Blob


class InMemoryBlobStorage[T: BaseModel](BaseBlobStorage):
    """In memory blob storage implementation"""

    buckets = {}

    def __init__(self, bucket_name: str, clazz: Type[T], content_type: Optional[str] = None):
        self.bucket_name = bucket_name
        self.clazz = clazz
        self.content_type = content_type
        if self.bucket_name not in self.buckets:
            self.buckets[self.bucket_name] = {}

    def upload(self, blob: Blob[T]) -> None:
        self.buckets[self.bucket_name][blob.name] = blob
    
    def upload_blob(
        self, key: str, data: bytes, metadata: Optional[T] = None, content_type: Optional[str] = None
    ) -> None:
        if key not in self.buckets[self.bucket_name]:
            self.buckets[self.bucket_name][key] = {}
        self.buckets[self.bucket_name][key]["data"] = data
        if metadata:
            self.buckets[self.bucket_name][key]["metadata"] = metadata.model_copy(
                deep=True
            )
        if content_type:
            self.buckets[self.bucket_name][key]["content_type"] = content_type

    def download(self, key: str) -> Blob[T]:
        try:
            return self.buckets[self.bucket_name][key]
        except KeyError:
            raise KeyNotExistsException(collection_name=self.bucket_name, key=key, clazz=self.clazz)

    def download_blob(self, key: str) -> bytes:
        if key not in self.buckets[self.bucket_name]:
            raise KeyNotExistsException(self.bucket_name, self.clazz, key)
        return self.buckets[self.bucket_name][key]["data"]

    def put_metadata(self, key: str, metadata: T) -> None:
        self.buckets[self.bucket_name][key]["metadata"] = metadata.model_copy(deep=True)

    def get_metadata(self, key: str) -> T:
        if key not in self.buckets[self.bucket_name]:
            raise KeyNotExistsException(self.bucket_name, self.clazz, key)
        return self.buckets[self.bucket_name][key]["metadata"]

    def delete(self, key: str):
        if key not in self.buckets[self.bucket_name]:
            raise KeyNotExistsException(self.bucket_name, self.clazz, key)
        self.buckets[self.bucket_name].pop(key, None)

    def keys(self) -> Iterator[str]:
        return self.buckets[self.bucket_name].keys()

    def drop(self) -> None:
        self.buckets.pop(self.bucket_name, None)

    def list_blobs(self, dir: Optional[str] = None) -> Iterator[Any]:
        if self.bucket_name not in self.buckets:
            return
        if dir:
            prefix = dir if dir[-1] == "/" else dir + "/"
        else:
            prefix = None
        i = len(prefix) if prefix else 0
        for k in self.keys():
            if not prefix or k.startswith(prefix):
                yield FileNameMimeType(
                    name=k[i:],
                    mime_type=self.buckets[self.bucket_name][k]["content_type"],
                )

    def move_blob(self, source_key: str, dest_key: str):
        self.buckets[self.bucket_name][dest_key] = self.buckets[self.bucket_name].pop(
            source_key
        )

    def delete_folder(self, folder_name: str):
        if self.bucket_name not in self.buckets:
            return
        prefix = folder_name if folder_name[-1] == "/" else folder_name + "/"
        deletable = []
        for k in self.keys():
            if k.startswith(prefix):
                deletable.append(k)
        for k in deletable:
            self.delete(k)
