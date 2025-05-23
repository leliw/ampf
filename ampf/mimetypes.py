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
}

content_type_map = {}


def get_content_type(filename: str):
    ext = "." + filename.split(".")[-1].lower()
    return extension_map.get(ext)


def get_extension(content_type):
    global content_type_map
    if not content_type_map:
        content_type_map = {}
        for k, v in extension_map.items():
            if k not in content_type_map.keys():
                content_type_map[v] = k
    return content_type_map.get(content_type)
