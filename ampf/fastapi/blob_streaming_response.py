from typing import Dict, Optional

from fastapi.responses import StreamingResponse

from ampf.base.blob_model import Blob


class BlobStreamingResponse(StreamingResponse):
    def __init__(self, blob: Blob, cache_control: Optional[str] = None, headers: Optional[Dict[str, str]] = None):
        """Streams Blob to client.
        
        Args:
            blob: The blob to stream.
            cache_control: The cache control header.
            headers: The headers to add.
        """
        if cache_control:
            headers = headers or {}
            headers["Cache-Control"] = cache_control
        super().__init__(blob.stream(), media_type=blob.metadata.content_type, headers=headers)
