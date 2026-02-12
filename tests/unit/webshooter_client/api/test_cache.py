"""Tests for API caching functionality."""

import json

import pytest

from webshooter_client.api.cache import (
    load_from_cache,
    save_to_cache,
    get_cache_key_for_competitions,
    get_cache_key_for_competition,
    get_cache_key_for_page,
)
from webshooter_client.common.application_config import ApplicationConfig


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Provide a temporary cache directory for testing."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return cache_dir


@pytest.fixture
def reset_config():
    """Reset ApplicationConfig singleton between tests."""
    # Clear the singleton instance
    ApplicationConfig._instances = {}
    yield
    # Clear again after test
    ApplicationConfig._instances = {}


@pytest.fixture
def mock_cache_dir(temp_cache_dir, reset_config):
    """Mock the cache directory to use temporary directory."""
    # Set cache_dir in ApplicationConfig
    ApplicationConfig(cache_dir=str(temp_cache_dir))
    yield temp_cache_dir


class TestCacheKeyGeneration:
    """Tests for cache key generation functions."""

    def test_get_cache_key_for_competitions(self):
        """Cache key for competitions list is consistent."""
        key = get_cache_key_for_competitions()
        assert key == "competitions"

    def test_get_cache_key_for_competition(self):
        """Cache key for single competition includes competition ID."""
        key = get_cache_key_for_competition(123)
        assert key == "competition_123"

    def test_get_cache_key_for_page(self):
        """Cache key for competition page includes ID and page name."""
        key = get_cache_key_for_page(123, "results")
        assert key == "competition_123_results"

    def test_get_cache_key_for_page_strips_query_params(self):
        """Cache key strips query parameters from page name."""
        key = get_cache_key_for_page(123, "signups?page=1&per_page=1000")
        assert key == "competition_123_signups"


