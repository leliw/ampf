from typing import Any, Callable, Optional
from unittest.mock import AsyncMock, MagicMock, NonCallableMagicMock

import pytest
from pytest_mock import MockerFixture


@pytest.fixture
def mock_method(mocker: MockerFixture) -> Callable[[Callable], MagicMock | AsyncMock | NonCallableMagicMock]:
    def _mock(
        method: Callable,
        return_value: Optional[Any] = None,
        side_effect: Optional[Callable] = None,
        *args,
        **kwargs,
    ) -> MagicMock | AsyncMock | NonCallableMagicMock:
        return mocker.patch(f"{method.__module__}.{method.__qualname__}", *args, return_value=return_value, side_effect=side_effect, **kwargs)

    return _mock
