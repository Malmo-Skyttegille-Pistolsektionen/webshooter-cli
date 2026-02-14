"""Tests for API calls with caching integration."""

import json
from unittest.mock import patch, MagicMock

import pytest

from webshooter_client.api.api_calls import (
    fetch_data,
    get_competitions,
    get_competition,
)
from webshooter_client.common.application_config import ApplicationConfig


@pytest.fixture
def reset_config():
    """Reset ApplicationConfig singleton between tests."""
    ApplicationConfig._instances = {}
    yield
    ApplicationConfig._instances = {}


@pytest.fixture
def mock_cache():
    """Mock the cache functions."""
    with (
        patch("webshooter_client.api.api_calls.load_from_cache") as mock_load,
        patch("webshooter_client.api.api_calls.save_to_cache") as mock_save,
    ):
        yield {"load": mock_load, "save": mock_save}


class TestFetchDataCaching:
    """Tests for fetch_data function with caching."""

    def test_fetch_data_without_cache_key(self, reset_config, mock_cache):
        """fetch_data without cache_key doesn't use cache."""
        ApplicationConfig(use_cache=True, token="test_token")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"data": "test"}'

        with patch("requests.get", return_value=mock_response):
            result = fetch_data("https://test.com/api")

        assert result == {"data": "test"}
        mock_cache["load"].assert_not_called()
        mock_cache["save"].assert_not_called()

    def test_fetch_data_loads_from_cache_when_available(self, reset_config, mock_cache):
        """fetch_data loads from cache when cache_key provided and data exists."""
        ApplicationConfig(use_cache=True, token="test_token")

        cached_data = {"data": "from_cache"}
        mock_cache["load"].return_value = cached_data

        # Should not make HTTP request
        with patch("requests.get") as mock_get:
            result = fetch_data("https://test.com/api", cache_key="test_key")

        assert result == cached_data
        mock_cache["load"].assert_called_once_with("test_key")
        mock_get.assert_not_called()

    def test_fetch_data_saves_to_cache_after_successful_fetch(self, reset_config, mock_cache):
        """fetch_data saves response to cache after successful API call."""
        ApplicationConfig(use_cache=True, token="test_token")

        mock_cache["load"].return_value = None  # Cache miss

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"data": "from_api"}'

        with patch("requests.get", return_value=mock_response):
            result = fetch_data("https://test.com/api", cache_key="test_key")

        assert result == {"data": "from_api"}
        mock_cache["load"].assert_called_once_with("test_key")
        mock_cache["save"].assert_called_once_with("test_key", {"data": "from_api"})

    def test_fetch_data_does_not_save_on_error(self, reset_config, mock_cache):
        """fetch_data doesn't save to cache on HTTP errors."""
        ApplicationConfig(use_cache=True, token="test_token")

        mock_cache["load"].return_value = None  # Cache miss

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not found"

        with patch("requests.get", return_value=mock_response):
            with pytest.raises(Exception):  # Should raise APIClientError
                fetch_data("https://test.com/api", cache_key="test_key")

        mock_cache["save"].assert_not_called()

    def test_fetch_data_cache_disabled(self, reset_config, mock_cache):
        """fetch_data with cache_key still works when cache is disabled."""
        ApplicationConfig(use_cache=False, token="test_token")

        # When cache is disabled, load_from_cache returns None
        mock_cache["load"].return_value = None

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"data": "from_api"}'

        with patch("requests.get", return_value=mock_response):
            result = fetch_data("https://test.com/api", cache_key="test_key")

        assert result == {"data": "from_api"}
        # Cache load should be called (it handles disabled state internally)
        mock_cache["load"].assert_called_once_with("test_key")


class TestGetCompetitionsWithCache:
    """Tests for get_competitions function with caching."""

    def test_get_competitions_uses_cache_key(self, reset_config, testdata_resources_rootdir_w_path):
        """get_competitions passes cache key to fetch_data."""
        ApplicationConfig(use_cache=True, token="test_token")

        # Load real test data
        with open(testdata_resources_rootdir_w_path("competitions/competitions.json")) as f:
            competitions_data = json.load(f)

        with patch("webshooter_client.api.api_calls.fetch_data") as mock_fetch:
            mock_fetch.return_value = competitions_data

            get_competitions(year=None)

            # Verify fetch_data was called with cache key
            mock_fetch.assert_called_once()
            assert mock_fetch.call_args.kwargs["cache_key"] == "competitions"

    def test_get_competitions_filters_by_year_after_caching(self, reset_config, testdata_resources_rootdir_w_path):
        """get_competitions filters by year even when loading from cache."""
        ApplicationConfig(use_cache=True, token="test_token")

        # Mock cache returning all competitions
        with open(testdata_resources_rootdir_w_path("competitions/competitions.json")) as f:
            all_competitions = json.load(f)

        with patch("webshooter_client.api.api_calls.load_from_cache") as mock_load:
            mock_load.return_value = all_competitions

            # Request only 2024 competitions
            result_2024 = get_competitions(year=2024)

            # All returned competitions should be from 2024
            for comp in result_2024.values():
                assert comp.competition_date.year == 2024


class TestGetCompetitionWithCache:
    """Tests for get_competition function with caching."""

    def test_get_competition_uses_cache_key_with_id(self, reset_config, testdata_resources_rootdir_w_path):
        """get_competition passes cache key with competition ID to fetch_data."""
        ApplicationConfig(use_cache=True, token="test_token")

        competition_id = 149

        # Load real test data (flat structure like cache)
        with open(testdata_resources_rootdir_w_path(f"competitions/competition_{competition_id}.json")) as f:
            competition_data = json.load(f)

        with patch("webshooter_client.api.api_calls.fetch_data") as mock_fetch:
            mock_fetch.return_value = competition_data

            result = get_competition(competition_id)

            # Verify fetch_data was called with cache key including ID
            mock_fetch.assert_called_once()
            # Check keyword arguments
            assert mock_fetch.call_args.kwargs["cache_key"] == f"competition_{competition_id}"
            assert result.id == competition_id
