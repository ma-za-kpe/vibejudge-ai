"""Unit tests for authentication component."""

from unittest.mock import Mock, patch

import requests
from components.auth import is_authenticated, logout, validate_api_key


class TestValidateAPIKey:
    """Test API key validation function."""

    @patch("components.auth.requests.get")
    def test_validate_api_key_success_returns_true(self, mock_get):
        """Test that valid API key returns True."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = validate_api_key("valid_key", "http://test-api.com")

        assert result is True
        mock_get.assert_called_once_with(
            "http://test-api.com/hackathons", headers={"X-API-Key": "valid_key"}, timeout=5
        )

    @patch("components.auth.requests.get")
    def test_validate_api_key_invalid_returns_false(self, mock_get):
        """Test that invalid API key returns False."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        result = validate_api_key("invalid_key", "http://test-api.com")

        assert result is False

    @patch("components.auth.requests.get")
    def test_validate_api_key_strips_trailing_slash(self, mock_get):
        """Test that base URL trailing slash is stripped."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        validate_api_key("test_key", "http://test-api.com/")

        mock_get.assert_called_once_with(
            "http://test-api.com/hackathons", headers={"X-API-Key": "test_key"}, timeout=5
        )

    @patch("components.auth.requests.get")
    def test_validate_api_key_timeout_returns_false(self, mock_get):
        """Test that timeout returns False."""
        mock_get.side_effect = requests.Timeout()

        result = validate_api_key("test_key", "http://test-api.com")

        assert result is False

    @patch("components.auth.requests.get")
    def test_validate_api_key_connection_error_returns_false(self, mock_get):
        """Test that connection error returns False."""
        mock_get.side_effect = requests.ConnectionError()

        result = validate_api_key("test_key", "http://test-api.com")

        assert result is False

    @patch("components.auth.requests.get")
    def test_validate_api_key_unexpected_error_returns_false(self, mock_get):
        """Test that unexpected error returns False."""
        mock_get.side_effect = Exception("Unexpected error")

        result = validate_api_key("test_key", "http://test-api.com")

        assert result is False


class TestIsAuthenticated:
    """Test is_authenticated function."""

    @patch("components.auth.st")
    def test_is_authenticated_with_api_key_returns_true(self, mock_st):
        """Test that is_authenticated returns True when API key exists."""
        mock_st.session_state = {"api_key": "test_key_123"}  # pragma: allowlist secret

        result = is_authenticated()

        assert result is True

    @patch("components.auth.st")
    def test_is_authenticated_without_api_key_returns_false(self, mock_st):
        """Test that is_authenticated returns False when API key doesn't exist."""
        mock_st.session_state = {}

        result = is_authenticated()

        assert result is False

    @patch("components.auth.st")
    def test_is_authenticated_with_none_api_key_returns_false(self, mock_st):
        """Test that is_authenticated returns False when API key is None."""
        mock_st.session_state = {"api_key": None}

        result = is_authenticated()

        assert result is False


class TestLogout:
    """Test logout function."""

    @patch("components.auth.st")
    def test_logout_clears_session_state(self, mock_st):
        """Test that logout clears all session state."""
        # Create a mock session_state with a mock clear method
        mock_session_state = Mock()
        mock_st.session_state = mock_session_state

        logout()

        mock_session_state.clear.assert_called_once()
