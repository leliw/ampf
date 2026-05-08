from typing import override

from pydantic import BaseModel

from .task_model import TaskRunner
from .task_registry import TaskRegistry


class DirectRunner(TaskRunner):
    @override
    def run(self, name: str, payload: BaseModel):
        TaskRegistry.run_task(name, payload)

    @override
    async def run_async(self, name: str, payload: BaseModel):
        await TaskRegistry.run_task_async(name, payload)

    @classmethod
    def create(cls) -> "DirectRunner":
        return cls()
