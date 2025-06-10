from google.cloud import pubsub_v1
from pydantic import BaseModel


class GcpTopic[T: BaseModel]:
    def __init__(self, project_id: str, topic_id: str):
        self.project_id = project_id
        self.topic_id = topic_id
        self.publisher = pubsub_v1.PublisherClient()
        self.topic_path = self.publisher.topic_path(self.project_id, self.topic_id)

    def publish(self, data: T | str | bytes):
        if isinstance(data, str):
            data = data.encode("utf-8")
        elif isinstance(data, bytes):
            bdata = data
        elif isinstance(data, BaseModel):
            bdata = data.model_dump_json().encode("utf-8")
        else:
            raise ValueError("Unsupported data type")
        # When you publish a message, the client returns a future.
        future = self.publisher.publish(self.topic_path, bdata)
        return future.result()
