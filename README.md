# AMPF - Angular + Material + Python + FastAPI

Set of helper classes:

* [Base] - package with base classes (mostly abstract)
  * [BaseFactory](doc/base_factory.md) - base class for factory implementations which create other objects.
  * [BaseStorage](doc/base_storage.md) - base class for storage implementations which store Pydantic objects.
  * [BaseDecorator](doc/base_decorator.md) - simple class to create **Decorator** patern.
* FastAPI - helper classes for FatAPI framework
  * StaticFileResponse - return static files or index.html (Angular files)
  * JsonStreamingResponse - streams Pydantic objects to client as JSON.
* [GCP](doc/gcp.md) - wrapping of **Google Cloud Platform** classes

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
```

* [fastapi] - for FastAPI framework
* [gcp] - for Google Cloud Platform
* [huggingface] - for Hugging Face classes (local embedding search)
