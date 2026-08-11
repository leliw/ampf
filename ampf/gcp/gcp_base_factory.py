import logging
from abc import ABC, abstractmethod

from google.cloud.pubsub_v1 import PublisherClient

from ampf.gcp.gcp_topic import GcpTopic

_log = logging.getLogger(__name__)


class GcpBaseFactory(ABC):
    def __init__(self, root_storage: str | None = None, bucket_name: str | None = None, otel: bool = False):
        self.root_storage = root_storage[:-1] if root_storage and root_storage.endswith("/") else root_storage
        self.bucket_name = bucket_name
        self._otel = otel
        self._publisher_client = None
        _log.debug("Using GcpBaseFactory with root_storage=%s and bucket_name=%s", self.root_storage, self.bucket_name)

    def get_publisher_client(self) -> PublisherClient:
        if not self._publisher_client:
            from google.cloud.pubsub_v1.types import PublisherOptions

            self._publisher_client = PublisherClient(
                publisher_options=PublisherOptions(enable_open_telemetry_tracing=self._otel)
            )
        return self._publisher_client

    @abstractmethod
    def get_project_id(self) -> str:
        """Returns the GCP project ID."""
        ...

    def create_topic(self, topic_id: str) -> GcpTopic:
        """Creates a GCP topic (object sender to publish messages to it).

        Args:
            topic_id: The ID of the topic.
        Returns:
            The created GcpTopic object.
        """
        return GcpTopic(topic_id, project_id=self.get_project_id(), publisher=self.get_publisher_client())
