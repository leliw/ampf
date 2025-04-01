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
* key_name(`str`): Mame of key field in stored object, default is first field
* key(`Callable[[T], str]`): Function to get key from object, default is None

## Abstract methods

These methods has to be implemented by child class.

* put(self, key: `str`, value: `T`) -> `None`: Store the value with the key
* get(self, key: `str`) -> `T`: Get the value with the key
* keys(self) -> `Iterator[T]`: Get all the keys:
* delete(self, key: `str`) -> `None`: Delete the value with the key

## Implemented methods

These methods are implemented in this class.

* create(self, value: `T`) -> `None`: Adds to collection a new element but only if such key doesn't already exists
* save(self, value: `T`) -> `None`: Save the value in the storage. The key is calculated based on the value. If the key already exists, it will be overwritten.
* get_key(self, value: `T`) -> `str`: Get the key for the value
* drop(self) -> `None`: Delete all the values
* get_all(self, sort: `Any` = None) -> `Iterator[T]`: Get all the values
* key_exists(self, needle: `str`) -> `bool`: Check if the key exists
* is_empty(self) -> `bool`: Is storage empty?
