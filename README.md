# AMPF - Angular + Material + Python + FastAPI

Set of helper classes:

* [Base] - package with base classes (mostly abstract)
  * [BaseStorage](doc/base_storage.md) - base class for storage implementations which store Pydantic objects.
  * [BaseDecorator](doc/base_decorator.md) - simple class to create **Decorator** patern.
* FastAPI - helper classes for FatAPI framework
  * StaticFileResponse - return static files or index.html (Angular files)
  * JsonStreamingResponse - streams Pydantic objects to client as JSON.
* [GCP](doc/gcp.md) - wrapping of **Google Cloud Platform** classes

## Build

Remove previous built and build library again.

```bash
rm dist/*; python -m build
```

Upload to private repository.

```bash
python3 -m twine upload --repository-url https://europe-west3-python.pkg.dev/development-428212/pip dist/*
```
