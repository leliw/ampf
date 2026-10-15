from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Self
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class CRUDRecord[H: BaseModel, C: BaseModel, P: BaseModel](BaseModel, ABC):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    @abstractmethod
    def create(cls, value_create: C) -> Self: ...
    @abstractmethod
    def to_header(self) -> H: ...
