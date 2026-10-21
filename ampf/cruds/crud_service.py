from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, TypeAdapter

from ampf.base.base_async_collection_storage import BaseAsyncCollectionStorage


class CRUDService[R: BaseModel, H: BaseModel, C: BaseModel, U: BaseModel]:
    def __init__(
        self,
        storage: BaseAsyncCollectionStorage[R],
        record_class: type[R] | TypeAdapter[R],
        header_class: type[H],
        create_class: type[C] | None = None,
        update_class: type[U] | None = None,
    ) -> None:
        self.storage = storage
        self.record_class = record_class
        self.record_adapter: TypeAdapter[R] = (
            record_class if isinstance(record_class, TypeAdapter) else TypeAdapter(record_class)
        )
        self.header_class = header_class
        self.create_class = create_class
        self.update_class = update_class

    def record_to_header(self, record: R) -> H:
        return self.header_class.model_validate(record.model_dump(), extra="ignore")

    def create_to_record(self, value_create: C) -> R:
        return self.record_adapter.validate_python(value_create.model_dump(), extra="forbid")

    async def get_rows(self) -> AsyncGenerator[H]:
        async for crud_record in self.storage.get_all():
            yield self.record_to_header(crud_record)

    async def create(self, value_create: C | R) -> R:
        if self.create_class is not None and isinstance(value_create, self.create_class):
            value = self.create_to_record(value_create)
        else:
            value = self.record_adapter.validate_python(value_create)
        await self.storage.create(value)
        return value

    async def update(self, record_id: UUID, value_update: U) -> R:
        dict_patch = value_update.model_dump(exclude_unset=True)
        dict_patch["updated_at"] = datetime.now(UTC)
        return await self.storage.patch(record_id, dict_patch)

    async def get(self, record_id: UUID) -> R:
        return await self.storage.get(record_id)

    async def delete(self, record_id: UUID) -> None:
        await self.storage.delete(record_id)
