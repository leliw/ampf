# GCP

GCP package implements abstract classes using Google Cloud Platform.

## Configuration

All configuration parameters are defined in `ServerConfig` class and can be set
using environment variables.

```python
class ServerConfig(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="__")

    version: str = "0.0.1"
    data_dir: str = "./data/"

    gcp_root_storage: Optional[str] = None
```

Environment variables for GCP configuration:

* GCP_ROOT_STORAGE - Root storage name e.g. `projects/ampf`

## GcpFactory

### Constructor

You can pass `root_storage` parameter to the constructor to set the root storage.
This is the way to use separate storage for each project in one GCP project.

## GcpStorage

### Vector search - embedding

If you want to use embeddings and vector search, there is a special solution.
Create field named `embedding` of type `List[float]` and add special index in
firestore database. Then you can use `find_nearest()` method which uses vector
serach over `embedding` field.

Creating indexes:

```bash
gcloud firestore indexes composite create \
    --project=development-428212 \
    --collection-group=tests-ampf-gcp \
    --query-scope=COLLECTION \
    --field-config=vector-config='{"dimension":"3","flat": "{}"}',field-path=embedding

gcloud firestore indexes composite create \
    --project=development-428212 \
    --collection-group=tests-ampf-gcp \
    --query-scope=COLLECTION \
    --field-config=order=ASCENDING,field-path=name \
    --field-config=vector-config='{"dimension":"3","flat": "{}"}',field-path=embedding
```

Code sample:

```python
class TC(BaseModel):
    name: str
    embedding: List[float] = None

# Given: Data with embedding
tc1 = TC(name="test1", embedding=[1.0, 2.0, 3.0])
tc2 = TC(name="test2", embedding=[4.0, 5.0, 6.0])
# When: Save them
storage.put("1", tc1)
storage.put("2", tc2)
# And: Find nearest
nearest = list(storage.find_nearest(tc1.embedding))
# Then: All two are returned
assert len(nearest) == 2
# And: The nearest is the first one
assert nearest[0] == tc1
# And: The second is the second
assert nearest[1] == tc2
```

## GcpBlobStorage

Stores blobs in GCP using **Cloud Storage** service.
The constructor has an extra parameter `bucket_name` which appoints
used bucket. If all storages use the same bucket, you can set default
bucket with `init_client()` class method.

```python
GcpBlobStorage.init_client(
    bucket_name=server_config.google_bucket_name
)
```
