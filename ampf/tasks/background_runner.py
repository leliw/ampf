from typing import override

from fastapi import BackgroundTasks
from pydantic import BaseModel

from .task_model import TaskRunner
from .task_registry import TaskRegistry


class BackgroundRunner(TaskRunner):
    def __init__(self, background_tasks: BackgroundTasks):
        self.background_tasks = background_tasks

    @override
    def run(self, name: str, payload: BaseModel):
        processor = TaskRegistry._tasks[name].processor
        parameters = TaskRegistry.get_task_parameters(name, payload)
        self.background_tasks.add_task(processor, **parameters)  # type: ignore

    @override
    async def run_async(self, name: str, payload: BaseModel):
        processor = TaskRegistry._tasks[name].processor
        parameters = TaskRegistry.get_task_parameters(name, payload)
        self.background_tasks.add_task(processor, **parameters)  # type: ignore

    @classmethod
    def create(cls, background_tasks: BackgroundTasks) -> "BackgroundRunner":
        return cls(background_tasks)
