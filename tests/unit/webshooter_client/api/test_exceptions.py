"""Tests for API exceptions."""

from webshooter_client.api.exceptions import (
    WebShooterAPIError,
    APIConnectionError,
    APITimeoutError,
    APIServerError,
    APIClientError,
    APIRetryExhaustedError,
    DataValidationError,
)


class TestWebShooterAPIError:
    """Tests for base WebShooterAPIError."""

    def test_base_error_with_message(self):
        """Base error can be created with just a message."""
        error = WebShooterAPIError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.url is None
        assert error.status_code is None

    def test_base_error_with_url_and_status(self):
        """Base error can store URL and status code."""
        error = WebShooterAPIError("Error", url="https://example.com", status_code=500)
        assert error.url == "https://example.com"
        assert error.status_code == 500


class TestAPIConnectionError:
    """Tests for APIConnectionError."""

    def test_connection_error_creation(self):
        """APIConnectionError can be created and provides context."""
        error = APIConnectionError("Failed to connect", url="https://webshooter.se")
        assert "Failed to connect" in str(error)
        assert error.url == "https://webshooter.se"
        assert isinstance(error, WebShooterAPIError)


class TestAPITimeoutError:
    """Tests for APITimeoutError."""

    def test_timeout_error_creation(self):
        """APITimeoutError can be created with timeout context."""
        error = APITimeoutError("Request timed out after 30s", url="https://webshooter.se")
        assert "timed out" in str(error)
        assert isinstance(error, WebShooterAPIError)


class TestAPIServerError:
    """Tests for APIServerError."""

    def test_server_error_with_status_code(self):
        """APIServerError stores server status codes."""
        error = APIServerError("Server error", url="https://webshooter.se", status_code=500)
        assert error.status_code == 500
        assert isinstance(error, WebShooterAPIError)


class TestAPIClientError:
    """Tests for APIClientError."""

    def test_client_error_with_status_code(self):
        """APIClientError stores client error status codes."""
        error = APIClientError("Bad request", url="https://webshooter.se", status_code=400)
        assert error.status_code == 400
        assert isinstance(error, WebShooterAPIError)


class TestAPIRetryExhaustedError:
    """Tests for APIRetryExhaustedError."""

    def test_retry_exhausted_with_context(self):
        """APIRetryExhaustedError provides retry context."""
        error = APIRetryExhaustedError(
            "Failed after 3 retries", url="https://webshooter.se", retries=3
        )
        assert "3 retries" in str(error)
        assert error.url == "https://webshooter.se"
        assert isinstance(error, WebShooterAPIError)


class TestDataValidationError:
    """Tests for DataValidationError."""

    def test_validation_error_creation(self):
        """DataValidationError can describe what field is missing."""
        error = DataValidationError("Missing required field 'placement'")
        assert "placement" in str(error)
        assert isinstance(error, WebShooterAPIError)

    def test_validation_error_with_multiple_fields(self):
        """DataValidationError can list multiple missing fields."""
        error = DataValidationError("Missing required fields: id, name, date")
        assert "id" in str(error)
        assert "name" in str(error)
        assert "date" in str(error)
