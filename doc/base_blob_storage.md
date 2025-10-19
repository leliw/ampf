# BaseBlobStorage

Base class for storage implementations which store binary objects (blobs).
Each object is stored in collection and is recogized by its name (key, path).
If a key contains `/`, it is treated as path and all sub-paths are
treated as sub-collections.

Type parameter:

* T - Pydantic class containing metadata of the blob

## Constructor

* `collection_name: str` - The name of the collection (root folder)
* `clazz: Optional[Type[T]] = None` - The class of the metadata
* `content_type: str = "text/plain"`- The content type of the blob

## Abstract methods

These methods has to be implemented by child class.

* put(self, key: `Any`, value: `T`) -> `None`: Store the value with the key
* get(self, key: `Any`) -> `T`: Get the value with the key
* keys(self) -> `Iterator[T]`: Get all the keys:
* `delete(self, name: str) -> None`: Deletes the blob
* `_upsert_transactional(self, name: str, create_func: Optional[Callable[[str], Awaitable[Blob[T]]]] = None, update_func: Optional[Callable[[Blob[T]], Awaitable[Blob[T]]]] = None -> None`: Updates or creates the blob transactionally

Async methods:

* `upload_async(self, blob: Blob[T]) -> None`: Uploads the blob asynchronously
* `download_async(self, key: Any) -> Blob[T]`: Downloads the blob asynchronously

## Implemented methods

These methods are implemented in this class.

* create(self, value: `T`) -> `None`: Adds to collection a new element but only if such key doesn't already exists
* save(self, value: `T`) -> `None`: Save the value in the storage. The key is calculated based on the value. If the key already exists, it will be overwritten.
* get_key(self, value: `T`) -> `str`: Get the key for the value
* drop(self) -> `None`: Delete all the values
* get_all(self, sort: `Any` = None) -> `Iterator[T]`: Get all the values
* key_exists(self, needle: `Any`) -> `bool`: Check if the key exists
* is_empty(self) -> `bool`: Is storage empty?
* create_collection(self, key: str, collection_name: str, clazz: Type[T]) -> BaseStorage[T]: Creates a new storage object for subcollection (see below)

## Transactional methods

These methods are implemented in this class but relies on the child class implementation of `_upsert_transactional`. They provide transactional create/update functionality for blobs.

* `create_transactional(self, name: str, create_func: Callable[[str], Awaitable[Blob[T]]]) -> None`: Creates a new blob transactionally. If the blob with the given name already exists, an error is raised.
* `update_transactional(self, name: str, update_func: Callable[[Blob[T]], Awaitable[Blob[T]]]) -> None`: Updates an existing blob transactionally. If the blob with the given name does not exist, an error is raised.
* `upsert_transactional(self, name: str, create_func: Optional[Callable[[str], Awaitable[Blob[T]]]] = None, update_func: Optional[Callable[[Blob[T]], Awaitable[Blob[T]]]] = None) -> None`: Creates or updates a blob transactionally. If the blob with the given name exists, it is updated using `update_func`; otherwise, it is created using `create_func`.

Both `create_transactional` and `update_transactional` methods internally call `_upsert_transactional`, passing the appropriate functions to handle creation or updating of blobs in a transactional manner. If during the transaction a conflict is detected (e.g., another process has created or modified the blob), the proper function will be retried until the operation succeeds without conflict.

```python
async def create_func(name: str) -> Blob[MyMetadata]:
    return Blob(name=name, data=b"new_data")

async def update_func(b: Blob[MyMetadata]) -> Blob[MyMetadata]:
    return Blob(name=b.name, data=b.data.read() + b"_updated")

await storage.upsert_transactional("new_blob", create_func, update_func)
```
