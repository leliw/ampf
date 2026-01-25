import asyncio
import json
import mimetypes
import os
from pathlib import Path
from typing import AsyncGenerator, Awaitable, Callable, Optional, Type, override

import aiofiles

from ampf.base.blob_model import BaseBlobMetadata
from ampf.base.exceptions import KeyExistsException, KeyNotExistsException

from ..base import Blob, BlobHeader
from ..base.base_async_blob_storage import BaseAsyncBlobStorage


class LocalAsyncBlobStorage[T: BaseBlobMetadata](BaseAsyncBlobStorage[T]):
    chunk_size = 1024 * 1024  # 1MB

    def __init__(
        self,
        collection_name: str,
        metadata_type: Optional[Type[T]] = None,
        content_type: Optional[str] = None,
        root_path: Optional[Path] = None,
    ):
        self.collection_name = collection_name
        self.clazz = metadata_type or BaseBlobMetadata  # type: ignore
        self.base_path = Path(root_path / collection_name) if root_path else Path(collection_name)
        self.content_type = content_type
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.transaction_lock = asyncio.Lock()

    def _get_meta_path(self, key: str) -> Path:
        path = self.base_path / f"{key}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _find_data_path(self, key: str) -> Optional[Path]:
        """Find data file path for the given key.

        This method searches for:
        1. A file named exactly `key` (e.g., 'mydata' or 'archive.tar').
        2. Files matching `key.*` (e.g., 'mydata.txt', 'archive.tar.gz').

        In second case, `.json` file is ignored as it is considered metadata.
        The direct match (case 1) is prioritized if found and valid.
        """
        # Check for a direct match (e.g., file named 'key' or 'key.original_ext')
        exact_match_path = self.base_path / key
        if exact_match_path.is_file():
            return exact_match_path

        # If no direct match, or if the direct match was a .json file or not a file,
        # search for files with the key name plus an additional extension (e.g., key.ext)
        matches_with_extension = list(self.base_path.glob(f"{key}.*"))

        valid_extended_matches = [m for m in matches_with_extension if m.is_file() and m.suffix != ".json"]
        return valid_extended_matches[0] if valid_extended_matches else None

    def _generate_data_path(self, key: str, content_type: Optional[str]) -> Path:
        """Generate a data path with appropriate extension."""
        ext = mimetypes.guess_extension(content_type or "")
        ext = ext or ""  # fallback to no extension
        if ext == ".json":
            ext = "._json"  # JSON extension is used by metadatafile
        if ext and key.endswith(ext):
            key = key[: -len(ext)]
        return self.base_path / f"{key}{ext}"

    @override
    async def upload_async(self, blob: Blob[T]) -> None:
        data_path = self._generate_data_path(blob.name, blob.metadata.content_type)
        meta_path = self._get_meta_path(blob.name)
        os.makedirs(data_path.parent, exist_ok=True)

        async def write_data():
            async with aiofiles.open(data_path, "wb") as f:
                async for chunk in blob.stream():
                    await f.write(chunk)
            # with open(data_path, "wb") as f:
            #     with blob.data() as data:
            #         shutil.copyfileobj(data, f)

        async def write_meta():
            async with aiofiles.open(meta_path, "w", encoding="utf-8") as f:
                await f.write(blob.metadata.model_dump_json())

        await asyncio.gather(write_data(), write_meta())

    @override
    async def download_async(self, key: str) -> Blob[T]:
        meta_path = self._get_meta_path(key)
        data_path = self._find_data_path(key)

        if not data_path or (self.clazz and not meta_path.exists()):
            raise KeyNotExistsException(self.collection_name, self.clazz, key)

        metadata = await self.get_metadata(key) if self.clazz else None
        f = await asyncio.to_thread(open, data_path, "rb")
        return Blob[T](name=key, metadata=metadata, data=f)

    @override
    def delete(self, key: str) -> None:
        data_path = self._find_data_path(key)
        meta_path = self._get_meta_path(key)

        if data_path and data_path.exists():
            data_path.unlink()
            if meta_path.exists():
                meta_path.unlink()
        else:
            raise KeyNotExistsException(self.collection_name, self.clazz, key)

    @override
    def exists(self, key: str) -> bool:
        data_path = self._find_data_path(key)
        return data_path is not None and self._get_meta_path(key).exists()

    @override
    async def list_blobs(self, prefix: Optional[str] = None) -> AsyncGenerator[BlobHeader[T]]:
        # Use rglob to recursively find all .json files in the directory tree.
        for meta_file in self.base_path.rglob("*.json"):
            # Calculate the key by making the path relative to the base_path
            # and removing the .json suffix.
            key = str(meta_file.relative_to(self.base_path))[:-5]

            if prefix and not key.startswith(prefix):
                continue
            metadata = await self.get_metadata(key)
            yield BlobHeader(name=key, metadata=metadata)

    @override
    async def get_metadata(self, name: str) -> T:
        if not self.clazz:
            raise ValueError("clazz must be set")
        meta_path = self._get_meta_path(name)
        try:
            async with aiofiles.open(meta_path, "r", encoding="utf-8") as f:
                meta_raw = json.loads(await f.read())
            if "metadata" in meta_raw:
                return self.clazz.model_validate(meta_raw["metadata"])  # type: ignore
            else:
                return self.clazz.model_validate(meta_raw)  # type: ignore
        except FileNotFoundError:
            raise KeyNotExistsException

    @override
    async def _upsert_transactional(
        self,
        name: str,
        create_func: Optional[Callable[[str], Awaitable[Blob[T]]]] = None,
        update_func: Optional[Callable[[Blob[T]], Awaitable[Blob[T]]]] = None,
    ) -> None:
        async with self.transaction_lock:
            try:
                blob = await self.download_async(name)
                if update_func:
                    updated_blob = await update_func(blob)
                    await self.upload_async(updated_blob)
                else:
                    raise KeyExistsException(self.collection_name, self.clazz, name)
            except KeyNotExistsException as e:
                if not create_func:
                    raise e
                created_blob = await create_func(name)
                await self.upload_async(created_blob)


class LocalBlobAsyncStorage[T: BaseBlobMetadata](LocalAsyncBlobStorage[T]):
    pass
