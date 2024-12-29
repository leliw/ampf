from typing import Type


class KeyException(Exception):
    def __init__(
        self, collection_name: str = None, clazz: Type = None, key: str = None
    ):
        self.collection_name = collection_name
        self.clazz = clazz
        self.key = key


class KeyNotExistsException(KeyException):
    def __init__(
        self, collection_name: str = None, clazz: Type = None, key: str = None
    ):
        super().__init__(collection_name, clazz, key)


class KeyExistsException(KeyException):
    def __init__(
        self, collection_name: str = None, clazz: Type = None, key: str = None
    ):
        super().__init__(collection_name, clazz, key)
