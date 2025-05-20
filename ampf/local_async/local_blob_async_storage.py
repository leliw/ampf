import asyncio
import json
import mimetypes
from pathlib import Path
from typing import List, Optional, Type, override

from pydantic import BaseModel

from ..base import Blob, BlobHeader
from ..base.base_blob_async_storage import BaseBlobAsyncStorage


class LocalBlobAsyncStorage[T: BaseModel](BaseBlobAsyncStorage[T]):
    def __init__(
        self,
        collection_name: str,
        metadata_type: Type[T],
        content_type: str = None,
        root_path: Optional[Path] = None,
    ):
        self.base_path = (
            Path(root_path / collection_name) if root_path else Path(collection_name)
        )
        self.metadata_type = metadata_type
        self.content_type = content_type
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_meta_path(self, key: str) -> Path:
        return self.base_path / f"{key}.json"

    def _find_data_path(self, key: str) -> Optional[Path]:
        """Find data file path using key with any extension."""
        matches = list(self.base_path.glob(f"{key}.*"))
        # Filter out .json files, as they are used for metadata
        matches = [match for match in matches if match.suffix != ".json"]
        return matches[0] if matches else None

    def _generate_data_path(self, key: str, content_type: Optional[str]) -> Path:
        """Generate a data path with appropriate extension."""
        ext = mimetypes.guess_extension(content_type or "")
        ext = ext if ext else ""  # fallback to no extension
        return self.base_path / f"{key}{ext}"

    @override
    async def upload_async(self, blob: Blob[T]) -> None:
        data_path = self._generate_data_path(blob.key, blob.content_type)
        meta_path = self._get_meta_path(blob.key)

        async def write_data():
            with open(data_path, "wb") as f:
                f.write(blob.data)

        async def write_meta():
            meta_dict = {
                "key": blob.key,
                "content_type": blob.content_type,
                "metadata": blob.metadata.model_dump(),
            }
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta_dict, f)

        await asyncio.gather(write_data(), write_meta())

    @override
    async def download_async(self, key: str) -> Blob[T]:
        meta_path = self._get_meta_path(key)
        data_path = self._find_data_path(key)

        if not data_path or not meta_path.exists():
            raise FileNotFoundError(f"Blob with key '{key}' not found.")

        with open(data_path, "rb") as f:
            data = f.read()

        with open(meta_path, "r", encoding="utf-8") as f:
            meta_raw = json.load(f)

        metadata = self.metadata_type.model_validate(meta_raw["metadata"])
        content_type = meta_raw.get("content_type")

        return Blob[T](key=key, metadata=metadata, content_type=content_type, data=data)

    @override
    def delete(self, key: str) -> None:
        data_path = self._find_data_path(key)
        meta_path = self._get_meta_path(key)

        if data_path and data_path.exists():
            data_path.unlink()
        if meta_path.exists():
            meta_path.unlink()

    @override
    def exists(self, key: str) -> bool:
        data_path = self._find_data_path(key)
        return data_path is not None and self._get_meta_path(key).exists()

    @override
    def list_blobs(self, prefix: Optional[str] = None) -> List[BlobHeader[T]]:
        headers = []
        for meta_file in self.base_path.glob("*.json"):
            key = meta_file.stem
            if prefix and not key.startswith(prefix):
                continue

            with open(meta_file, "r", encoding="utf-8") as f:
                meta_raw = json.load(f)

            metadata = self.metadata_type.model_validate(meta_raw["metadata"])
            content_type = meta_raw.get("content_type")

            headers.append(
                BlobHeader(key=key, metadata=metadata, content_type=content_type)
            )
        return headers
