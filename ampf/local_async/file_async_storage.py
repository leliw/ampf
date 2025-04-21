from pathlib import Path

import aiofiles

from ampf.local import FileStorage

type StrPath = str | Path


class FileAsyncStorage(FileStorage):
    async def _async_write_to_file(self, full_path: str, data: str) -> None:
        async with aiofiles.open(full_path, "w", encoding="utf-8") as file:
            await file.write(data)

    async def _async_read_from_file(self, full_path: str) -> str:
        async with aiofiles.open(full_path, "r", encoding="utf-8") as file:
            return await file.read()
