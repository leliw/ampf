import asyncio
import logging
from contextlib import contextmanager
from io import BytesIO
from mimetypes import guess_file_type
from tempfile import SpooledTemporaryFile
from typing import Any, AsyncGenerator, BinaryIO, Generator, Optional, Self
from uuid import uuid4

from pydantic import BaseModel

_log = logging.getLogger(__name__)

try:
    from fastapi import UploadFile
except ImportError:
    type UploadFile = Any


type BlobData = BinaryIO | SpooledTemporaryFile


class BlobLocation(BaseModel):
    """Blob location, containing bucket and name."""

    bucket: Optional[str] = None
    name: str


class BaseBlobMetadata(BaseModel):
    content_type: str = "application/octet-stream"
    filename: Optional[str] = None

    @classmethod
    def create(cls, file: UploadFile) -> Self:
        if file.content_type is None or file.content_type in ["application/octet-stream", "video/vnd.dlna.mpeg-tts"]:
            return cls.from_filename(file.filename or "")
        else:
            return cls(filename=file.filename or None, content_type=file.content_type)

    @classmethod
    def from_filename(cls, filename: str) -> Self:
        ext = filename.split(".")[-1]
        if ext == "ts":
            content_type = "text/typescript"
        else:
            content_type, _ = guess_file_type(filename)
        content_type = content_type or "application/octet-stream"
        return cls(filename=filename or None, content_type=content_type)


empty_blob_metadata = BaseBlobMetadata(content_type="")


class BlobCreate[T: BaseBlobMetadata]:
    def __init__(
        self,
        name: Optional[str] = None,
        data: Optional[BlobData] = None,
        content: Optional[bytes | str] = None,
        metadata: T = BaseBlobMetadata(),
    ):
        self.name = name
        self.data = data
        self.content = content
        self.metadata = metadata

    @classmethod
    def from_upload_file(cls, file: UploadFile, metadata: T = empty_blob_metadata) -> "BlobCreate[T]":
        if metadata == empty_blob_metadata:
            metadata = metadata.__class__.create(file)
        return cls(data=file.file, metadata=metadata)

    @classmethod
    def from_content(
        cls, content: bytes | str, content_type: str = "application/octet-stream"
    ) -> "BlobCreate[BaseBlobMetadata]":
        return BlobCreate[BaseBlobMetadata](content=content, metadata=BaseBlobMetadata(content_type=content_type))


class BlobError(ValueError):
    def __init__(self):
        super().__init__("Provide either 'data' or 'content', but not both")


class Blob[T: BaseBlobMetadata]:
    """Blob, containing data and metadata. Data can be a file-like object or bytes. Metadata is optional."""

    def __init__(
        self,
        name: str,
        data: Optional[BlobData] = None,
        content: Optional[bytes | str] = None,
        content_type: Optional[str] = None,
        metadata: T = empty_blob_metadata,
    ):
        self.name = name
        if metadata == empty_blob_metadata:
            if content_type:
                metadata = metadata.__class__(content_type=content_type)
            else:
                metadata = metadata.__class__()
        elif metadata and content_type:
            metadata.content_type = content_type
        self.metadata: T = metadata
        self._data: Optional[BlobData] = data
        self._content: Optional[bytes] = None
        if content:
            self._content = content.encode() if isinstance(content, str) else content
        if not data and not content:
            raise BlobError()
        if data and content:
            raise BlobError()

    @property
    def content_type(self) -> str:
        return self.metadata.content_type

    @classmethod
    def create(cls, value_create: BlobCreate) -> "Blob":
        return cls(
            name=value_create.name or str(uuid4()),
            data=value_create.data,
            content=value_create.content,
            metadata=value_create.metadata,
        )

    @classmethod
    def from_upload_file(cls, file: UploadFile, metadata: T = empty_blob_metadata) -> "Blob[T]":
        return cls.create(BlobCreate.from_upload_file(file, metadata))

    @contextmanager
    def data(self) -> Generator[BlobData]:
        if not self._data:
            if self._content:
                data = BytesIO(self._content)
            else:
                raise BlobError()
        else:
            data = self._data
            data.seek(0)
        yield data
        data.close()
        self._data = None

    @property
    def content(self) -> bytes:
        if self._content:
            return self._content
        else:
            with self.data() as data:
                self._content = data.read()
            self._data = None
            return self._content

    @content.setter
    def content(self, v: bytes | str):
        if self._data:
            raise BlobError()
        else:
            self._content = v.encode() if isinstance(v, str) else v

    async def stream(self, chunk_size=1024 * 1024) -> AsyncGenerator[bytes]:
        if self._content:
            # If content is already loaded in memory, yield chunks from it
            for i in range(0, len(self._content), chunk_size):
                yield self._content[i : i + chunk_size]
            return
        else:
            with self.data() as data:
                while True:
                    # data.read() jest synchroniczne, więc delegujemy do wątku
                    chunk = await asyncio.to_thread(data.read, chunk_size)
                    if not chunk:
                        break
                    yield chunk


class BlobHeader[T: BaseBlobMetadata](BaseModel):
    """Header for a blob, containing metadata."""

    name: str
    metadata: T

    @classmethod
    def create(cls, blob: Blob[T]):
        return cls(name=blob.name, metadata=blob.metadata)
