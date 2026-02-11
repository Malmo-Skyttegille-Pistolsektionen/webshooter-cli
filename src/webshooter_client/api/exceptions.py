"""Custom exceptions for WebShooter API interactions."""


class WebShooterAPIError(Exception):
    """Base exception for WebShooter API errors."""

    def __init__(self, message: str, url: str = None, status_code: int = None):
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


class DataValidationError(WebShooterAPIError):
    """Raised when API response data fails validation."""

    def __init__(self, message: str, field: str = None, data: dict = None):
        self.field = field
        self.data = data
        super().__init__(message)