class TestSaveToCache:
    """Tests for save_to_cache function."""

    def test_save_to_cache_when_disabled(self, mock_cache_dir, reset_config):
        """Saving to cache does nothing when cache is disabled."""
        ApplicationConfig(use_cache=False)

        data = {"test": "data"}
        save_to_cache("test_key", data)

        cache_file = mock_cache_dir / "test_key.json"
        assert not cache_file.exists()

    def test_save_to_cache_when_enabled(self, mock_cache_dir, reset_config):
        """Saving to cache creates file when cache is enabled."""
        config = ApplicationConfig()
        config.use_cache = True

        data = {"test": "data", "nested": {"value": 123}}
        save_to_cache("test_key", data)

        cache_file = mock_cache_dir / "test_key.json"
        assert cache_file.exists()

        # Verify content
        with open(cache_file, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
        assert saved_data == data

    def test_save_to_cache_creates_directory(self, tmp_path, reset_config):
        """Saving to cache creates directory if it doesn't exist."""
        cache_dir = tmp_path / "nonexistent" / "cache"
        ApplicationConfig(use_cache=True, cache_dir=str(cache_dir))

        assert not cache_dir.exists()

        save_to_cache("test_key", {"data": "test"})

        # Directory should be created
        assert cache_dir.exists()
        assert (cache_dir / "test_key.json").exists()

    def test_save_to_cache_with_unicode(self, mock_cache_dir, reset_config):
        """Saving to cache preserves unicode characters."""
        config = ApplicationConfig()
        config.use_cache = True

        data = {"name": "Tävling", "city": "Göteborg"}
        save_to_cache("test_key", data)

        cache_file = mock_cache_dir / "test_key.json"
        with open(cache_file, "r", encoding="utf-8") as f:
            saved_data = json.load(f)

        assert saved_data["name"] == "Tävling"
        assert saved_data["city"] == "Göteborg"


class TestLoadFromCache:
    """Tests for load_from_cache function."""

    def test_load_from_cache_when_disabled(self, mock_cache_dir, reset_config):
        """Loading from cache returns None when cache is disabled."""
        ApplicationConfig(use_cache=False)

        # Create a cache file
        cache_file = mock_cache_dir / "test_key.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump({"test": "data"}, f)

        # Should return None because cache is disabled
        result = load_from_cache("test_key")
        assert result is None

    def test_load_from_cache_when_file_not_exists(self, mock_cache_dir, reset_config):
        """Loading from cache returns None when file doesn't exist."""
        config = ApplicationConfig()
        config.use_cache = True

        result = load_from_cache("nonexistent_key")
        assert result is None

    def test_load_from_cache_when_file_exists(self, mock_cache_dir, reset_config):
        """Loading from cache returns data when file exists."""
        config = ApplicationConfig()
        config.use_cache = True

        # Create a cache file
        data = {"test": "data", "value": 123}
        cache_file = mock_cache_dir / "test_key.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

        # Load from cache
        result = load_from_cache("test_key")
        assert result == data

    def test_load_from_cache_with_corrupted_file(self, mock_cache_dir, reset_config):
        """Loading from cache returns None when JSON is corrupted."""
        config = ApplicationConfig()
        config.use_cache = True

        # Create a corrupted cache file
        cache_file = mock_cache_dir / "test_key.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write("this is not valid JSON {{{")

        # Should return None and not crash
        result = load_from_cache("test_key")
        assert result is None

    def test_load_from_cache_with_unicode(self, mock_cache_dir, reset_config):
        """Loading from cache preserves unicode characters."""
        config = ApplicationConfig()
        config.use_cache = True

        # Create cache with unicode
        data = {"name": "Tävling", "city": "Göteborg"}
        cache_file = mock_cache_dir / "test_key.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

        # Load from cache
        result = load_from_cache("test_key")
        assert result["name"] == "Tävling"
        assert result["city"] == "Göteborg"


class TestCacheIntegration:
    """Integration tests for cache save and load."""

    def test_save_then_load_roundtrip(self, mock_cache_dir, reset_config):
        """Data saved to cache can be loaded back identically."""
        config = ApplicationConfig()
        config.use_cache = True

        original_data = {
            "competitions": {
                "data": [{"id": 123, "name": "Test Competition"}, {"id": 456, "name": "Another Competition"}]
            }
        }

        # Save to cache
        save_to_cache("test_competitions", original_data)

        # Load from cache
        loaded_data = load_from_cache("test_competitions")

        assert loaded_data == original_data

    def test_multiple_cache_files(self, mock_cache_dir, reset_config):
        """Multiple cache files can coexist."""
        config = ApplicationConfig()
        config.use_cache = True

        data1 = {"type": "competitions"}
        data2 = {"type": "competition", "id": 123}
        data3 = {"type": "results"}

        save_to_cache("key1", data1)
        save_to_cache("key2", data2)
        save_to_cache("key3", data3)

        assert load_from_cache("key1") == data1
        assert load_from_cache("key2") == data2
        assert load_from_cache("key3") == data3


class TestClearCache:
    """Tests for clear_cache() function."""

    def test_clear_cache_with_files(self, mock_cache_dir, reset_config):
        """Clearing cache deletes all files and returns count."""
        from webshooter_client.api.cache import clear_cache

        # Enable cache and create some cache files
        config = ApplicationConfig()
        config.use_cache = True
        save_to_cache("test1", {"data": "one"})
        save_to_cache("test2", {"data": "two"})
        save_to_cache("test3", {"data": "three"})

        # Verify files exist
        assert (mock_cache_dir / "test1.json").exists()
        assert (mock_cache_dir / "test2.json").exists()
        assert (mock_cache_dir / "test3.json").exists()

        # Clear cache
        deleted_count = clear_cache()

        # Verify all files deleted
        assert deleted_count == 3
        assert not (mock_cache_dir / "test1.json").exists()
        assert not (mock_cache_dir / "test2.json").exists()
        assert not (mock_cache_dir / "test3.json").exists()

    def test_clear_cache_empty_directory(self, mock_cache_dir, reset_config):
        """Clearing empty cache returns 0."""
        from webshooter_client.api.cache import clear_cache

        # Cache directory exists but is empty
        deleted_count = clear_cache()
        assert deleted_count == 0

    def test_clear_cache_no_directory(self, tmp_path, reset_config):
        """Clearing non-existent cache directory returns 0."""
        from webshooter_client.api.cache import clear_cache

        # Use a cache directory that doesn't exist
        non_existent = tmp_path / "does_not_exist"
        ApplicationConfig(cache_dir=str(non_existent))
        deleted_count = clear_cache()
        assert deleted_count == 0

    def test_clear_cache_only_deletes_json_files(self, mock_cache_dir, reset_config):
        """Clear cache only deletes .json files, not other files."""
        from webshooter_client.api.cache import clear_cache

        # Create cache files and other files
        config = ApplicationConfig()
        config.use_cache = True
        save_to_cache("test1", {"data": "one"})

        # Create non-JSON file
        other_file = mock_cache_dir / "README.txt"
        other_file.write_text("Do not delete")

        # Clear cache
        deleted_count = clear_cache()

        # Only JSON file deleted
        assert deleted_count == 1
        assert not (mock_cache_dir / "test1.json").exists()
        assert other_file.exists()  # Non-JSON file remains
