"""Custom exceptions for WebShooter API interactions."""

from typing import Optional


class WebShooterAPIError(Exception):
    """Base exception for WebShooter API errors."""

    def __init__(self, message: str, url: Optional[str] = None, status_code: Optional[int] = None):
        self.url = url
        self.status_code = status_code
        super().__init__(message)


class APIConnectionError(WebShooterAPIError):
    """Raised when unable to connect to the API."""

    pass


class APITimeoutError(WebShooterAPIError):
    """Raised when API request times out."""

    pass


class APIServerError(WebShooterAPIError):
    """Raised when API returns 5xx server error."""

    pass


class APIClientError(WebShooterAPIError):
    """Raised when API returns 4xx client error."""

    pass


class APIRetryExhaustedError(WebShooterAPIError):
    """Raised when max retries exceeded."""

    def __init__(self, message: str, url: str, retries: int):
        self.retries = retries
        super().__init__(message, url=url)


class OfflineCacheMissError(WebShooterAPIError):
    """Raised when offline mode is active and the requested data is not in the local cache.

    Offline mode guarantees that no network call is ever made. When a caller asks for
    data that has not been downloaded yet, this error tells them to run a sync first
    rather than silently reaching for the network.
    """

    def __init__(self, message: str, url: Optional[str] = None, cache_key: Optional[str] = None):
        self.cache_key = cache_key
        super().__init__(message, url=url)


class DataValidationError(WebShooterAPIError):
    """Raised when API response data fails validation."""

    def __init__(self, message: str, field: Optional[str] = None, data: Optional[dict] = None):
        self.field = field
        self.data = data
        super().__init__(message)
