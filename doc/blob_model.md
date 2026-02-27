# Blob Model

This module defines data models for handling binary large objects (blobs), including their location, metadata, creation, and content management. It provides classes for representing blobs, their associated metadata, and utilities for creating and streaming blob data.

## BlobLocation

`BlobLocation` is a Pydantic model representing the location of a blob, specified by its bucket and name.

```python
class BlobLocation(BaseModel):
    bucket: Optional[str] = None
    name: str
```

### Fields

* `bucket: Optional[str]` - The name of the storage bucket where the blob is located. Defaults to `None`.
* `name: str` - The unique name or key of the blob within its bucket.

## BaseBlobMetadata

`BaseBlobMetadata` is a Pydantic model for storing essential metadata about a blob, such as its content type and original filename.

```python
class BaseBlobMetadata(BaseModel):
    content_type: str = "application/octet-stream"
    filename: Optional[str] = None
```

### Fields

* `content_type: str` - The MIME type of the blob's content. Defaults to `"application/octet-stream"`.
* `filename: Optional[str]` - The original filename of the blob. Defaults to `None`.

### Class Methods

* `create(cls, file: UploadFile) -> Self`:
    Creates a `BaseBlobMetadata` instance from a `fastapi.UploadFile` object. It attempts to determine the content type from the `UploadFile` or by guessing from the filename.
* `from_filename(cls, filename: str) -> Self`:
    Creates a `BaseBlobMetadata` instance by guessing the content type based on the provided filename's extension.

## BlobCreate

`BlobCreate` is a generic class used to prepare data for creating a new `Blob` object. It can encapsulate blob data from various sources like files, `UploadFile` objects, or raw content (bytes/string).

```python
class BlobCreate[T: BaseBlobMetadata]:
    def __init__(
        self,
        name: Optional[str] = None,
        data: Optional[BlobData] = None,
        content: Optional[bytes | str] = None,
        metadata: T = BaseBlobMetadata(),
    ):
        # ...
```

### Constructor

* `name: Optional[str]` - An optional name for the blob. If not provided, a UUID will be generated when creating a `Blob`.
* `data: Optional[BlobData]` - A file-like object (`BinaryIO` or `SpooledTemporaryFile`) containing the blob's binary data.
* `content: Optional[bytes | str]` - The raw content of the blob as bytes or a string.
* `metadata: T` - An instance of `BaseBlobMetadata` (or a subclass) containing additional metadata. Defaults to `BaseBlobMetadata()`.

**Note**: You must provide either `data` or `content`, but not both.

### Class Methods

* `from_file(cls, path: Path, metadata: T = empty_blob_metadata) -> "BlobCreate[T]"`:
    Creates a `BlobCreate` instance from a local file specified by `path`. The file is opened in binary read mode. Metadata is automatically inferred from the filename if not provided.
* `from_upload_file(cls, file: UploadFile, metadata: T = empty_blob_metadata) -> "BlobCreate[T]"`:
    Creates a `BlobCreate` instance from a `fastapi.UploadFile` object. Metadata is automatically inferred from the `UploadFile` if not provided.
* `from_content(cls, content: bytes | str, content_type: str = "application/octet-stream") -> "BlobCreate[BaseBlobMetadata]"`:
    Creates a `BlobCreate` instance directly from raw `content` (bytes or string) and an optional `content_type`.

## BlobError

`BlobError` is a custom `ValueError` raised when invalid combinations of `data` and `content` are provided during `Blob` or `BlobCreate` initialization (e.g., both or neither are provided).

## Blob

`Blob` is a generic class representing a complete blob, encapsulating its name, data (as a file-like object or bytes), and metadata.

```python
class Blob[T: BaseBlobMetadata]:
    def __init__(
        self,
        name: str,
        data: Optional[BlobData] = None,
        content: Optional[bytes | str] = None,
        content_type: Optional[str] = None,
        metadata: T = empty_blob_metadata,
    ):
        # ...
```

### Constructor

