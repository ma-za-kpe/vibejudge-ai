"""Unit tests for API client component."""

from unittest.mock import Mock, patch

import pytest
import requests
from components.api_client import (
    APIClient,
    AuthenticationError,
    BadRequestError,
    BudgetExceededError,
    ConflictError,
    ConnectionTimeoutError,
    RateLimitError,
    ResourceNotFoundError,
    ServerError,
    ServiceUnavailableError,
    ValidationError,
)


@pytest.fixture
def api_client():
    """Create an API client instance for testing."""
    return APIClient("http://test-api.com", "test_key_123", timeout=5)


class TestAPIClientInitialization:
    """Test API client initialization."""

    def test_init_sets_base_url(self):
        """Test that initialization sets base URL correctly."""
        client = APIClient("http://test-api.com", "test_key")
        assert client.base_url == "http://test-api.com"

    def test_init_strips_trailing_slash(self):
        """Test that initialization strips trailing slash from base URL."""
        client = APIClient("http://test-api.com/", "test_key")
        assert client.base_url == "http://test-api.com"

    def test_init_sets_api_key(self):
        """Test that initialization sets API key correctly."""
        client = APIClient("http://test-api.com", "test_key_123")
        assert client.api_key == "test_key_123"  # pragma: allowlist secret

    def test_init_sets_timeout(self):
        """Test that initialization sets timeout correctly."""
        client = APIClient("http://test-api.com", "test_key", timeout=15)
        assert client.timeout == 15

    def test_init_creates_session_with_api_key_header(self):
        """Test that initialization creates session with X-API-Key header."""
        client = APIClient("http://test-api.com", "test_key_123")
        assert "X-API-Key" in client.session.headers
        assert client.session.headers["X-API-Key"] == "test_key_123"


class TestAPIClientErrorHandling:
    """Test API client error handling for different HTTP status codes."""

    def test_handle_error_400_raises_bad_request_error(self, api_client):
        """Test that 400 status code raises BadRequestError."""
        response = Mock()
        response.status_code = 400
        response.json.return_value = {"detail": "Bad request"}

        with pytest.raises(BadRequestError, match="Bad request"):
            api_client.handle_error(response)

    def test_handle_error_401_raises_authentication_error(self, api_client):
        """Test that 401 status code raises AuthenticationError."""
        response = Mock()
        response.status_code = 401
        response.json.return_value = {"detail": "Invalid API key"}

        with pytest.raises(AuthenticationError, match="Invalid API key"):
            api_client.handle_error(response)

    def test_handle_error_402_raises_budget_exceeded_error(self, api_client):
        """Test that 402 status code raises BudgetExceededError."""
        response = Mock()
        response.status_code = 402
        response.json.return_value = {"detail": "Budget exceeded"}

        with pytest.raises(BudgetExceededError, match="Budget limit exceeded"):
            api_client.handle_error(response)

    def test_handle_error_404_raises_resource_not_found_error(self, api_client):
        """Test that 404 status code raises ResourceNotFoundError."""
        response = Mock()
        response.status_code = 404
        response.json.return_value = {"detail": "Not found"}

        with pytest.raises(ResourceNotFoundError, match="Resource not found"):
            api_client.handle_error(response)

    def test_handle_error_409_raises_conflict_error(self, api_client):
        """Test that 409 status code raises ConflictError."""
        response = Mock()
        response.status_code = 409
        response.json.return_value = {"detail": "Analysis already running"}

        with pytest.raises(ConflictError, match="Conflict: Analysis already running"):
            api_client.handle_error(response)

    def test_handle_error_422_raises_validation_error(self, api_client):
        """Test that 422 status code raises ValidationError."""
        response = Mock()
        response.status_code = 422
        response.json.return_value = {"detail": "Validation failed"}

        with pytest.raises(ValidationError, match="Validation error: Validation failed"):
            api_client.handle_error(response)

    def test_handle_error_429_raises_rate_limit_error(self, api_client):
        """Test that 429 status code raises RateLimitError."""
        response = Mock()
        response.status_code = 429
        response.json.return_value = {"detail": "Too many requests"}

        with pytest.raises(RateLimitError, match="Rate limit exceeded"):
            api_client.handle_error(response)

    def test_handle_error_500_raises_server_error(self, api_client):
        """Test that 500 status code raises ServerError."""
        response = Mock()
        response.status_code = 500
        response.json.return_value = {"detail": "Internal server error"}

        with pytest.raises(ServerError, match="Server error"):
            api_client.handle_error(response)

    def test_handle_error_503_raises_service_unavailable_error(self, api_client):
        """Test that 503 status code raises ServiceUnavailableError."""
        response = Mock()
        response.status_code = 503
        response.json.return_value = {"detail": "Service unavailable"}

        with pytest.raises(ServiceUnavailableError, match="Service unavailable"):
            api_client.handle_error(response)


