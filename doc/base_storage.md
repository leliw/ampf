# BaseStorage

Base class for storage implementations which store Pydantic objects.
Each object is stored in collection and is recogized by its key.
If a key contains `/`, it is treated as path and all sub-paths are
treated as sub-collections.

Type parameter:

* T - Pydantic class stored in storage

## Constructor

* collection_name(`str`): Name of collection in storage
* clazz(`Type[T]`): Class of objects stored in storage,
* key(`str | Callable[[T], str]`): Name of key field or function to get key from object, default is the first field
* embedding_field_name(`str`) = "embedding": Name of field in object which contains embedding vector
* embedding_search_limit(`int`) = 5: Limit of objects to be returned by embedding search

## Abstract methods

These methods has to be implemented by child class.

* put(self, key: `Any`, value: `T`) -> `None`: Store the value with the key
* get(self, key: `Any`) -> `T`: Get the value with the key
* keys(self) -> `Iterator[T]`: Get all the keys:
* delete(self, key: `Any`) -> `None`: Delete the value with the key

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

## Collections hierarchy - subcollections

### Deprecated

Collections and their storages can be organized in a hierarchy (like files hierarchy).
Subcollections can be created by using `/` character in a key or by using `create_collection()` method.

### New solution

Collections are defined with `CollectionDef` class.
The attribute `collections` defines subcollections of the
parent collection. Then root collection is created by `factory.create_collection()` method
and subcollections are obtained by `storage.get_collection()` method. There are two parameters:

* key of the parent collection
* name (or class) of the subcollection

Example:

```python
storage_def = CollectionDef("sites", Sitemap, "site", subcollections=[
    CollectionDef("raw_markdown", SitePage),
    CollectionDef("clean_markdown", SitePage),
    CollectionDef("chunks", Chunk),
])
storage = factory.create_collection(storage_def)

... 

storage_raw_markdown = storage.get_collection(sitemap.site, "raw_markdown")
```

## Embedding search - find_nearest

This method is used to find the nearest object in the storage. There is
a simple, not optimal implementation of this method in the base class. It is
used if the storage doesn't implement this method. The method uses
`scipy.spatial.distance.cdist` to calculate the distance between the
embeddings of the objects in the storage and the embedding of the object
passed as a parameter. The method returns the list of the nearest objects
sorted by distance. The number of objects returned is limited by the
`embedding_search_limit` parameter.
