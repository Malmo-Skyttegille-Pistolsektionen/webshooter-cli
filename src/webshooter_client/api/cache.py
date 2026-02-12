"""
Local file cache for API responses.

This module provides functions to cache API responses to local files
following XDG Base Directory specification. By default, caches are stored
in ~/.cache/webshooter/ on Linux/Unix systems.

Usage:
    # Enable cache mode
    ApplicationConfig(use_cache=True)

    # Cache will automatically be used by api_calls.py functions
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from webshooter_client.common.application_config import ApplicationConfig

logger = logging.getLogger(__name__)


def _get_default_cache_dir() -> Path:
    """
    Get the default cache directory following XDG Base Directory specification.

    Uses $XDG_CACHE_HOME/webshooter if set, otherwise falls back to
    ~/.cache/webshooter on Unix-like systems.

    Returns:
        Path object pointing to the default cache directory
    """
    # Check XDG_CACHE_HOME environment variable
    xdg_cache = os.getenv("XDG_CACHE_HOME")
    if xdg_cache:
        return Path(xdg_cache) / "webshooter"

    # Fall back to ~/.cache/webshooter (XDG default)
    return Path.home() / ".cache" / "webshooter"


def _get_cache_dir() -> Path:
    """
    Get the cache directory path.

    Returns the configured cache directory from ApplicationConfig, or the
    XDG-compliant default if not configured.

    Returns:
        Path object pointing to the cache directory
    """
    config = ApplicationConfig()
    if config.cache_dir:
        return Path(config.cache_dir).expanduser()
    return _get_default_cache_dir()


def _get_cache_path(cache_key: str) -> Path:
    """
    Get the full path for a cache file.

    Args:
        cache_key: Unique identifier for the cached data (e.g., 'competitions' or 'comp_123_results')

    Returns:
        Path object pointing to the cache file
    """
    return _get_cache_dir() / f"{cache_key}.json"


def load_from_cache(cache_key: str) -> Optional[Dict[str, Any]]:
    """
    Load data from cache if it exists.

    Args:
        cache_key: Unique identifier for the cached data

    Returns:
        Cached data as dict, or None if cache doesn't exist or cache is disabled
    """
    if not ApplicationConfig().use_cache:
        return None

    cache_path = _get_cache_path(cache_key)

    if not cache_path.exists():
        return None

    try:
        logger.debug(f"Loading from cache: {cache_path}")
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        logger.warning(f"Corrupted cache file: {cache_path}")
        return None
    except IOError as e:
        logger.warning(f"Error loading cache: {e}")
        return None


def save_to_cache(cache_key: str, data: Dict[str, Any]) -> None:
    """
    Save data to cache.

    Args:
        cache_key: Unique identifier for the cached data
        data: Data to cache (must be JSON-serializable)
    """
    if not ApplicationConfig().use_cache:
        return

    # Create cache directory if it doesn't exist
    cache_dir = _get_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)

    cache_path = _get_cache_path(cache_key)

    try:
        logger.debug(f"Saving to cache: {cache_path}")
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except (IOError, TypeError) as e:
        logger.warning(f"Error saving cache: {e}")


def get_cache_key_for_competitions() -> str:
    """Get cache key for competitions list."""
    return "competitions"


def get_cache_key_for_competition(competition_id: int) -> str:
    """Get cache key for a specific competition."""
    return f"competition_{competition_id}"


def get_cache_key_for_page(competition_id: int, page: str) -> str:
    """Get cache key for a competition page (results, signups, patrols, etc.)."""
    # Clean page name (remove query parameters)
    page_name = page.split("?")[0]
    return f"competition_{competition_id}_{page_name}"


def clear_cache() -> int:
    """
    Clear all cached files by deleting the cache directory.

    Returns:
        Number of cache files deleted
    """
    cache_dir = _get_cache_dir()
    if not cache_dir.exists():
        logger.debug(f"Cache directory does not exist: {cache_dir}")
        return 0

    # Count and delete all .json files in cache directory
    deleted_count = 0
    try:
        for cache_file in cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
                deleted_count += 1
                logger.debug(f"Deleted cache file: {cache_file}")
            except OSError as e:
                logger.warning(f"Failed to delete {cache_file}: {e}")

        logger.debug(f"Cleared {deleted_count} cache files from {cache_dir}")
        return deleted_count
    except OSError as e:
        logger.error(f"Error accessing cache directory {cache_dir}: {e}")
        return deleted_count
