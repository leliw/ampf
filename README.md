# AMPF - Angular + Material + Python + FastAPI

![Python](https://img.shields.io/badge/python-3.12-blue)

Set of helper classes:

* [Base] - package with base classes (mostly abstract)
  * [BaseFactory](doc/base_factory.md) - base class for factory implementations which create other objects.
  * [BaseAsyncFactory](doc/base_async_factory.md) - base class for factory implementations which create other **asynchrous** objects.
  * [BaseStorage](doc/base_storage.md) - base class for storage implementations which store Pydantic objects.
  * [BaseBlobStorage](doc/base_blob_storage.md) - base class for storage implementations which store binary objects (blobs).
  * [BaseQueryStorage](doc/base__query_storage.md) - base class for storage implementations which store Pydantic objects and support query by filters.
  * [BaseDecorator](doc/base_decorator.md) - simple class to create **Decorator** patern.
  * [SubscriptionProcessor](doc/base_subscription_processor.md) - base class for processing messages from a subscription.
* FastAPI - helper classes for FatAPI framework
  * [StaticFileResponse](doc/fastapi/static_file_response.md) - return static files or index.html (Angular files)
  * [JsonStreamingResponse](doc/fastapi/json_streaming_response.md) - streams Pydantic objects to client as JSON.
* [GCP](doc/gcp.md) - wrapping of **Google Cloud Platform** classes
  * [GcpTopic](doc/gcp/gcp_topic.md) - helper class for Pub/Sub topic.
  * [GcpSubscription](doc/gcp/gcp_subscription.md) - helper class for Pub/Sub subscription in Push mode.
  * [GcpSubscriptionPull](doc/gcp/gcp_subscription_pull.md) - helper class for Pub/Sub subscription in Pull mode.
  * [GcpPubsubPush](doc/gcp/gcp_pubsub_push.md) - helper class for handling Pub/Sub push messages.
  * [gcp_pubsub_push_handler](doc/gcp/gcp_pub_sub_handler.md) - decorator for handling Pub/Sub push messages in FastAPI endpoints (deprecated, use `gcp_pubsub_process_push` instead).
  * [gcp_pubsub_process_push](doc/gcp_pubsub_process_push.md) - helper class for processing Pub/Sub push messages.
* Testing - helper classes for testing
  * [ApiTestClient](doc/testing/api_test_client.md) - helper for testing FastAPI endpoints
  * [mock_gcp_publish](doc/testing/mock_gcp_publish.md) - helper for mocking GCP Pub/Sub publish method
  * [mock_method](doc/testing/mock_method.md) - helper for mocking methods and functions
  * [subscription_factory](doc/testing/subscription_factory.md) - helper for creating GCP Pub/Sub subscription
  * [cloud_run_proxy_factory](doc/testing/cloud_run_proxy_factory.md) - helper for running proxy to GCP Cloud Run service.
  * [container_factory](doc/testing/container_factory.md) - helper for running docker container.
  * [pubsub_manager](doc/testing/pubsub_manager.md) - helper for managing GCP Pub/Sub topics and subscriptions during testing.
  
## Build and publish

```bash
source ./build.sh
```

## Install

```bash
pip install ampf
```

Optionall dependecies:

```bash
pip install ampf[fastapi]
pip install ampf[gcp]
pip install ampf[huggingface]
pip install ampf[testing]
```

* [fastapi] - for FastAPI framework
* [gcp] - for Google Cloud Platform
* [huggingface] - for Hugging Face classes (local embedding search)
* [testing] - for pytest and pytest-mock
