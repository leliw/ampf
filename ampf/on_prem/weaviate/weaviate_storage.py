import json
import logging
import uuid
from typing import Any, Callable, Iterable, Iterator, List, Literal, Optional, Type

from pydantic import BaseModel

from ampf.base import BaseStorage, KeyNotExistsException
from weaviate.classes.config import Configure, DataType, Property, VectorDistances
from weaviate.classes.query import MetadataQuery, Filter

from ampf.base.base_query import BaseQuery

from .weaviate_db import WeaviateDB


class WeaviateStorage[T: BaseModel](BaseStorage[T]):
    _log = logging.getLogger(__name__)

    def __init__(
        self,
        collection_name: str,
        clazz: Type[T],
        key_name: Optional[str] = None,
        key: Optional[Callable[[T], str]] = None,
        db: Optional[WeaviateDB] = None,
    ):
        BaseStorage.__init__(self, collection_name, clazz, key_name, key)
        # BaseQuery.__init__(self, self.get_all)
        self.db = db or WeaviateDB()
        self.collection = self.db.get_collection(
            self.collection_name,
            [
                Property(name="key", data_type=DataType.TEXT),
                Property(name="content", data_type=DataType.TEXT),
            ],
            Configure.VectorIndex.hnsw(distance_metric=VectorDistances.COSINE),
        )

    def _get_uuid(self, key: str) -> uuid.UUID:
        for i in self.collection.iterator():
            if i.properties["key"] == key:
                return i.uuid
        raise KeyNotExistsException(key)

    def put(self, key: str, value: T) -> None:
        p = value.model_dump()
        v = p.pop(self.embedding_field_name)
        try:
            uuid = self._get_uuid(key)
            self.collection.data.replace(
                uuid,
                properties={
                    "key": key,
                    "content": json.dumps(p),
                },
                vector=v,
            )
        except KeyNotExistsException:
            self.create(value)

    def create(self, value: T):
        p = value.model_dump()
        v = p.pop(self.embedding_field_name)
        self.collection.data.insert(
            properties={
                "key": p[self.key], # type: ignore
                "content": json.dumps(p),
            },
            vector=v,
        )

    def get(self, key: str) -> T:
        for i in self.collection.iterator():
            if i.properties["key"] == key:
                content = i.properties["content"]
                if isinstance(content, str):
                    return self.clazz.model_validate_json(content)
                else:
                    raise ValueError("Content is not a string")
        raise KeyNotExistsException(key)

    def keys(self) -> Iterable[str]:
        return [str(i.properties["key"]) for i in self.collection.iterator()]

    def delete(self, key: str) -> None:
        uuid = self._get_uuid(key)
        self.collection.data.delete_by_id(uuid)

    def is_empty(self) -> bool:
        for i in self.collection.iterator():
            return False
        return True

    def drop(self):
        self.collection.data.delete_many(where=Filter.by_property("key").like("*"))

    def find_nearest(self, embedding: List[float], limit: Optional[int] = None) -> Iterator[T]:
        response = self.collection.query.near_vector(
            near_vector=embedding, limit=limit, return_metadata=MetadataQuery(distance=True)
        )
        for o in response.objects:
            print(o.properties)
            print(o.metadata.distance)
            yield self.clazz.model_validate(o.properties)

    def where(self, field: str, op: Literal["==", "!=", "<", "<=", ">", ">="], value: Any) -> BaseQuery[T]:
        return super().where(field, op, value)