class TestAPIClientGetMethod:
    """Test API client GET method."""

    @patch("components.api_client.requests.Session.get")
    def test_get_success_returns_json(self, mock_get, api_client):
        """Test that successful GET request returns JSON response."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"data": "test"}
        mock_get.return_value = mock_response

        result = api_client.get("/test")

        assert result == {"data": "test"}
        mock_get.assert_called_once_with("http://test-api.com/test", params=None, timeout=5)

    @patch("components.api_client.requests.Session.get")
    def test_get_with_params(self, mock_get, api_client):
        """Test that GET request includes query parameters."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"data": "test"}
        mock_get.return_value = mock_response

        api_client.get("/test", params={"key": "value"})

        mock_get.assert_called_once_with(
            "http://test-api.com/test", params={"key": "value"}, timeout=5
        )

    @patch("components.api_client.requests.Session.get")
    def test_get_timeout_raises_connection_timeout_error(self, mock_get, api_client):
        """Test that GET request timeout raises ConnectionTimeoutError."""
        mock_get.side_effect = requests.Timeout()

        with pytest.raises(ConnectionTimeoutError, match="Connection timeout"):
            api_client.get("/test")

    @patch("components.api_client.requests.Session.get")
    def test_get_connection_error_raises_service_unavailable_error(self, mock_get, api_client):
        """Test that GET connection error raises ServiceUnavailableError."""
        mock_get.side_effect = requests.ConnectionError()

        with pytest.raises(ServiceUnavailableError, match="Service unavailable"):
            api_client.get("/test")

    @patch("components.api_client.requests.Session.get")
    def test_get_http_error_calls_handle_error(self, mock_get, api_client):
        """Test that GET HTTP error calls handle_error method."""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 404
        mock_response.json.return_value = {"detail": "Not found"}
        mock_get.return_value = mock_response

        with pytest.raises(ResourceNotFoundError):
            api_client.get("/test")


class TestAPIClientPostMethod:
    """Test API client POST method."""

    @patch("components.api_client.requests.Session.post")
    def test_post_success_returns_json(self, mock_post, api_client):
        """Test that successful POST request returns JSON response."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"id": "123"}
        mock_post.return_value = mock_response

        result = api_client.post("/test", json={"name": "test"})

        assert result == {"id": "123"}
        mock_post.assert_called_once_with(
            "http://test-api.com/test", json={"name": "test"}, timeout=5
        )

    @patch("components.api_client.requests.Session.post")
    def test_post_timeout_raises_connection_timeout_error(self, mock_post, api_client):
        """Test that POST request timeout raises ConnectionTimeoutError."""
        mock_post.side_effect = requests.Timeout()

        with pytest.raises(ConnectionTimeoutError, match="Connection timeout"):
            api_client.post("/test", json={"name": "test"})

    @patch("components.api_client.requests.Session.post")
    def test_post_connection_error_raises_service_unavailable_error(self, mock_post, api_client):
        """Test that POST connection error raises ServiceUnavailableError."""
        mock_post.side_effect = requests.ConnectionError()

        with pytest.raises(ServiceUnavailableError, match="Service unavailable"):
            api_client.post("/test", json={"name": "test"})

    @patch("components.api_client.requests.Session.post")
    def test_post_http_error_calls_handle_error(self, mock_post, api_client):
        """Test that POST HTTP error calls handle_error method."""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 422
        mock_response.json.return_value = {"detail": "Validation error"}
        mock_post.return_value = mock_response

        with pytest.raises(ValidationError):
            api_client.post("/test", json={"name": "test"})


class TestAPIKeyHeaderInclusion:
    """Test that X-API-Key header is included in all requests."""

    @patch("components.api_client.requests.Session.get")
    def test_get_includes_api_key_header(self, mock_get, api_client):
        """Test that GET request includes X-API-Key header."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {}
        mock_get.return_value = mock_response

        api_client.get("/test")

        # Verify session has X-API-Key header
        assert "X-API-Key" in api_client.session.headers
        assert api_client.session.headers["X-API-Key"] == "test_key_123"

    @patch("components.api_client.requests.Session.post")
    def test_post_includes_api_key_header(self, mock_post, api_client):
        """Test that POST request includes X-API-Key header."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {}
        mock_post.return_value = mock_response

        api_client.post("/test", json={})

        # Verify session has X-API-Key header
        assert "X-API-Key" in api_client.session.headers
        assert api_client.session.headers["X-API-Key"] == "test_key_123"
