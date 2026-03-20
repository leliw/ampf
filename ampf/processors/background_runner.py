from fastapi import BackgroundTasks

from .task_model import TaskRegistry, TaskRunner


class BackgroundRunner(TaskRunner):
    def __init__(self, background_tasks: BackgroundTasks):
        self.background_tasks = background_tasks

    def run(self, name: str, *args, **kwargs):
        processor = TaskRegistry._tasks[name]
        self.background_tasks.add_task(processor, *args, **kwargs)  # type: ignore

    async def run_async(self, name: str, *args, **kwargs):
        processor = TaskRegistry._tasks[name]
        self.background_tasks.add_task(processor, *args, **kwargs)  # type: ignore

    @classmethod
    def create(cls, background_tasks: BackgroundTasks) -> "BackgroundRunner":
        return cls(background_tasks)
