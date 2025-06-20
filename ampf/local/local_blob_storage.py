import json
import logging
import os
import shutil
from typing import Iterator, Optional, Type, override

from pydantic import BaseModel

from ampf.base import BaseBlobStorage
from ampf.base.base_blob_storage import FileNameMimeType
from ampf.base.exceptions import KeyNotExistsException

from ..mimetypes import get_content_type, get_extension
from .file_storage import FileStorage, StrPath


class LocalBlobStorage[T: BaseModel](BaseBlobStorage[T], FileStorage):
    """Zapisuje na dysku dane binarne.

    Args:
        bucket_name: nazwa podkatalogu w który są składowane pliki
        default_ext: domyślne rozszerzenie pliku
        subfolder_characters: liczba początkowych znaków nazwy pliku, które tworzą opcjonalny podkatalog
    """

    def __init__(
        self,
        bucket_name: str,
        clazz: Optional[Type[T]] = None,
        content_type: Optional[str] = None,
        subfolder_characters: Optional[int] = None,
        root_path: Optional[StrPath] = None,
    ):
        BaseBlobStorage.__init__(
            self, collection_name=bucket_name, clazz=clazz, content_type=content_type
        )
        default_ext = get_extension(content_type) if content_type else None
        default_ext = default_ext[1:] if default_ext else None
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
        metadata: Optional[BaseModel] = None,
        content_type: Optional[str] = None,
    ) -> None:
        if content_type:
            ext = get_extension(content_type)
            ext = ext[1:] if ext else None
        else:
            ext = None
        file_path = self._create_file_path(key, ext)
        os.makedirs(file_path.parent, exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(data)
        if metadata:
            self.put_metadata(key=key, metadata=metadata)

    @override
    def download_blob(self, key: str) -> bytes:
        file_path = self._create_file_path(key)
        try:
            with open(file_path, "rb") as f:
                return f.read()
        except FileNotFoundError:
            raise KeyNotExistsException

    @override
    def put_metadata(self, key: str, metadata: dict | BaseModel):
        file_path = self._create_file_path(key, ext="json")
        with open(file_path, "wt", encoding="utf8") as f:
            if isinstance(metadata, BaseModel):
                f.write(metadata.model_dump_json(indent=4))
            else:
                json.dump(metadata, f, indent=4, ensure_ascii=False)

    @override
    def get_metadata(self, key: str) -> T:
        if not self.clazz:
            raise ValueError("clazz must be set")
        file_path = self._create_file_path(key, ext="json")
        try:
            with open(file_path, "rt", encoding="utf8") as f:
                d = json.load(f)
            return self.clazz.model_validate(d)
        except FileNotFoundError:
            raise KeyNotExistsException

    @override
    def keys(self) -> Iterator[str]:
        for root, _, files in os.walk(self.folder_path):
            ext = f".{self.default_ext}" if self.default_ext else ""
            len_ext = len(ext)
            for file in files:
                if not file.endswith(".json"):
                    key = file[:-len_ext] if file.endswith(ext) else file
                    yield root[len(str(self.folder_path)) + 1 :] + "/" + key

    @override
    def delete(self, key: str):
        file_path = self._create_file_path(key)
        try:
            os.remove(file_path)
        except FileNotFoundError:
            pass

    def move_blob(self, source_key: str, dest_key: str):
        source_path = self._create_file_path(source_key)
        dest_path = self._create_file_path(dest_key)
        os.makedirs(dest_path.parent, exist_ok=True)
        os.rename(source_path, dest_path)
        if source_path.with_suffix(".json").exists():
            os.rename(source_path.with_suffix(".json"), dest_path.with_suffix(".json"))

    def list_blobs(self, dir: Optional[str] = None) -> Iterator[FileNameMimeType]:
        if dir:
            prefix = dir if dir[-1] == "/" else dir + "/"
        else:
            prefix = ""
        for root, _, files in os.walk(self.folder_path.joinpath(prefix)):
            for file in files:
                if file.endswith(".json"):
                    continue
                path = os.path.join(root, file)
                if path.startswith(str(self.folder_path.joinpath(prefix))):
                    yield FileNameMimeType(
                        name=file,
                        mime_type=get_content_type(file),
                    )

    @override
    def delete_folder(self, folder_name: str):
        shutil.rmtree(self.folder_path.joinpath(folder_name))
