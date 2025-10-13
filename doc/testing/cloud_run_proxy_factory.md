# cloud_run_proxy_factory

Fixture that run proxy to GCP Cloud Run service.

## Parameters

* `service: str` - Cloud Run service name.
* `region: str` Cloud Run region.
* `port Optional[int]` - Port to expose. If not provided, a random port will be used.

## Returns

* `url` - `f"http://127.0.0.1:{port}"` - Service url.

## Usage

Declare fixture in `conftest.py`

```python
from ampf.testing import *  # noqa: F403

```

```python
@pytest.fixture
def scrapper_url(cloud_run_proxy_factory) -> str:
    url = cloud_run_proxy_factory("scrapper", "europe-west3")
    return url

def test_cloud_run_proxy(scrapper_url: str):
    try:
        requests.get(f"{scrapper_url}/openapi.json", timeout=1)
    except requests.ReadTimeout:
        assert False
    assert True
```
