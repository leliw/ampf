import pytest
import requests


@pytest.fixture(scope="session")
def scrapper_url(cloud_run_proxy_factory) -> str:
    url = cloud_run_proxy_factory("scrapper", "europe-west3")
    return url

def test_cloud_run_proxy(scrapper_url: str):
    try:
        requests.get(f"{scrapper_url}/openapi.json", timeout=10)
    except requests.ReadTimeout:
        assert False
    assert True