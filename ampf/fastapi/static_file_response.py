"""This module provides a function to return static files or index.html from a base directory."""

import os
from pathlib import Path

from fastapi import HTTPException, Response


class StaticFileResponse(Response):
    def __init__(self, base_dir: str, uri_path: str):
        file_path = Path(base_dir) / uri_path
        if file_path.is_dir():
            file_path = file_path / "index.html"
        if not file_path.exists():
            file_path = Path(base_dir) / "index.html"
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Page not found")
        super().__init__(
            content=self.get_file_content(file_path),
            status_code=200,
            media_type=self.get_content_type(file_path),
        )

    def get_file_content(self, file_path: Path):
        """Return the file content"""
        file_extension = os.path.splitext(file_path)[1]
        if file_extension in [
            ".js",
            ".css",
            ".html",
            ".json",
            ".yaml",
            ".yml",
            ".xml",
            ".csv",
            ".txt",
        ]:
            return file_path.read_text()
        else:
            return file_path.read_bytes()

    def get_content_type(self, file_path: Path) -> str:
        file_extension = os.path.splitext(file_path)[1]
        match file_extension:
            case ".js":
                media_type = "text/javascript"
            case ".css":
                media_type = "text/css"
            case ".ico":
                media_type = "image/x-icon"
            case ".png":
                media_type = "image/png"
            case ".jpg":
                media_type = "image/jpeg"
            case ".jpeg":
                media_type = "image/jpeg"
            case ".svg":
                media_type = "image/svg+xml"
            case _:
                media_type = "text/html"
        return media_type
