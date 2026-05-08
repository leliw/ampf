import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from ampf.gcp import gcp_pubsub_push_handler

from .pubsub_runner import PubsubRunner
from .task_registry import TaskRegistry

_log = logging.getLogger(__name__)


class PubsubPushRunner(PubsubRunner):
    @asynccontextmanager
    async def manage_lifecycle(self, app: FastAPI):
        if not self._initialised:
            self._initialised = True
            self._setup_routes(app)
        yield self

    def _setup_routes(self, app: FastAPI):
        router = APIRouter(prefix="/pub-sub/task-processors", tags=["Pub/Sub Push task processors"])

        for task_name, processor_definition in TaskRegistry._tasks.items():
            if processor_definition.payload_type is None:
                _log.warning("Payload type is missing for task %s, skipping route creation", task_name)
                continue

            def create_handler(name: str):
                @gcp_pubsub_push_handler()
                async def endpoint(payload: processor_definition.payload_type) -> None:  # pyright: ignore[reportInvalidTypeForm]
                    _log.info("Received push task: %s", name)
                    await TaskRegistry.run_task_async(name, payload)

                return endpoint

            router.add_api_route(
                f"/{task_name}",
                create_handler(task_name),
                methods=["POST"],
                status_code=204,
                response_model=None,
            )

        app.include_router(router)
        _log.info("Pub/Sub Push routes registered.")
