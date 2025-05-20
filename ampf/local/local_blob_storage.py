import json
import logging
import os
import shutil
from typing import Iterator, override

from pydantic import BaseModel

from ampf.base import BaseBlobStorage
from ampf.base.base_blob_storage import FileNameMimeType
from ampf.base.exceptions import KeyNotExistsException

from ..mimetypes import get_content_type, get_extension
from .file_storage import FileStorage, StrPath


class LocalBlobStorage[T: BaseModel](BaseBlobStorage[T], FileStorage):
    """Stores binary data on the local disk.

    Args:
        bucket_name: The name of the subfolder where files are stored.
        clazz: The Pydantic model for metadata (optional).
        content_type: The default content type for blobs (optional).
        subfolder_characters: The number of initial characters of the filename used to create an optional subfolder.
        root_path: The root path for storing data.
    """

    def __init__(
        self,
        bucket_name: str,
        clazz: BaseModel = None,
        content_type: str = None,
        subfolder_characters: int = None,
        root_path: StrPath = None,
    ):
        # Initialize BaseBlobStorage with collection name, metadata class, and content type
        BaseBlobStorage.__init__(
            self, collection_name=bucket_name, clazz=clazz, content_type=content_type
        )
        default_ext = get_extension(content_type)[1:] if content_type else None
        FileStorage.__init__(
            self,
            folder_name=bucket_name,
            subfolder_characters=subfolder_characters,
            default_ext=default_ext,
            root_path=root_path,
        )
        self.clazz = clazz
        self._log = logging.getLogger(__name__)

    @override
    def upload_blob(
        self,
        key: str,
        data: bytes,
        metadata: BaseModel = None,
        content_type: str = None,
    ) -> None:
        """Uploads a blob to the local storage.

        Args:
            key: The key (filename) of the blob.
            data: The binary data of the blob.
            metadata: Optional Pydantic model for metadata.
            content_type: Optional content type of the blob.
        """
        if content_type:
            ext = get_extension(content_type)
            ext = ext[1:] if ext else None
        else:
            ext = None
        file_path = self._create_file_path(key, ext)
        os.makedirs(file_path.parent, exist_ok=True)
        # Write blob data to the file
        with open(file_path, "wb") as f:
            f.write(data)
        # If metadata is provided, save it as a separate JSON file
        if metadata:
            self.put_metadata(key=key, metadata=metadata)

    @override
    def download_blob(self, key: str) -> bytes:
        """Downloads a blob from the local storage.

        Args:
            key: The key (filename) of the blob.
        Returns:
            The binary data of the blob.
        """
        file_path = self._create_file_path(key)
        try:
            with open(file_path, "rb") as f:
                return f.read()
        except FileNotFoundError:
            raise KeyNotExistsException

    @override
    def put_metadata(self, key: str, metadata: dict | BaseModel):
        """Saves metadata for a blob as a JSON file.

        Args:
            key: The key (filename) of the blob.
            metadata: The metadata to save (can be a Pydantic model or a dict).
        """
        file_path = self._create_file_path(key, ext="json")
        with open(file_path, "wt", encoding="utf8") as f:
            if isinstance(metadata, BaseModel):
                f.write(metadata.model_dump_json(indent=4))
            else:
                json.dump(metadata, f, indent=4, ensure_ascii=False)

    @override
    def get_metadata(self, key: str) -> T:
        """Retrieves metadata for a blob from its JSON file.

        Args:
            key: The key (filename) of the blob.
        Returns:
            The metadata as a Pydantic model instance.
        """
        file_path = self._create_file_path(key, ext="json")
        try:
            with open(file_path, "rt", encoding="utf8") as f:
                d = json.load(f)
            return self.clazz.model_validate(d)
        except FileNotFoundError:
            raise KeyNotExistsException

    @override
    def keys(self) -> Iterator[str]:
        """Iterates over the keys (filenames without extension) of blobs in the storage.

        Yields:
            Blob keys.
        """
        for root, _, files in os.walk(self.folder_path):
            ext = f".{self.default_ext}" if self.default_ext else ""
            len_ext = len(ext)
            for file in files:
                # Skip metadata files
                if not file.endswith(".json"):
                    key = file[:-len_ext] if file.endswith(ext) else file
                    # Construct the relative path to be used as a key
                    yield root[len(str(self.folder_path)) + 1 :] + "/" + key

    @override
    def delete(self, key: str):
        """Deletes a blob and its associated metadata file (if exists).

        Args:
            key: The key (filename) of the blob to delete.
        """
        file_path = self._create_file_path(key)
        try:
            os.remove(file_path)
        except FileNotFoundError:
            pass
        # Attempt to delete the metadata file as well
        metadata_file_path = file_path.with_suffix(".json")
        try:
            os.remove(metadata_file_path)
        except FileNotFoundError:
            pass

    def move_blob(self, source_key: str, dest_key: str):
        """Moves a blob and its metadata from a source key to a destination key.

        Args:
            source_key: The current key of the blob.
            dest_key: The new key for the blob.
        """
        source_path = self._create_file_path(source_key)
        dest_path = self._create_file_path(dest_key)
        os.makedirs(dest_path.parent, exist_ok=True)
        os.rename(source_path, dest_path)
        # Move metadata file if it exists
        if source_path.with_suffix(".json").exists():
            os.rename(source_path.with_suffix(".json"), dest_path.with_suffix(".json"))

    def list_blobs(self, dir: str = None) -> Iterator[FileNameMimeType]:
        """Lists blobs in a specified directory within the storage.

        Args:
            dir: The directory prefix to list blobs from (optional).

        Yields:
            FileNameMimeType objects for each blob found.
        """
        if dir:
            prefix = dir if dir[-1] == "/" else dir + "/"
        else:
            prefix = ""
        for root, _, files in os.walk(self.folder_path.joinpath(prefix)):
            for file in files:
                if file.endswith(".json"):
                    # Skip metadata files
                    continue
                path = os.path.join(root, file)
                if path.startswith(str(self.folder_path.joinpath(prefix))):
                    # Yield blob information including name and guessed mime type
                    yield FileNameMimeType(
                        name=file,
                        mime_type=get_content_type(file),
                    )

    @override
    def delete_folder(self, folder_name: str):
        """Deletes a folder and all its contents within the blob storage.

        Args:
            folder_name: The name of the folder to delete.
        """
        shutil.rmtree(self.folder_path.joinpath(folder_name))
