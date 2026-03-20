import asyncio

from .task_model import TaskRegistry, TaskRunner


class DirectRunner(TaskRunner):
    def run(self, name: str, *args, **kwargs):
        processor = TaskRegistry._tasks[name]
        if callable(processor):
            ret = processor(*args, **kwargs)
            if asyncio.iscoroutine(ret):
                raise TypeError(f"Processor '{name}' is an asynchronous task. Use 'run_async' for asynchronous execution.")
        else:
            raise ValueError(f"Processor {name} is not callable")

    async def run_async(self, name: str, *args, **kwargs):
        processor = TaskRegistry._tasks[name]
        if callable(processor):
            ret = processor(*args, **kwargs)
            if asyncio.iscoroutine(ret):
                await ret
        else:
            raise ValueError(f"Processor {name} is not callable")

    @classmethod
    def create(cls) -> "DirectRunner":
        return cls()
