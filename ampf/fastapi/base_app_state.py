import logging
from abc import ABC
from collections.abc import AsyncGenerator
from contextlib import AbstractAsyncContextManager, AsyncExitStack, asynccontextmanager
from typing import Any, Protocol, Self, runtime_checkable

from fastapi import FastAPI

_log = logging.getLogger(__name__)


@runtime_checkable
class LifecycleManager(Protocol):
    def manage_lifecycle(self, app: FastAPI) -> AbstractAsyncContextManager[Any]: ...


class BaseAppState(ABC):
    def get_lifecycle_managers(self) -> list[LifecycleManager]:
        managers: list[LifecycleManager] = []
        for name in dir(self):
            if name.startswith("_"):
                continue
            try:
                attr = getattr(self, name)
                if not callable(attr) and isinstance(attr, LifecycleManager):
                    managers.append(attr)
            except Exception:
                _log.exception("Failed to inspect attribute '%s' for lifecycle manager", name)
                continue
        return managers

    @asynccontextmanager
    async def manage_lifecycle(self, app: FastAPI) -> AsyncGenerator[Self]:
        async with AsyncExitStack() as stack:
            for lm in self.get_lifecycle_managers():
                await stack.enter_async_context(lm.manage_lifecycle(app))
            yield self
