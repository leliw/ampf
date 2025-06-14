import os
import shutil
from abc import ABC
from pathlib import Path
from typing import Optional

type StrPath = str | Path


class FileStorage(ABC):
    """Klasa bazowa dla magazynów operujących na plikach lokalnych.

    W celu poprawy wydajności operacji na plikach, mogą być tworzone dodatkowe podkatalogi.

    Atrybut klasy `_root_dir_path` określa katalog główny wszystkich danych zapisywanych na
    dysku przez klasy dziedziczące.

    Args:
        folder_name: katalog w którym są składowane pliki
        default_ext: domyślne rozszerzenie plików
        subfolder_characters: liczba początkowych znaków, które tworzą opcjonalny podkatalog
    """

    def __init__(
        self,
        folder_name: Optional[str] = None,
        default_ext: Optional[str] = None,
        subfolder_characters: Optional[int] = None,
        root_path: Optional[StrPath] = None,
    ):
        self._root_path = Path(root_path) if root_path else Path(os.path.abspath("./data"))
        if folder_name:
            self.folder_path = self._root_path.joinpath(folder_name)
        else:
            self.folder_path = self._root_path
        self.subfolder_characters = subfolder_characters
        self.default_ext = default_ext
        os.makedirs(self.folder_path, exist_ok=True)

    def _split_to_folders(self, file_name: str) -> list[str]:
        """Adds extra subfolder if subfolder_characters is set"""
        folders = file_name.split("/")
        if self.subfolder_characters:
            file_name = folders.pop()
            sub_folder = file_name[0 : self.subfolder_characters]
            return [*folders, sub_folder, file_name]
        else:
            return folders

    def _create_file_path(self, file_name: str, ext: Optional[str] = None) -> Path:
        ext = ext or self.default_ext
        file_ext = self._get_ext(file_name)
        if file_ext != ext:
            file_name = f"{file_name}.{ext}"
        path = self.folder_path.joinpath(*self._split_to_folders(file_name))
        os.makedirs(path.parent, exist_ok=True)
        return path

    def drop(self):
        shutil.rmtree(self.folder_path)

    def _write_to_file(self, full_path: Path, data: str) -> None:
        with open(full_path, "w", encoding="utf-8") as file:
            file.write(data)

    def _read_from_file(self, full_path: Path) -> str:
        with open(full_path, "r", encoding="utf-8") as file:
            return file.read()

    @classmethod
    def _get_ext(cls, file_name: str, default_ext: Optional[str] = None) -> str | None:
        return file_name.split(".")[-1] if "." in file_name else default_ext