* `name: str` - The unique name of the blob.
* `data: Optional[BlobData]` - A file-like object (`BinaryIO` or `SpooledTemporaryFile`) containing the blob's binary data.
* `content: Optional[bytes | str]` - The raw content of the blob as bytes or a string.
* `content_type: Optional[str]` - An optional content type. If provided, it will override or set the `content_type` in the `metadata`.
* `metadata: T` - An instance of `BaseBlobMetadata` (or a subclass) containing additional metadata. Defaults to `empty_blob_metadata`.

**Note**: Similar to `BlobCreate`, you must provide either `data` or `content`, but not both.

### Properties

* `content_type: str` (read-only):
    Returns the `content_type` from the blob's metadata.
* `content: bytes` (read/write):
### Usage Examples

#### Getting and Setting Blob Content

```python
from io import BytesIO
from ampf.base.blob_model import Blob

# Create a blob with initial content
blob = Blob(name="foo", data=BytesIO(b"bar"))

# Get the content
content = blob.content
assert content == b"bar"

# Set new content
blob.content = b"baz"
assert blob.content == b"baz"
```

Provides access to the blob's content as `bytes`. If the content is not yet loaded into memory (i.e., `_content` is `None` and `_data` is present), it will read the data from the file-like object, store it in `_content`, and then close the `_data` stream.
Setting this property will update the blob's content. If `_data` is present, a `BlobError` will be raised.

### Methods

* `data(self) -> Generator[BlobData]`:
    A context manager that provides access to the blob's data as a file-like object (`BlobData`). It ensures the data stream is seeked to the beginning before yielding and closed afterwards. If the blob was initialized with `content`, it creates a `BytesIO` object.

    ```python
    with blob.data() as f:
        # Read from f
        content_bytes = f.read()
    ```

* `stream(self, chunk_size=1024 * 1024) -> AsyncGenerator[bytes]`:
    An asynchronous generator that yields chunks of the blob's content. This is useful for efficiently streaming large files without loading the entire content into memory. If `_content` is already loaded, it yields chunks from memory; otherwise, it reads from the `_data` stream in chunks, delegating synchronous file reads to a separate thread using `asyncio.to_thread`.

    ```python
    async for chunk in blob.stream(chunk_size=8192):
        # Process chunk
        print(f"Received chunk of size: {len(chunk)}")
    ```

### Class Methods

* `create(cls, value_create: BlobCreate) -> "Blob"`:
    Creates a `Blob` instance from a `BlobCreate` object. If `value_create.name` is `None`, a UUID is generated for the blob's name.
* `from_file(cls, path: Path, metadata: T = empty_blob_metadata) -> "Blob[T]"`:
    Convenience method to create a `Blob` directly from a local file path. Internally uses `BlobCreate.from_file`.
* `from_upload_file(cls, file: UploadFile, metadata: T = empty_blob_metadata) -> "Blob[T]"`:
    Convenience method to create a `Blob` directly from a `fastapi.UploadFile`. Internally uses `BlobCreate.from_upload_file`.

### Usage Examples

#### Creating BlobCreate from Content

```python
from ampf.base.blob_model import BlobCreate

# Create from content without specifying content-type
blob_create = BlobCreate.from_content(b"bar")
assert blob_create.metadata.content_type == "application/octet-stream"

# Create from content with a specified content-type
blob_create = BlobCreate.from_content(b"bar", "text/plain")
assert blob_create.metadata.content_type == "text/plain"
```

#### Creating Blob from File

```python
from pathlib import Path
from ampf.base.blob_model import Blob

# Assuming a file 'tests/data/test.txt' exists with content "This is the test file."
# Create a blob directly from a file path
blob = Blob.from_file(Path("./tests/data/test.txt"))
assert blob.name == "test.txt"
assert blob.content == b"This is the test file."
assert blob.metadata.content_type == "text/plain"
```


## BlobHeader

`BlobHeader` is a generic Pydantic model representing a blob's header, containing only its name and metadata. It's useful for scenarios where only blob metadata is needed without the actual content.

```python
class BlobHeader[T: BaseBlobMetadata](BaseModel):
    name: str
    metadata: T
```

### Fields

* `name: str` - The name of the blob.
* `metadata: T` - An instance of `BaseBlobMetadata` (or a subclass) containing the blob's metadata.

### Class Methods

* `create(cls, blob: Blob[T])`:
    Creates a `BlobHeader` instance from an existing `Blob` object, extracting its name and metadata.
