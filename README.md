# AMPF - Angular + Material + Python + FastAPI

![Python](https://img.shields.io/badge/python-3.12-blue)

Set of helper classes:

* [Base] - package with base classes (mostly abstract)
  * [BaseFactory](doc/base_factory.md) - base class for factory implementations which create other objects.
  * [BaseStorage](doc/base_storage.md) - base class for storage implementations which store Pydantic objects.
  * [BaseQueryStorage](doc/base__query_storage.md) - base class for storage implementations which store Pydantic objects and support query by filters.
  * [BaseDecorator](doc/base_decorator.md) - simple class to create **Decorator** patern.
* FastAPI - helper classes for FatAPI framework
  * [StaticFileResponse](doc/fastapi/static_file_response.md) - return static files or index.html (Angular files)
  * [JsonStreamingResponse](doc/fastapi/json_streaming_response.md) - streams Pydantic objects to client as JSON.
* [GCP](doc/gcp.md) - wrapping of **Google Cloud Platform** classes
  * [gcp_pubsub_push_handler](doc/gcp_pub_sub_handler.md) - decorator for handling Pub/Sub push messages in FastAPI endpoints
* Testing - helper classes for testing
  * [ApiTestClient](doc/testing/api_test_client.md) - helper for testing FastAPI endpoints
  * [mock_gcp_publish](doc/testing/mock_gcp_publish.md) - helper for mocking GCP Pub/Sub publish method
  * [subscription_factory](doc/testing/subscription_factory.md) - helper for creating GCP Pub/Sub subscription
  * [cloud_run_proxy_factory](doc/testing/cloud_run_proxy_factory.md) - helper for running proxy to GCP Cloud Run service.
  * [container_factory](doc/testing/fixtrue_container_factory.md) - helper for running docker container.
  
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
