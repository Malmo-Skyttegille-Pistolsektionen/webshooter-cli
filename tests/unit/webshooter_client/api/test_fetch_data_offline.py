"""Tests for offline handling and force_refresh in fetch_data."""

import json
from unittest.mock import MagicMock, patch

import pytest

from webshooter_client.api.api_calls import fetch_data
from webshooter_client.api.exceptions import OfflineCacheMissError
from webshooter_client.common.application_config import ApplicationConfig


@pytest.fixture
def reset_config():
    """Reset the ApplicationConfig singleton between tests."""
    ApplicationConfig._instances = {}
    yield
    ApplicationConfig._instances = {}


class TestFetchDataOffline:
    def test_offline_raises_on_cache_miss_and_never_calls_requests(self, reset_config, tmp_path):
        ApplicationConfig(offline=True, use_cache=True, cache_dir=str(tmp_path))

        with patch("requests.get") as mock_get:
            with pytest.raises(OfflineCacheMissError):
                fetch_data("https://example.com/api", cache_key="missing_key")

        mock_get.assert_not_called()

    def test_offline_returns_cached_value_without_network_call(self, reset_config, tmp_path):
        ApplicationConfig(offline=True, use_cache=True, cache_dir=str(tmp_path))
        cache_file = tmp_path / "present_key.json"
        cache_file.write_text(json.dumps({"cached": True}))

        with patch("requests.get") as mock_get:
            result = fetch_data("https://example.com/api", cache_key="present_key")

        assert result == {"cached": True}
        mock_get.assert_not_called()

    def test_offline_error_carries_cache_key_and_url(self, reset_config, tmp_path):
        ApplicationConfig(offline=True, use_cache=True, cache_dir=str(tmp_path))

        with pytest.raises(OfflineCacheMissError) as exc_info:
            fetch_data("https://example.com/api", cache_key="missing_key")

        assert exc_info.value.cache_key == "missing_key"
        assert exc_info.value.url == "https://example.com/api"


class TestFetchDataForceRefresh:
    def test_force_refresh_bypasses_cached_value_but_writes_fresh_data(self, reset_config, tmp_path):
        ApplicationConfig(use_cache=True, cache_dir=str(tmp_path), token="test-token")
        cache_file = tmp_path / "some_key.json"
        cache_file.write_text(json.dumps({"old": True}))

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = json.dumps({"new": True})

        with patch("requests.get", return_value=mock_response) as mock_get:
            result = fetch_data("https://example.com/api", cache_key="some_key", force_refresh=True)

        assert result == {"new": True}
        mock_get.assert_called_once()
        assert json.loads(cache_file.read_text()) == {"new": True}

    def test_without_force_refresh_cached_value_is_used(self, reset_config, tmp_path):
        ApplicationConfig(use_cache=True, cache_dir=str(tmp_path), token="test-token")
        cache_file = tmp_path / "some_key.json"
        cache_file.write_text(json.dumps({"old": True}))

        with patch("requests.get") as mock_get:
            result = fetch_data("https://example.com/api", cache_key="some_key")

        assert result == {"old": True}
        mock_get.assert_not_called()
