from typing import Any, Callable, Optional, Protocol, Union
from unittest.mock import AsyncMock, MagicMock, NonCallableMagicMock

import pytest


class MockMethod(Protocol):
    def __call__(
        self,
        method: Callable[..., Any],
        return_value: Optional[Any] = None,
        side_effect: Optional[Callable[..., Any]] = None,
        **kwargs: Any,  # Obejmuje *args i **kwargs przekazywane do mocker.patch
    ) -> Union[MagicMock, AsyncMock, NonCallableMagicMock]:
        raise NotImplementedError()


try:
    from pytest_mock import MockerFixture

    @pytest.fixture
    def mock_method(mocker: MockerFixture) -> MockMethod:
        def _mock(
            method: Callable,
            return_value: Optional[Any] = None,
            side_effect: Optional[Callable] = None,
            *args,
            **kwargs,
        ) -> MagicMock | AsyncMock | NonCallableMagicMock:
            return mocker.patch(
                f"{method.__module__}.{method.__qualname__}",
                *args,
                return_value=return_value,
                side_effect=side_effect,
                **kwargs,
            )

        return _mock
except ImportError:

    @pytest.fixture
    def mock_method(mocker: Any):
        # If pytest-mock is not installed, raise an error when mock_method is called.
        raise RuntimeError("pytest-mock is not installed. Please install it to use 'mock_method'.")
