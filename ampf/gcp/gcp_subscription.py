import os
import queue
import time
from concurrent.futures import TimeoutError
from typing import Generator, Optional, Type

from google.cloud import pubsub_v1
from pydantic import BaseModel


class GcpSubscription[T: BaseModel]:
    def __init__(
        self,
        subscription_id: str,
        project_id: Optional[str] = None,
        clazz: Optional[Type[T]] = None,
        processing_timeout: float = 5.0,
        per_message_timeout: float = 1.0,
    ):
        self.subscription_id = subscription_id
        self.project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT", "")
        if not self.project_id:
            raise ValueError("Project ID or GOOGLE_CLOUD_PROJECT environment variable is not set")        
        self.clazz = clazz
        self.processing_timeout = processing_timeout
        self.per_message_timeout = per_message_timeout

    def __iter__(self) -> Generator[T, None, None]:
        _messages_queue = queue.Queue()
        subscriber = pubsub_v1.SubscriberClient()
        subscription_path = subscriber.subscription_path(
            self.project_id, self.subscription_id
        )

        def callback(message: pubsub_v1.subscriber.message.Message) -> None:  # type: ignore
            _messages_queue.put(message)
            message.ack()

        streaming_pull_future = subscriber.subscribe(
            subscription_path, callback=callback
        )

        with subscriber:
            end_time = time.time() + self.processing_timeout
            try:
                while time.time() < end_time:
                    try:
                        remaining_time_for_cycle = end_time - time.time()
                        if remaining_time_for_cycle <= 0:
                            break

                        current_wait_timeout = min(
                            self.per_message_timeout, remaining_time_for_cycle
                        )

                        message = _messages_queue.get(
                            block=True, timeout=current_wait_timeout
                        )
                        if self.clazz:
                            yield self.clazz.model_validate_json(message.data.decode("utf-8"))
                        else:
                            yield message
                    except queue.Empty:
                        if not streaming_pull_future.running():
                            break
                        continue
            finally:
                if streaming_pull_future.running():
                    streaming_pull_future.cancel()
                    try:
                        streaming_pull_future.result(timeout=2.0)
                    except TimeoutError:
                        pass
                    except Exception:
                        pass
