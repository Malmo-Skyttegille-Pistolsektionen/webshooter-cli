"""Tests for offline handling and force_refresh in fetch_data."""

import json
from unittest.mock import MagicMock, patch

import pytest

from webshooter_client.api.api_calls import fetch_data, get_competitions
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

    def test_force_refresh_overrides_offline(self, reset_config, tmp_path):
        """Offline blocks the implicit fallback to the API, not an explicit refresh.

        This is what lets --refresh-competitions update the competition list while
        every other lookup stays local.
        """
        ApplicationConfig(offline=True, use_cache=True, cache_dir=str(tmp_path), token="test-token")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = json.dumps({"fresh": True})

        with patch("requests.get", return_value=mock_response) as mock_get:
            result = fetch_data("https://example.com/api", cache_key="some_key", force_refresh=True)

        assert result == {"fresh": True}
        mock_get.assert_called_once()


class TestRefreshCompetitionsSetting:
    """The competition list is the one thing an offline run may re-fetch."""

    @staticmethod
    def _competitions_payload():
        return {
            "competitions": {
                "data": [
                    {
                        "id": 1,
                        "name": "Fresh Competition",
                        "date": "2026-05-01",
                        "results_type": "precision",
                        "contact_city": "Malmö",
                        "contact_venue": "Bödkaregården",
                        "signups_closing_date": "2026-04-24",
                    }
                ]
            }
        }

    def test_refresh_competitions_refetches_the_list_while_offline(self, reset_config, tmp_path):
        ApplicationConfig(
            offline=True,
            use_cache=True,
            refresh_competitions=True,
            cache_dir=str(tmp_path),
            token="test-token",
        )
        stale = tmp_path / "competitions.json"
        stale.write_text(json.dumps({"competitions": {"data": []}}))

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = json.dumps(self._competitions_payload())

        with patch("requests.get", return_value=mock_response) as mock_get:
            competitions = get_competitions(year=None)

        mock_get.assert_called_once()
        assert list(competitions) == [1]
        assert competitions[1].name == "Fresh Competition"

    def test_without_the_setting_the_cached_list_is_used(self, reset_config, tmp_path):
        ApplicationConfig(offline=True, use_cache=True, cache_dir=str(tmp_path), token="test-token")
        cached = tmp_path / "competitions.json"
        cached.write_text(json.dumps(self._competitions_payload()))

        with patch("requests.get") as mock_get:
            competitions = get_competitions(year=None)

        mock_get.assert_not_called()
        assert list(competitions) == [1]
