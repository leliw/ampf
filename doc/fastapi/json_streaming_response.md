# JsonStreamingResponse

`JsonStreamingResponse` is a FastAPI response class that streams Pydantic objects to the client as JSON. It is useful for sending large datasets or continuous streams of data without loading everything into memory at once.

## Features

- Streams Pydantic models as JSON.
- Supports asynchronous iteration over data sources.
- Efficient memory usage for large datasets.
- Compatible with FastAPI and Starlette.

## Usage

```pythonpython
from fastapi import FastAPI
from ampf.fastapi import JsonStreamingResponse
from pydantic import BaseModel
from typing import AsyncGenerator

app = FastAPI()

class Item(BaseModel):
    id: int
    name: str

async def get_items() -> AsyncGenerator[Item, None]:
    for i in range(1, 101):
        yield Item(id=i, name=f"Item {i}")

@app.get("/items")
async def read_items():
    return JsonStreamingResponse(get_items())
```
