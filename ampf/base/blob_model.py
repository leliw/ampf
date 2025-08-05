from io import BytesIO, StringIO
from tempfile import SpooledTemporaryFile
from typing import BinaryIO, Optional

from pydantic import BaseModel, ConfigDict


class BlobCreate[T: BaseModel](BaseModel):
    """Blob, containing data and metadata. Data can be a file-like object or bytes. Metadata is optional."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: Optional[str] = None
    data: BinaryIO | BytesIO | bytes | str | SpooledTemporaryFile
    content_type: Optional[str] = None
    metadata: Optional[T] = None


class BlobHeader[T: BaseModel](BaseModel):
    """Header for a blob, containing metadata."""

    name: str
    content_type: Optional[str] = None
    metadata: Optional[T] = None


class Blob[T: BaseModel](BlobHeader[T]):
    """Blob, containing data and metadata. Data can be a file-like object or bytes. Metadata is optional."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    _data: Optional[BinaryIO | BytesIO | bytes | str] = None

    def __init__(
        self,
        name: str,
        data: BinaryIO | BytesIO | bytes | str | SpooledTemporaryFile,
        content_type: Optional[str] = None,
        metadata: Optional[T] = None,
    ):
        super().__init__(name=name, content_type=content_type, metadata=metadata)
        self.data = data  # type: ignore # setter

    @property
    def data(self) -> BinaryIO:
        if not self._data:
            raise ValueError("Data is not set")
        if isinstance(self._data, BinaryIO) or isinstance(self._data, SpooledTemporaryFile):
            self._data.seek(0)
            return self._data  # type: ignore
        elif isinstance(self._data, str):
            return BytesIO(self._data.encode())
        else:
            return BytesIO(self._data) # type: ignore

    @data.setter
    def data(self, value: BinaryIO | BytesIO | bytes | str):
        self._data = value
        if isinstance(value, str) and not self.content_type:
            self.content_type = "text/plain"
