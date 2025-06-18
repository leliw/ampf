from typing import Optional
from pydantic import BaseModel


class BlobHeader[T: BaseModel](BaseModel):
    key: str
    content_type: Optional[str] = None
    metadata: Optional[T] = None


class Blob[T: BaseModel](BlobHeader[T]):
    data: bytes
