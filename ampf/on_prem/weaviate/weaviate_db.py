import logging
from typing import List, Optional, Self

import weaviate
from weaviate.classes.config import Property
from weaviate.collections.classes.config_vector_index import _VectorIndexConfigCreate


class WeaviateDB:
    _log = logging.getLogger(__name__)

    def __init__(self, host: str = "localhost", port: int = 8082, grpc_port: int = 50051):
        self.host = host
        self.port = int(port)
        self.grpc_port = grpc_port
        self.db : Optional[weaviate.WeaviateClient] = None

    def connect(self) -> Self:
        self.db = weaviate.connect_to_local(host=self.host, port=self.port, grpc_port=self.grpc_port)
        self._log.info("Connected to %s:%d.", self.host, self.port)
        return self

    def is_connected(self) -> bool:
        return self.db is not None

    def close(self) -> None:
        if self.db:
            self.db.close()
            self._log.info("Connection closed.")

    def __enter__(self) -> Self:
        return self.connect()

    def __exit__(self, type, value, traceback):
        self.close()

    def get_collection(self, name, properties: List[Property], vector_index_config: _VectorIndexConfigCreate):
        if not self.db:
            raise Exception("Not connected to database.")
        collection = self.db.collections.get(name)
        if not collection.exists():
            collection = self.db.collections.create(
                name, properties=properties, vector_index_config=vector_index_config
            )
        return collection
