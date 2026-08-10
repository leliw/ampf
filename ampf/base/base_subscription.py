from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from pydantic import BaseModel

from ampf.base.base_push_emulator import BasePushEmulator
from ampf.shared.pubsub_message import PubsubMessage

_log = logging.getLogger(__name__)


class BaseSubscription[T: BaseModel](ABC):
    """A base class for Pub/Sub subscriptions."""

    @abstractmethod
    def receive_message(self, timeout: float | None = None) -> PubsubMessage | None: ...

    @abstractmethod
    def receive_messages(
        self,
        processing_timeout: float | None = None,
        per_message_timeout: float | None = None,
    ) -> Generator[Any]: ...

    @contextmanager
    def run_push_emulator(self, client, endpoint: str) -> Generator[BasePushEmulator[T]]:
        """Runs a push emulator for the subscription.

        Args:
            client: The test client to use for the emulator.
            endpoint: The endpoint to which messages should be pushed.
        """
        raise NotImplementedError("Subclasses must implement run_push_emulator")
