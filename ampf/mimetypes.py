extension_map = {
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
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
