import logging
import os
from abc import abstractmethod
from typing import Optional

from google.cloud.pubsub_v1 import PublisherClient
from google.cloud.pubsub_v1.types import PublisherOptions

from ampf.gcp.gcp_topic import GcpTopic


class GcpBaseFactory:
    _log = logging.getLogger(__name__)
    _otel = bool(os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"))
    if _otel:
        _log.info("OpenTelemetry is enabled")
    _publisher_client = None

    @classmethod
    def get_publisher_client(cls) -> PublisherClient:
        if not cls._publisher_client:
            cls._publisher_client = PublisherClient(
                publisher_options=PublisherOptions(enable_open_telemetry_tracing=cls._otel)
            )
        return cls._publisher_client

    def __init__(self, root_storage: Optional[str] = None, bucket_name: Optional[str] = None):
        self.root_storage = root_storage[:-1] if root_storage and root_storage.endswith("/") else root_storage
        self.bucket_name = bucket_name
        self._log.debug("Using GcpFactory with root_storage=%s and bucket_name=%s", self.root_storage, self.bucket_name)

    @abstractmethod
    def get_project_id(self) -> str:
        """Returns the GCP project ID."""
        pass

    def create_topic(self, topic_id: str) -> GcpTopic:
        """Creates a GCP topic (object sender to publish messages to it).

        Args:
            topic_id: The ID of the topic.
        Returns:
            The created GcpTopic object.
        """
        return GcpTopic(topic_id, project_id=self.get_project_id(), publisher=self.get_publisher_client())
