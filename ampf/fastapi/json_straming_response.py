from typing import AsyncIterator, Iterator, List, Mapping, Optional

from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from starlette.background import BackgroundTask


class StreamedException(BaseModel):
    """Data streamed to client when any exception occured"""

    error: str
    args: Optional[List[str]] = None

    @classmethod
    def from_exception(cls, e: Exception):
        args = []
        for a in e.args:
            if isinstance(a, str):
                args.append(a)
            else:
                args.append(str(a))
        return StreamedException(error=type(e).__name__, args=args)


class JsonStreamingResponse[T: BaseModel](StreamingResponse):
    """Streams Pydantic objects to client as JSON.

    Stream contain array of JSON objects. Each object and  "[","]" 
    are in one line. Each object starts with "," (except first line).
    """

    def __init__(
        self,
        content: Iterator[T] | AsyncIterator[T],
        status_code: int = 200,
        headers: Mapping[str, str] = None,
        media_type: str = "application/json",
        background: BackgroundTask = None,
    ):
        super().__init__(
            self.objects_to_text(content), status_code, headers, media_type, background
        )
        self.media_type = media_type


    async def objects_to_text(
        self, responses: Iterator[T] | AsyncIterator[T]
    ) -> Iterator[str] | AsyncIterator[str]:
        """Converts object iterator to JSON string iterator of these objects."""
        yield "[\n"
        try:
            i = 0
            if isinstance(responses, AsyncIterator):
                async for r in responses:
                    yield self.object_to_text(i, r)
                    i += 1
            else:
                for r in responses:
                    yield self.object_to_text(i, r)
                    i += 1
        except Exception as e:
            yield self.object_to_text(i, StreamedException.from_exception(e))
        yield "]\n"

    def object_to_text(self, i: int, o: T) -> str:
        """Converts object to JSON string."""
        return f"{',' if i > 0 else ''}{o.model_dump_json()}\n"
