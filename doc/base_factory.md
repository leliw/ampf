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

* `create_storage[T: BaseModel](self, collection_name: str, clazz: Type[T], key: Optional[str | Callable[[T], str]] = None) -> BaseQueryStorage[T]` - Create a storage for the given collection name and class. The key is optional and if not provided, the first field of the class is used as the key.
* `create_blob_storage[T: BaseBlobMetadata](self, collection_name: Optional[str] = None, clazz: Optional[Type[T]] = None, content_type: Optional[str] = None, bucket_name: Optional[str] = None) -> BaseBlobStorage[T]` - Create a blob storage for the given collection name and class.

## Implemented methods

* `create_compact_storage[T: BaseModel](self, collection_name: str, clazz: Type[T], key: Optional[str | Callable[[T], str]] = None) -> BaseQueryStorage[T]` - Create a compact storage for the given collection name and class. It calls `create_storage()` by default.
* `create_collection[T: BaseModel](self, definition: CollectionDef[T] | dict) -> BaseCollectionStorage[T]` - Create a collection storage for the given collection definition.
* `create_storage_tree[T: BaseModel](self, root: CollectionDef[T]) -> BaseCollectionStorage[T]` - Create a storage tree for the given collection definition.
* `register_collections(self, definitions: list[CollectionDef[Any]])` - Registers a list of collection definitions in the factory.
* `get_collection[T: BaseModel](self, collection_name_or_type: str | Type[T]) -> BaseCollectionStorage[T]` - Retrieves a collection by its name or type from the registered definitions.
* `create_blob_location(self, name: str, bucket: Optional[str] = None) -> BlobLocation` - Create a blob location for the given name and bucket.
* `download_blob(self, blob_location: BlobLocation) -> Blob` - Download a blob from the given location.
* `upload_blob(self, blob_location: BlobLocation, blob: Blob) -> None` - Upload a blob to the given location.
