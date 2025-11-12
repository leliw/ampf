# SubscriptionProcessor

Base class for processing messages from a subscription.
It is designed to be used with `gcp_pubsub_process_push` or `GcpSubscriptionPull`.

Type parameter:

* T - Pydantic class of the payload to be processed.

## Constructor

* `factory: BaseAsyncFactory` - An asynchronous factory to create other objects (e.g., storages, topics).
* `clazz: Type[T]` - The Pydantic model class for the payload.

## Abstract methods

* `process_payload(self, payload: T) -> T | AsyncIterator[T]` - This method must be implemented by subclasses. It defines the logic for processing the incoming payload. It can return a single processed payload or an asynchronous iterator of payloads if multiple responses are expected.

## Implemented methods

* `process_request(self, request: GcpPubsubRequest) -> None` - Processes a request. It calls `process_payload` method and publishes the response.
* `publish_response(self, request: GcpPubsubRequest, response: Any) -> None` - Publishes the response to the topic specified in the request.

## Usage
