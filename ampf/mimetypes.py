import os
from typing import Optional

extension_map = {
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
    ".svg": "image/svg+xml",
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".json": "application/json",
    ".xml": "application/xml",
    ".csv": "text/csv",
    ".js": "text/javascript",
    ".css": "text/css",
    ".ico": "image/x-icon",
    ".html": "text/html",
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".mp4": "video/mp4",
    ".avi": "video/x-msvideo",
    ".mov": "video/quicktime",
    ".wmv": "video/x-ms-wmv",
    ".flv": "video/x-flv",
    ".webm": "video/webm",
    ".md": "text/markdown",

    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "ppt": "application/vnd.ms-powerpoint",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    
    "zip": "application/zip",
    "rar": "application/x-rar-compressed",
    "tar": "application/x-tar",
    "gz": "application/gzip",
    "bz2": "application/x-bzip2",
    "7z": "application/x-7z-compressed",
}

# Pre-compute the reverse map (content_type -> extension).
# This stores the *first* extension encountered in `extension_map` for a given content type.
# For example, for "image/jpeg", ".jpeg" will be stored because it appears before ".jpg"
# in the `extension_map` definition.
_content_type_to_extension_map: dict[str, str] = {}
for _ext, _c_type in extension_map.items():
    if _c_type not in _content_type_to_extension_map:
        _content_type_to_extension_map[_c_type] = _ext


def get_content_type(filename: str) -> Optional[str]:
    """
    Determines the MIME content type of a file based on its extension.

    Args:
        filename: The name of the file (e.g., "image.jpg", "document.pdf").

    Returns:
        The MIME content type as a string (e.g., "image/jpeg"),
        or None if the extension is not recognized or filename is invalid/empty.
    """
    if not filename or not isinstance(filename, str):
        return None
    # os.path.splitext correctly handles various filename formats,
    # e.g., "archive.tar.gz" -> (".gz"), ".bashrc" -> (".bashrc"), "no_ext" -> ("")
    _root, ext = os.path.splitext(filename)
    return extension_map.get(ext.lower())


def get_extension(content_type: str) -> Optional[str]:
    """
    Determines a common file extension for a given MIME content type.

    It returns the first extension found in the predefined map for that content type.
    For example, for "image/jpeg", it will return ".jpeg".

    Args:
        content_type: The MIME content type (e.g., "image/jpeg").

    Returns:
        The file extension as a string (e.g., ".jpeg"),
        or None if the content type is not recognized or is invalid/empty.
    """
    if not content_type or not isinstance(content_type, str):
        return None
    # Normalize lookup to lowercase as content types can have varied casing.
    return _content_type_to_extension_map.get(content_type.lower())
