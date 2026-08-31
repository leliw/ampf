from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Literal, Protocol, override

from fastapi import BackgroundTasks

from ampf.base.base_async_factory import BaseAsyncFactory
from ampf.dependency.dependency_container import DependencyContainer
from ampf.dependency.dependency_registry import DependencyRegistry
from ampf.fastapi.base_app_state import BaseAppState, LifecycleManager
from ampf.tasks.pubsub_runner import PubsubRunner
from ampf.tasks.task_model import ManagedTaskRunner, TaskRunner


class TasksAppConfig(Protocol):
    task_runner: Literal["Direct", "Background", "PubsubPull", "PubsubPush"]


@dataclass
class TasksAppState[T: TasksAppConfig](BaseAppState):
    config: T
    factory: BaseAsyncFactory
    task_runner: TaskRunner | type[TaskRunner] | None = None

    @override
    def get_lifecycle_managers(self) -> list[LifecycleManager]:
        if not self.task_runner:
            match self.config.task_runner:
                case "Direct":
                    from ampf.tasks.direct_runner import DirectRunner

                    task_runner_type = DirectRunner
                case "Background":
                    from ampf.tasks.background_runner import BackgroundRunner

                    task_runner_type = BackgroundRunner
                case "PubsubPush":
                    from ampf.tasks.pubsub_push_runner import PubsubPushRunner

                    task_runner_type = PubsubPushRunner
                case "PubsubPull":
                    from ampf.tasks.pubsub_pull_runner import PubsubPullRunner

                    task_runner_type = PubsubPullRunner
                case _:
                    raise ValueError(f"Unknown task runner type: {self.config.task_runner}")

            if issubclass(task_runner_type, PubsubRunner):
                from ampf.gcp.gcp_async_factory import GcpAsyncFactory

                if not isinstance(self.factory, GcpAsyncFactory):
                    raise TypeError("The PubsubRunner requires GcpAsyncFactory!")
                self.task_runner = task_runner_type.create(self.factory, self.config)
            else:
                self.task_runner = task_runner_type
        return super().get_lifecycle_managers()


@DependencyRegistry.register
def get_task_runner(app_state: TasksAppState, background_tasks: BackgroundTasks) -> TaskRunner:
    if isinstance(app_state.task_runner, ManagedTaskRunner):
        return app_state.task_runner
    from ampf.tasks.background_runner import BackgroundRunner

    if app_state.task_runner is BackgroundRunner:
        return BackgroundRunner(background_tasks)
    elif app_state.task_runner:
        return app_state.task_runner.create()
    else:
        raise ValueError("AppState.task_runner is not set!")


async def get_dependency_container(background_tasks: BackgroundTasks) -> AsyncGenerator[DependencyContainer]:
    with DependencyRegistry.scope() as container:
        container.add(background_tasks)
        yield container
