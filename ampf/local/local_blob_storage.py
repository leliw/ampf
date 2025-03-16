import json
import logging
import os
import shutil
from typing import Iterator
from pydantic import BaseModel

from ampf.base import BaseBlobStorage
from ampf.base.base_blob_storage import FileNameMimeType
from ampf.base.exceptions import KeyNotExistsException

from .file_storage import FileStorage
from ..mimetypes import get_content_type, get_extension


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
        clazz: BaseModel = None,
        content_type: str = None,
        subfolder_characters: int = None,
    ):
        default_ext = get_extension(content_type)[1:] if content_type else None
        FileStorage.__init__(
            self,
            folder_name=bucket_name,
            subfolder_characters=subfolder_characters,
            default_ext=default_ext,
        )
        self.clazz = clazz
        self._log = logging.getLogger(__name__)

    def upload_blob(
        self,
        file_name: str,
        data: bytes,
        metadata: BaseModel = None,
        content_type: str = None,
    ) -> None:
        if content_type:
            ext = get_extension(content_type)
            ext = ext[1:] if ext else None
        else:
            ext = None
        file_path = self._create_file_path(file_name, ext)
        os.makedirs(file_path.parent, exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(data)
        if metadata:
            self.put_metadata(file_name=file_name, metadata=metadata)

    def download_blob(self, file_name: str) -> bytes:
        file_path = self._create_file_path(file_name)
        try:
            with open(file_path, "rb") as f:
                return f.read()
        except FileNotFoundError:
            raise KeyNotExistsException

    def put_metadata(self, file_name: str, metadata: dict | BaseModel):
        file_path = self._create_file_path(file_name, ext="json")
        with open(file_path, "wt", encoding="utf8") as f:
            if isinstance(metadata, BaseModel):
                f.write(metadata.model_dump_json(indent=4))
            else:
                json.dump(metadata, f, indent=4, ensure_ascii=False)

    def get_metadata(self, file_name: str) -> T:
        file_path = self._create_file_path(file_name, ext="json")
        try:
            with open(file_path, "rt", encoding="utf8") as f:
                d = json.load(f)
            return self.clazz.model_validate(d)
        except FileNotFoundError:
            raise KeyNotExistsException

    def keys(self) -> Iterator[str]:
        for root, _, files in os.walk(self.folder_path):
            ext = f".{self.default_ext}" if self.default_ext else ""
            len_ext = len(ext)
            for file in files:
                if not file.endswith(".json"):
                    key = file[:-len_ext] if file.endswith(ext) else file
                    yield root[len(str(self.folder_path)) + 1 :] + "/" + key

    def delete(self, file_name: str):
        file_path = self._create_file_path(file_name)
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

    def list_blobs(self, dir: str = None) -> Iterator[str]:
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

    def delete_folder(self, folder_name: str):
        shutil.rmtree(self.folder_path.joinpath(folder_name))
