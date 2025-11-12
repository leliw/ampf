import logging
from abc import ABC
from typing import Any, AsyncIterator, Coroutine, Iterator, List, Type

from pydantic import BaseModel

from ampf.base import BaseAsyncFactory
from ampf.gcp import GcpPubsubRequest

_log = logging.getLogger(__name__)


class SubscriptionProcessor[T: BaseModel](ABC):
    """Base class for subscription processors.

    It is responsible for processing messages (pulled or pushed) from
    a subscription one by one.
    """

    def __init__(self, async_factory: BaseAsyncFactory, clazz: Type[T]):
        """Initializes the processor.

        Args:
            async_factory: The async factory to use for publishing responses.
            clazz: The class to use for deserializing the payload.
        """
        self.async_factory = async_factory
        self.clazz = clazz

    async def process_request(self, request: GcpPubsubRequest) -> None:
        """Processes a request.

        It calls `process_payload` method and publishes the response.

        Args:
            request: The request to process.
        """
        req = request.decoded_data(self.clazz)
        try:
            resp = self.process_payload(req)
            await self.process_response(request, resp)
        except Exception as e:
            _log.warning("Failed to process message ID:%s", request.message.messageId)
            _log.exception(e)
            raise e

    async def process_payload(
        self, payload: T
    ) -> BaseModel | Iterator[BaseModel] | List[BaseModel] | AsyncIterator[BaseModel] | None:
        """Processes a payload.

        This method should be implemented by subclasses to process the payload.
        It can return a single BaseModel, an Iterator of BaseModels, a List of BaseModels,
        an AsyncIterator of BaseModels, or None.
        Args:
            payload: The deserialized payload.
        Returns:
            The response to publish, or None if no response is needed.
        """
        raise NotImplementedError()

    async def process_response(self, request: GcpPubsubRequest, response: Any) -> None:
        """Processes & publishes the response to the topic specified in the request.

        Args:
            request: The original Pub/Sub request.
            response: The response to publish.
        """
        if isinstance(response, Coroutine):
            response = await response
        if isinstance(response, AsyncIterator):
            async for result in response:
                await self.publish_response(request, result)
        elif isinstance(response, Iterator) or isinstance(response, List):
            for result in response:
                await self.publish_response(request, result)
        elif response:
            await self.publish_response(request, response)
        else:
            _log.debug("No response to publish")

    async def publish_response(self, request: GcpPubsubRequest, response: Any) -> None:
        """Publishes the response to the topic specified in the request.

        Args:
            request: The original Pub/Sub request.
            response: The response to publish.
        """
        await request.publish_response_async(self.async_factory, response)
