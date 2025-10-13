# container_factory

Fixture that run docker container.

## Parameters

* `image: str` - Docker image.
* `name: str` - Container name.
* `ports: List[str]` - Container ports to expose.
* `wait_for_http: str` - Optional path to check service readiness, e.g. '/docs'.
* `timeout: int` - How long to wait for container readiness.
* `gpus: bool` - Whether to use GPUs.

## Returns

* URL of the started container.

## Usage

Declare fixture in `conftest.py`

```python
from ampf.testing import *  # noqa: F403
```
