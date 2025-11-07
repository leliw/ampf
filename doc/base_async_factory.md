# BaseAsyncFactory

Base class for **async** factory implementations which create other objects.

Usually it is created in `lifespan` function of FastAPI app and stored in app state.
Then it can be accessed by `AsyncFactoryDep` dependency.
The specific factory is used depending on the configuration of the server.

```python
def lifespan(config: ServerConfig = ServerConfig()):
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.config = config
        if config.gcp_root_storage or config.gcp_bucket_name:
            from ampf.gcp import GcpAsyncFactory

            app.state.async_factory = GcpAsyncFactory(
                root_storage=config.gcp_root_storage, bucket_name=config.gcp_bucket_name
            )
        else:
            from ampf.local_async import AsyncLocalFactory

            app.state.async_factory = AsyncLocalFactory(config.data_dir)
        yield
    return lifespan

def get_app(request: Request) -> FastAPI:
    return request.app


AppDep = Annotated[FastAPI, Depends(get_app)]


def get_server_config(app: AppDep) -> ServerConfig:
    return app.state.config


ConfigDep = Annotated[ServerConfig, Depends(get_server_config)]


def get_async_factory(app: AppDep) -> BaseAsyncFactory:
    return app.state.async_factory


AsyncFactoryDep = Annotated[BaseAsyncFactory, Depends(get_async_factory)]
```

## Constructor

The constructor of the base factory takes no parameters but derived classes
may have additional parameters to configure the factory.

## Abstract methods

* `create_storage[T: BaseModel](self, collection_name: str, clazz: Type[T], key: Optional[str | Callable[[T], str]] = None) -> BaseAsyncQueryStorage[T]` - Create a storage for the given collection name and class. The key is optional and if not provided, the first field of the class is used as the key.
* `create_blob_storage[T: BaseModel](self, collection_name: Optional[str] = None, clazz: Optional[Type[T]] = None, content_type: Optional[str] = None, bucket_name: Optional[str] = None) -> BaseAsyncBlobStorage[T]` - Create a blob storage for the given collection name and class. The content type is optional and if not provided, it defaults to `application/octet-stream`.
* `create_topic(self, topic_id: str) -> BaseTopic[BaseModel]` - Create a topic for the given topic id.

## Implemented methods

* `create_compact_storage[T: BaseModel](self, collection_name: str, clazz: Type[T], key: Optional[str | Callable[[T], str]] = None) -> BaseAsyncQueryStorage[T]` - Create a compact storage for the given collection name and class. It calls `create_storage()` by default but can be overridden in derived classes to provide a different more efficient implementation for small data sets e.g. one json file for the whole collection.
* `create_collection[T: BaseModel](self, definition: CollectionDef[T] | dict) -> BaseAsyncCollectionStorage[T]` - Create a collection storage for the given collection definition.
* `create_storage_tree[T: BaseModel](self, root: CollectionDef[T]) -> BaseAsyncCollectionStorage[T]` - Create a storage tree for the given collection definition.
* `download_blob(self, blob_location: BlobLocation) -> Blob` - Download a blob from the given location.
* `upload_blob(self, blob_location: BlobLocation, blob: Blob) -> None` - Upload a blob to the given location.
* `publish_message(self, topic_id: str, data: BaseModel | str | bytes, response_topic: Optional[str] = None, sender_id: Optional[str] = None) -> str` - Publish a message to the given topic.
* `create_blob_location(self, name: str, bucket: Optional[str] = None) -> BlobLocation` - Create a blob location for the given name.
