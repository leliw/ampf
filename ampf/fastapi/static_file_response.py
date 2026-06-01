"""This module provides a function to return static files or index.html from a base directory."""

import os
from pathlib import Path
from warnings import deprecated

from anyio import Path as AsyncPath
from fastapi import HTTPException, Response
from fastapi.responses import FileResponse

from ..mimetypes import get_content_type


@deprecated("Use function get_static_file_response instead")
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
            media_type=get_content_type(str(file_path)),
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


async def get_static_file_response(base_dir: str, uri_path: str) -> FileResponse:
    base_path = await AsyncPath(base_dir).resolve()
    requested_path = await (base_path / uri_path.lstrip("/")).resolve()
    if not str(requested_path).startswith(str(base_path)):
        raise HTTPException(status_code=403, detail="Forbidden")
    if await requested_path.is_dir():
        target_path = requested_path / "index.html"
    else:
        target_path = requested_path
    if not await target_path.exists():
        target_path = base_path / "index.html"
    if not await target_path.exists():
        raise HTTPException(status_code=404, detail="Page not found")
    return FileResponse(path=str(target_path))
