import os
from typing import Optional

from google.cloud import pubsub_v1
from pydantic import BaseModel


class GcpTopic[T: BaseModel]:
    def __init__(self, topic_id: str, project_id: Optional[str] = None):
        self.topic_id = topic_id
        self.project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")
        if not self.project_id:
            raise ValueError("Project ID or GOOGLE_CLOUD_PROJECT environment variable is not set")
        self.publisher = pubsub_v1.PublisherClient()
        self.topic_path = self.publisher.topic_path(self.project_id, self.topic_id)

    def publish(self, data: T | str | bytes):
        if isinstance(data, str):
            bdata = data.encode("utf-8")
        elif isinstance(data, bytes):
            bdata = data
        elif isinstance(data, BaseModel):
            bdata = data.model_dump_json().encode("utf-8")
        else:
            raise ValueError("Unsupported data type")
        # When you publish a message, the client returns a future.
        future = self.publisher.publish(self.topic_path, bdata)
        return future.result()
