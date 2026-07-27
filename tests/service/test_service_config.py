import pytest

from ampf.service.service_config import ServiceConfig


def test_required_url():
    # Given: A config with empty url
    config = ServiceConfig(url=None, api_key="test_key")
    # When & Then: Accessing required_url raises ValueError
    with pytest.raises(ValueError, match="Service URL is required"):
        _ = config.required_url


def test_required_api_key():
    # Given: A config with empty api_key
    config = ServiceConfig(url="http://example.com", api_key=None)
    # When & Then: Accessing required_api_key raises ValueError
    with pytest.raises(ValueError, match="Service API key is required"):
        _ = config.required_api_key
