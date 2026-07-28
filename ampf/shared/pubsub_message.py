from datetime import UTC, datetime


class PubsubMessage:
    def __init__(self, message_id: str, data: str, attributes: dict[str, str]):
        self.message_id = message_id
        self.messageId = message_id 
        self.data = data
        self.attributes = attributes
        self.publish_time = datetime.now(UTC)
        self._acked = False
        self._nacked = False

    def ack(self):
        self._acked = True

    def nack(self):
        self._nacked = True

    @property
    def acked(self) -> bool:
        return self._acked

    @property
    def nacked(self) -> bool:
        return self._nacked
