# StaticFileResponse

`StaticFileResponse` is a FastAPI response class that serves static files from a specified directory. If the requested file is not found, it serves an `index.html` file, making it suitable for single-page applications (SPAs) like those built with Angular.

## Features

- Serves static files from a given directory.
- Falls back to `index.html` if the requested file is not found.
- Compatible with FastAPI and Starlette.

## Usage

```python
from fastapi import FastAPI
from ampf.fastapi import StaticFileResponse

app = FastAPI()

# Angular static files - it have to be at the end of file
@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    if not full_path.startswith("api/"):
        return StaticFileResponse("static/browser", full_path)
    else:
        raise HTTPException(status_code=404, detail="Not found")
```
