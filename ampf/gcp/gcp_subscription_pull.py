import asyncio
import logging
import signal
import threading
import time
from typing import Optional, Type

from google.cloud.pubsub_v1 import SubscriberClient
from google.cloud.pubsub_v1.subscriber.message import Message
from pydantic import BaseModel

from ampf.gcp.gcp_base_subscription import GcpBaseSubscription
from ampf.gcp.gcp_pubsub_model import GcpPubsubRequest


class GcpSubscriptionPull[T: BaseModel](GcpBaseSubscription):
    """A pull subscription for GCP Pub/Sub that allows processing messages with a callback."""

    _log = logging.getLogger(__name__)

    def __init__(
        self,
        subscription_id: str,
        project_id: Optional[str] = None,
        clazz: Optional[Type[T]] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        subscriber: Optional[SubscriberClient] = None,
    ):
        """Initializes the subscription.

        Args:
            subscription_id: The name of the subscription.
            project_id: The project ID.
            clazz: The class to which the message data should be deserialized.
            subscriber: The subscriber client.
        """
        super().__init__(subscription_id, project_id, clazz, subscriber)
        self.is_running = False
        self.loop = loop

    async def run_and_exit(self, processing_timeout: float = 5.0, per_message_timeout: float = 1.0):
        """The subscription asynchronously, processing messages until a timeout or SIGTERM.

        Args:
            processing_timeout: The maximum time in seconds to process messages before exiting.
            per_message_timeout: The maximum time in seconds to wait for a single message.
        """
        self.processing_timeout = processing_timeout
        self.per_message_timeout = per_message_timeout
        self.is_running = True
        self.end_time = time.time() + self.processing_timeout if self.processing_timeout else None
        signal.signal(signal.SIGTERM, self._handle_sigterm)
        await self._run()

    def run(self, per_message_timeout: float = 1.0):
        """Runs the subscription in the background, processing messages until stopped or SIGTERM.

        Args:
            per_message_timeout: The maximum time in seconds to wait for a single message.
        """
        self.per_message_timeout = per_message_timeout
        self.is_running = True
        self.end_time = None
        loop = asyncio.get_running_loop()
        loop.create_task(self._run())
        if threading.current_thread() is threading.main_thread():
            signal.signal(signal.SIGTERM, self._handle_sigterm)

    def callback(self, request: GcpPubsubRequest) -> bool:
        """Synchronous callback to process a message. By default, it runs the async version.

        Args:
            request: The Pub/Sub request containing the message.

        Returns:
            True if the message was processed successfully, False otherwise.
        """
        self._log.debug("Processing message %s", request.message.messageId)
        try:
            if self.loop:
                future = asyncio.run_coroutine_threadsafe(self.callback_async(request), self.loop)
                return future.result(timeout=300)
            else:
                return asyncio.run(self.callback_async(request))
        except TimeoutError:
            self._log.warning("Timeout while processing message %s", request.message.messageId)
            return True
        except asyncio.CancelledError:
            self._log.warning("Message processing cancelled %s", request.message.messageId)
            return True
        except Exception as e:
            self._log.exception(e)
            return True

    async def callback_async(self, request: GcpPubsubRequest) -> bool:
        raise NotImplementedError()

    def _handle_sigterm(self, *_):
        self.stop()

    def stop(self):
        """Stops the subscription."""
        self.running = False
        self.future.cancel()

    def _callback(self, message: Message):
        self._log.debug("Received message %s", message.message_id)
        req = GcpPubsubRequest.create_from_message(message, self.subscription_id)
        if self.callback(req):
            message.ack()
        else:
            message.nack()
        if self.processing_timeout:
            self.end_time = time.time() + self.processing_timeout

    async def _run(self):
        """Runs the subscription, listening for messages and invoking the callback."""
        self._log.info("Starting GCP subscription pull for %s", self.subscription_path)
        self.future = self.subscriber.subscribe(self.subscription_path, callback=self._callback)
        try:
            while not self.end_time or time.time() < self.end_time:
                if self.future.done():
                    e = self.future.exception()
                    if e:
                        raise e
                self._log.debug("Waiting for messages...")
                await asyncio.sleep(self.per_message_timeout)
                if not self.is_running:
                    break
            self._log.debug("Stopping subscription pull for %s", self.subscription_path)
        except Exception as e:
            self._log.exception(e)
            raise e
        finally:
            if self.future.running():
                self.future.cancel()
                try:
                    self.future.result(timeout=2.0)
                except TimeoutError:
                    pass
                except Exception:
                    pass
