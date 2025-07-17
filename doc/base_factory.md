# BaseFactory

Base class for factory implementations which create other objects.
Factory is a singleton and can be used to create objects of different types.

Usually it is created in `lifespan` function of FastAPI app and stored in app state.
Then it can be accessed by `FactoryDep` dependency.
The specific factory is used depending on the configuration of the server.

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    config = ServerConfig()
    app.state.config = config
    if app.state.config.gcp_root_storage:
        from ampf.gcp import GcpFactory
        
        app.state.factory = GcpFactory(app.state.config.gcp_root_storage)
        _log.info(f"GCP storage: {app.state.config.gcp_root_storage}")
    else:
        app.state.factory = LocalFactory(app.state.config.data_dir)
        _log.info(f"Local storage: {app.state.config.data_dir}")
    yield

def get_app(request: Request) -> FastAPI:
    return request.app


AppDep = Annotated[FastAPI, Depends(get_app)]


def get_server_config(app: FastAPI = Depends(get_app)) -> ServerConfig:
    return app.state.config


ConfigDep = Annotated[ServerConfig, Depends(get_server_config)]


ServerConfigDep = Annotated[ServerConfig, Depends(get_server_config)]


def get_factory(app: FastAPI = Depends(get_app)) -> BaseFactory:
    return app.state.factory


FactoryDep = Annotated[BaseFactory, Depends(get_factory)]
```

## Constructor

The constructor of the base factory takes no parameters but derived classes
may have additional parameters to configure the factory.

## Abstract methods

* create_storage[T: BaseModel](self, collection_name: str, clazz: Type[T], key: Optional[str | Callable[[T], str]] = None) -> BaseStorage[T]
  * Create a storage for the given collection name and class.
  * The key is optional and if not provided, the first field of the class is used as the key.
* create_blob_storage[T: BaseModel](self, collection_name: str, clazz: Optional[Type[T]] = None, content_type: Optional[str] = None) -> BaseBlobStorage[T]
  * Create a blob storage for the given collection name and class.
  * The content type is optional and if not provided, it defaults to `application/octet-stream`.

## Implemented methods

* create_compact_storage[T: BaseModel](self, collection_name: str, clazz: Type[T], key: Optional[str | Callable[[T], str]] = None) -> BaseStorage[T]
  * Create a compact storage for the given collection name and class.
  * It calls `create_storage()` by default but can be overridden in derived classes to provide a different more efficient implementation for small data sets e.g. one json file for the whole collection.
