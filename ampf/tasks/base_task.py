from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Self
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, computed_field


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class BaseTask(BaseModel, ABC):
    """Base class for all tasks run in background."""

    id: UUID = Field(default_factory=uuid4)
    type: str | StrEnum = "task"
    name: str | None = None
    status: TaskStatus = TaskStatus.PENDING
    error_message: str | None = None

    @computed_field
    @property
    def progress(self) -> int | None:
        return None

    @computed_field
    @property
    @abstractmethod
    def result_id(self) -> str | None:
        pass


class TaskHeader(BaseModel):
    """Default class returning basic information about task."""

    id: UUID
    type: str | StrEnum
    status: TaskStatus
    error_message: str | None
    name: str | None
    progress: int | None
    result_id: str | None

    @classmethod
    def from_task(cls, task: BaseTask) -> Self:
        return cls(
            id=task.id,
            type=task.type,
            status=task.status,
            error_message=task.error_message,
            name=task.name,
            progress=task.progress,
            result_id=task.result_id,
        )
