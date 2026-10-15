from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel

from ampf.base.base_async_collection_storage import BaseAsyncCollectionStorage

from .crud_model import CRUDRecord


class CRUDService[T: CRUDRecord, H: BaseModel, C: BaseModel, P: BaseModel]:
    def __init__(self, storage: BaseAsyncCollectionStorage[T], clazz: type[T]) -> None:
        self.storage = storage
        self.clazz = clazz

    async def get_rows(self) -> AsyncGenerator[H]:
        async for crud_record in self.storage.get_all():
            yield crud_record.to_header()

    async def create(self, value_create: C | T) -> T:
        if isinstance(value_create, self.clazz):
            value = value_create
        else:
            value = self.clazz.create(value_create)
        await self.storage.create(value)
        return value

    async def update(self, record_id: UUID, value_patch: P) -> T:
        dict_patch = value_patch.model_dump(exclude_unset=True)
        dict_patch["updated_at"] = datetime.now(UTC)
        return await self.storage.patch(record_id, dict_patch)

    async def get(self, record_id: UUID) -> T:
        return await self.storage.get(record_id)

    async def delete(self, record_id: UUID) -> None:
        await self.storage.delete(record_id)
