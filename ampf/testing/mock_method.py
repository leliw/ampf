from collections.abc import Callable
from typing import Any, Protocol
from unittest.mock import AsyncMock, MagicMock, NonCallableMagicMock

import pytest


class MockMethod(Protocol):
    def __call__(
        self,
        method: Callable[..., Any],
        return_value: Any | None = None,
        return_values: list[Any] | None = None,
        side_effect: Callable[..., Any] | None = None,
        **kwargs: Any,  # Obejmuje *args i **kwargs przekazywane do mocker.patch
    ) -> MagicMock | AsyncMock | NonCallableMagicMock:
        raise NotImplementedError()


try:
    from pytest_mock import MockerFixture

    @pytest.fixture
    def mock_method(mocker: MockerFixture) -> MockMethod:
        def _mock(
            method: Callable,
            return_value: Any | None = None,
            return_values: list[Any] | None = None,
            side_effect: Callable[..., Any] | None = None,
            *args,
            **kwargs,
        ) -> MagicMock | AsyncMock | NonCallableMagicMock:
            return mocker.patch(
                f"{method.__module__}.{method.__qualname__}",
                *args,
                return_value=return_value,
                side_effect=side_effect or ((lambda *_, **__: return_values.pop(0)) if return_values else None),
                **kwargs,
            )

        return _mock
except ImportError:

    @pytest.fixture
    def mock_method():
        # If pytest-mock is not installed, raise an error when mock_method is called.
        raise RuntimeError("pytest-mock is not installed. Please install it to use 'mock_method'.")
