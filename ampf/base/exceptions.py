from typing import Optional, Type


class KeyException(Exception):
    def __init__(
        self, collection_name: Optional[str] = None, clazz: Optional[Type] = None, key: Optional[str] = None
    ):
        self.collection_name = collection_name
        self.clazz = clazz
        self.key = key

    def __str__(self) -> str:
        return f"{self.__class__.__name__}: collection_name={self.collection_name}, clazz={self.clazz}, key={self.key}"
        

class KeyNotExistsException(KeyException):
    def __init__(
        self, collection_name: Optional[str] = None, clazz: Optional[Type] = None, key: Optional[str] = None
    ):
        super().__init__(collection_name, clazz, key)


class KeyExistsException(KeyException):
    def __init__(
        self, collection_name: Optional[str] = None, clazz: Optional[Type] = None, key: Optional[str] = None
    ):
        super().__init__(collection_name, clazz, key)
