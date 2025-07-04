import json
import logging
import uuid
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Type

from pydantic import BaseModel

from ampf.base import BaseCollectionStorage, KeyNotExistsException
from weaviate.collections.classes.filters import _Filters
from weaviate.classes.config import Configure, DataType, Property, VectorDistances
from weaviate.classes.query import Filter, MetadataQuery

from .weaviate_db import WeaviateDB


class WeaviateStorage[T: BaseModel](BaseCollectionStorage[T]):
    _log = logging.getLogger(__name__)

    def __init__(
        self,
        collection_name: str,
        clazz: Type[T],
        key_name: Optional[str] = None,
        key: Optional[Callable[[T], str]] = None,
        db: Optional[WeaviateDB] = None,
        indexed_fields: Optional[List[str]] = None,
    ):
        BaseCollectionStorage.__init__(self, collection_name, clazz, key_name, key)
        # BaseQuery.__init__(self, self.get_all)
        self.db = db or WeaviateDB()
        self.key_name = self.key_name or "key"
        self.indexed_fields = indexed_fields or []

        properties = [
            Property(name=self.key_name, data_type=DataType.TEXT),
        ]
        for field in self.indexed_fields:
            properties.append(Property(name=field, data_type=DataType.TEXT))
        properties.append(Property(name="content", data_type=DataType.TEXT))

        self.collection = self.db.get_collection(
            self.collection_name,
            properties,
            Configure.VectorIndex.hnsw(distance_metric=VectorDistances.COSINE),
        )

    def _get_uuid(self, key: str) -> uuid.UUID:
        for i in self.collection.iterator():
            if i.properties[self.key_name] == key:
                return i.uuid
        raise KeyNotExistsException(key)

    def put(self, key: str, value: T) -> None:
        p = value.model_dump()
        v = p.pop(self.embedding_field_name)
        try:
            uuid = self._get_uuid(key)
            self.collection.data.replace(
                uuid,
                properties=self.create_properties(p),
                vector=v,
            )
        except KeyNotExistsException:
            self.create(value)

    def create(self, value):
        p = value.model_dump()
        v = p.pop(self.embedding_field_name)
        self.collection.data.insert(
            properties=self.create_properties(p),
            vector=v,
        )

    def create_properties(self, p: Dict[str, Any]) -> Dict[str, Any]:
        ret = {self.key_name: p[self.key_name]}
        for field in self.indexed_fields:
            ret[field] = p.pop(field)
        ret["content"] = json.dumps(p, default=str)
        return ret

    def get(self, key: str) -> T:
        for i in self.collection.iterator():
            if i.properties[self.key_name] == key:
                content = i.properties["content"]
                if isinstance(content, str):
                    ret = json.loads(content)
                    for field in self.indexed_fields:
                        ret[field] = i.properties[field]
                    if i.vector:
                        ret[self.embedding_field_name] = i.vector
                    try:
                        return self.clazz.model_validate(ret)
                    except Exception as e:
                        self._log.error("Error validating model: %s", e)
                        raise ValueError(f"Error validating model: {e}")
                else:
                    raise ValueError("Content is not a string")
        raise KeyNotExistsException(key)

    def keys(self) -> Iterable[str]:
        return [str(i.properties[self.key_name]) for i in self.collection.iterator()]

    def delete(self, key: str) -> None:
        uuid = self._get_uuid(key)
        self.collection.data.delete_by_id(uuid)

    def is_empty(self) -> bool:
        for i in self.collection.iterator():
            return False
        return True

    def drop(self):
        self.collection.data.delete_many(where=Filter.by_property(self.key_name).like("*"))

    def find_nearest(self, embedding: List[float], limit: Optional[int] = None, filters: Optional[_Filters] = None) -> Iterator[T]:
        response = self.collection.query.near_vector(
            near_vector=embedding, 
            filters=filters,
            limit=limit, 
            return_metadata=MetadataQuery(distance=True),
        )
        for i in response.objects:
            content = i.properties["content"]
            if isinstance(content, str):
                ret = json.loads(content)
                for field in self.indexed_fields:
                    ret[field] = i.properties[field]
                if i.vector:
                    self._log.warning(ret)
                    ret[self.embedding_field_name] = i.vector
                try:
                    self._log.warning(ret)
                    yield self.clazz.model_validate(ret)
                except Exception as e:
                    self._log.error("Error validating model: %s\n\n%s\n", e, ret)
                    raise ValueError(f"Error validating model: {e}")

            else:
                raise ValueError("Content is not a string")

    def delete_where(self, field: str, value: str):
        ret = self.collection.data.delete_many(where=Filter.by_property(field).equal(value), verbose=True)
        if len(ret.objects) > 0:
            self._log.info("Deleted %d items.", len(ret.objects))
