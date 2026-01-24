import asyncio
from contextlib import contextmanager
from io import BytesIO
from mimetypes import guess_file_type
from tempfile import SpooledTemporaryFile
from typing import AsyncGenerator, BinaryIO, Generator, Optional
from uuid import uuid4

from fastapi import UploadFile
from pydantic import BaseModel

type BlobData = BinaryIO | SpooledTemporaryFile


class BlobLocation(BaseModel):
    """Blob location, containing bucket and name."""

    bucket: Optional[str] = None
    name: str


class BlobCreate[T: BaseModel]:
    def __init__(
        self,
        name: Optional[str] = None,
        data: Optional[BlobData] = None,
        content: Optional[bytes | str] = None,
        content_type: Optional[str] = None,
        metadata: Optional[T] = None,
    ):
        self.name = name
        self.data = data
        self.content = content
        self.content_type = content_type
        self.metadata = metadata

    @classmethod
    def create(cls, file: UploadFile, metadata: Optional[T] = None) -> "BlobCreate":
        if file.content_type is None or file.content_type in ["application/octet-stream", "video/vnd.dlna.mpeg-tts"]:
            content_type, _ = guess_file_type(file.filename) if file.filename else (None, None)
            content_type = content_type or "application/octet-stream"
        else:
            content_type = file.content_type
        return cls(name=file.filename, data=file.file, content_type=content_type, metadata=metadata)


class BlobHeader[T: BaseModel](BaseModel):
    """Header for a blob, containing metadata."""

    name: str
    content_type: Optional[str] = None
    metadata: Optional[T] = None


class BlobError(ValueError):
    def __init__(self):
        super().__init__("Provide either 'data' or 'content', but not both")


class Blob[T: BaseModel]:
    """Blob, containing data and metadata. Data can be a file-like object or bytes. Metadata is optional."""

    def __init__(
        self,
        name: str,
        data: Optional[BlobData] = None,
        content: Optional[bytes | str] = None,
        content_type: Optional[str] = None,
        metadata: Optional[T] = None,
    ):
        self.name = name
        self.content_type = content_type
        self.metadata = metadata
        self._data: Optional[BlobData] = data
        self._content: Optional[bytes] = None
        if content:
            self.content = content
        if not data and not content:
            raise BlobError()
        if data and content:
            raise BlobError()

    @classmethod
    def create(cls, value_create: BlobCreate[T]) -> "Blob[T]":
        return cls(
            name=value_create.name or str(uuid4()),
            data=value_create.data,
            content=value_create.content,
            content_type=value_create.content_type,
            metadata=value_create.metadata,
        )

    @classmethod
    def create_from_file(cls, file: UploadFile, metadata: Optional[T] = None) -> "Blob[T]":
        return cls.create(BlobCreate.create(file, metadata))

    @contextmanager
    def data(self) -> Generator[BlobData]:
        if not self._data:
            if self._content:
                data = BytesIO(self._content)
            else:
                raise BlobError()
        else:
            data = self._data
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
