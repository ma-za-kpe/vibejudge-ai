"""Property-based tests for API client component.

Feature: streamlit-organizer-dashboard
Tests universal properties of API client behavior using Hypothesis.
"""

from contextlib import suppress
from typing import Any
from unittest.mock import Mock, patch

from components.api_client import APIClient
from hypothesis import given
from hypothesis import strategies as st


class TestAPIKeyHeaderInclusionProperty:
    """Property 1: API Key Header Inclusion

    **Validates: Requirements 1.5**

    For any authenticated API request, the X-API-Key header should be present
    and contain the stored API key from session state.
    """

    @given(
        api_key=st.text(min_size=1, max_size=100),
        base_url=st.from_regex(r"https?://[a-z0-9\-\.]+(?::\d+)?", fullmatch=True),
        endpoint=st.from_regex(r"/[a-z0-9\-_/]*", fullmatch=True),
    )
    @patch("components.api_client.requests.Session")
    def test_get_request_includes_api_key_header(
        self, mock_session_class: Mock, api_key: str, base_url: str, endpoint: str
    ) -> None:
        """
        Property: For any GET request made through APIClient, the X-API-Key
        header should be present and contain the API key.

        This test verifies that:
        1. APIClient initializes session with X-API-Key header
        2. GET requests include the X-API-Key header
        3. The header value matches the provided API key

        Args:
            mock_session_class: Mocked requests.Session class
            api_key: Generated API key string
            base_url: Generated base URL string
            endpoint: Generated API endpoint string
        """
        # Arrange: Mock session instance and response
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"data": "test"}
        mock_session.get.return_value = mock_response

        # Act: Create APIClient and make GET request
        client = APIClient(base_url, api_key)
        client.get(endpoint)

        # Assert: Session headers were updated with X-API-Key
        mock_session.headers.update.assert_called_once()
        headers_update_call = mock_session.headers.update.call_args[0][0]

        assert "X-API-Key" in headers_update_call, (
            "X-API-Key header should be set in session headers"
        )
        assert headers_update_call["X-API-Key"] == api_key, (
            f"X-API-Key header should contain '{api_key}', but got '{headers_update_call.get('X-API-Key')}'"
        )

        # Assert: GET request was made
        assert mock_session.get.call_count == 1, (
            f"GET request should be made exactly once, but was called {mock_session.get.call_count} times"
        )

    @given(
        api_key=st.text(min_size=1, max_size=100),
        base_url=st.from_regex(r"https?://[a-z0-9\-\.]+(?::\d+)?", fullmatch=True),
        endpoint=st.from_regex(r"/[a-z0-9\-_/]*", fullmatch=True),
        json_data=st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.one_of(
                st.text(),
                st.integers(),
                st.floats(allow_nan=False, allow_infinity=False),
                st.booleans(),
            ),
            min_size=0,
            max_size=5,
        ),
    )
    @patch("components.api_client.requests.Session")
    def test_post_request_includes_api_key_header(
        self,
        mock_session_class: Mock,
        api_key: str,
        base_url: str,
        endpoint: str,
        json_data: dict[str, Any],
    ) -> None:
        """
        Property: For any POST request made through APIClient, the X-API-Key
        header should be present and contain the API key.

        This test verifies that:
        1. APIClient initializes session with X-API-Key header
        2. POST requests include the X-API-Key header
        3. The header value matches the provided API key

        Args:
            mock_session_class: Mocked requests.Session class
            api_key: Generated API key string
            base_url: Generated base URL string
            endpoint: Generated API endpoint string
            json_data: Generated JSON payload
        """
        # Arrange: Mock session instance and response
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"data": "test"}
        mock_session.post.return_value = mock_response

        # Act: Create APIClient and make POST request
        client = APIClient(base_url, api_key)
        client.post(endpoint, json_data)

        # Assert: Session headers were updated with X-API-Key
        mock_session.headers.update.assert_called_once()
        headers_update_call = mock_session.headers.update.call_args[0][0]

        assert "X-API-Key" in headers_update_call, (
            "X-API-Key header should be set in session headers"
        )
        assert headers_update_call["X-API-Key"] == api_key, (
            f"X-API-Key header should contain '{api_key}', but got '{headers_update_call.get('X-API-Key')}'"
        )

        # Assert: POST request was made
        assert mock_session.post.call_count == 1, (
            f"POST request should be made exactly once, but was called {mock_session.post.call_count} times"
        )

    @given(
        api_key=st.text(min_size=1, max_size=100),
        base_url=st.from_regex(r"https?://[a-z0-9\-\.]+(?::\d+)?", fullmatch=True),
        endpoints=st.lists(
            st.from_regex(r"/[a-z0-9\-_/]*", fullmatch=True), min_size=2, max_size=5
        ),
    )
    @patch("components.api_client.requests.Session")
    def test_multiple_requests_all_include_api_key_header(
        self, mock_session_class: Mock, api_key: str, base_url: str, endpoints: list[str]
    ) -> None:
        """
        Property: For any sequence of API requests made through the same
        APIClient instance, all requests should include the X-API-Key header.

        This test verifies that:
        1. The X-API-Key header is set once during initialization
        2. All subsequent requests use the same session with the header
        3. The header persists across multiple requests

        Args:
            mock_session_class: Mocked requests.Session class
            api_key: Generated API key string
            base_url: Generated base URL string
            endpoints: List of generated API endpoints
        """
        # Arrange: Mock session instance and response
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"data": "test"}
        mock_session.get.return_value = mock_response

        # Act: Create APIClient and make multiple GET requests
        client = APIClient(base_url, api_key)
        for endpoint in endpoints:
            client.get(endpoint)

        # Assert: Session headers were updated with X-API-Key exactly once
        assert mock_session.headers.update.call_count == 1, (
            f"Session headers should be updated exactly once during initialization, but was called {mock_session.headers.update.call_count} times"
        )

        headers_update_call = mock_session.headers.update.call_args[0][0]
        assert "X-API-Key" in headers_update_call, (
            "X-API-Key header should be set in session headers"
        )
        assert headers_update_call["X-API-Key"] == api_key, (
            f"X-API-Key header should contain '{api_key}', but got '{headers_update_call.get('X-API-Key')}'"
        )

        # Assert: All GET requests were made using the same session
        assert mock_session.get.call_count == len(endpoints), (
            f"GET should be called {len(endpoints)} times, but was called {mock_session.get.call_count} times"
        )

    @given(
        api_key=st.text(min_size=1, max_size=100),
        base_url=st.from_regex(r"https?://[a-z0-9\-\.]+(?::\d+)?", fullmatch=True),
        endpoint=st.from_regex(r"/[a-z0-9\-_/]*", fullmatch=True),
    )
    @patch("components.api_client.requests.Session")
    def test_api_key_header_is_set_during_initialization(
        self, mock_session_class: Mock, api_key: str, base_url: str, endpoint: str
    ) -> None:
        """
        Property: For any APIClient instance, the X-API-Key header should be
        set during initialization, before any requests are made.

        This test verifies that:
        1. The X-API-Key header is set immediately upon initialization
        2. The header is set before any API calls
        3. The header value is correct

        Args:
            mock_session_class: Mocked requests.Session class
            api_key: Generated API key string
            base_url: Generated base URL string
            endpoint: Generated API endpoint string
        """
        # Arrange: Mock session instance
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Act: Create APIClient (no requests made yet)
        APIClient(base_url, api_key)

        # Assert: Session headers were updated with X-API-Key during initialization
        mock_session.headers.update.assert_called_once()
        headers_update_call = mock_session.headers.update.call_args[0][0]

        assert "X-API-Key" in headers_update_call, (
            "X-API-Key header should be set during initialization"
        )
        assert headers_update_call["X-API-Key"] == api_key, (
            f"X-API-Key header should contain '{api_key}', but got '{headers_update_call.get('X-API-Key')}'"
        )

        # Assert: No requests have been made yet
        assert mock_session.get.call_count == 0, (
            "No GET requests should be made during initialization"
        )
        assert mock_session.post.call_count == 0, (
            "No POST requests should be made during initialization"
        )

    @given(
        api_key_1=st.text(min_size=1, max_size=100),
        api_key_2=st.text(min_size=1, max_size=100),
        base_url=st.from_regex(r"https?://[a-z0-9\-\.]+(?::\d+)?", fullmatch=True),
        endpoint=st.from_regex(r"/[a-z0-9\-_/]*", fullmatch=True),
    )
    @patch("components.api_client.requests.Session")
    def test_different_clients_use_different_api_keys(
        self, mock_session_class: Mock, api_key_1: str, api_key_2: str, base_url: str, endpoint: str
    ) -> None:
        """
        Property: For any two APIClient instances with different API keys,
        each should use its own API key in the X-API-Key header.

        This test verifies that:
        1. Each APIClient instance has its own session
        2. Each session has the correct X-API-Key header
        3. API keys don't interfere with each other

        Args:
            mock_session_class: Mocked requests.Session class
            api_key_1: First generated API key string
            api_key_2: Second generated API key string
            base_url: Generated base URL string
            endpoint: Generated API endpoint string
        """
        # Arrange: Mock two separate session instances
        mock_session_1 = Mock()
        mock_session_2 = Mock()
        mock_session_class.side_effect = [mock_session_1, mock_session_2]

        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"data": "test"}
        mock_session_1.get.return_value = mock_response
        mock_session_2.get.return_value = mock_response

        # Act: Create two APIClient instances with different API keys
        APIClient(base_url, api_key_1)
        APIClient(base_url, api_key_2)

        # Assert: Each session was updated with its own X-API-Key header
        assert mock_session_1.headers.update.call_count == 1, (
            "First session should have headers updated once"
        )
        assert mock_session_2.headers.update.call_count == 1, (
            "Second session should have headers updated once"
        )

        headers_1 = mock_session_1.headers.update.call_args[0][0]
        headers_2 = mock_session_2.headers.update.call_args[0][0]

        assert headers_1["X-API-Key"] == api_key_1, (
            f"First client should use API key '{api_key_1}', but got '{headers_1.get('X-API-Key')}'"
        )
        assert headers_2["X-API-Key"] == api_key_2, (
            f"Second client should use API key '{api_key_2}', but got '{headers_2.get('X-API-Key')}'"
        )

        # If API keys are different, verify they're not the same
        if api_key_1 != api_key_2:
            assert headers_1["X-API-Key"] != headers_2["X-API-Key"], (
                "Different clients should use different API keys"
            )

    @given(
        api_key=st.text(min_size=1, max_size=100),
        base_url=st.from_regex(r"https?://[a-z0-9\-\.]+(?::\d+)?", fullmatch=True),
        endpoint=st.from_regex(r"/[a-z0-9\-_/]*", fullmatch=True),
    )
    @patch("components.api_client.requests.Session")
    def test_api_key_header_persists_after_error_response(
        self, mock_session_class: Mock, api_key: str, base_url: str, endpoint: str
    ) -> None:
        """
        Property: For any APIClient instance, the X-API-Key header should
        persist even after receiving error responses from the API.

        This test verifies that:
        1. The X-API-Key header is set during initialization
        2. Error responses don't clear or modify the header
        3. Subsequent requests still include the header

        Args:
            mock_session_class: Mocked requests.Session class
            api_key: Generated API key string
            base_url: Generated base URL string
            endpoint: Generated API endpoint string
        """
        # Arrange: Mock session instance with error response
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # First request returns error
        mock_error_response = Mock()
        mock_error_response.ok = False
        mock_error_response.status_code = 500
        mock_error_response.json.return_value = {"detail": "Server error"}

        # Second request returns success
        mock_success_response = Mock()
        mock_success_response.ok = True
        mock_success_response.json.return_value = {"data": "test"}

        mock_session.get.side_effect = [mock_error_response, mock_success_response]

        # Act: Create APIClient and make requests
        client = APIClient(base_url, api_key)

        # First request (should raise error)
        with suppress(Exception):
            client.get(endpoint)

        # Second request (should succeed)
        client.get(endpoint)

        # Assert: Session headers were updated with X-API-Key exactly once
        assert mock_session.headers.update.call_count == 1, (
            f"Session headers should be updated exactly once, but was called {mock_session.headers.update.call_count} times"
        )

        headers_update_call = mock_session.headers.update.call_args[0][0]
        assert "X-API-Key" in headers_update_call, (
            "X-API-Key header should be set in session headers"
        )
        assert headers_update_call["X-API-Key"] == api_key, (
            f"X-API-Key header should contain '{api_key}', but got '{headers_update_call.get('X-API-Key')}'"
        )

        # Assert: Both GET requests were made using the same session
        assert mock_session.get.call_count == 2, (
            f"GET should be called 2 times, but was called {mock_session.get.call_count} times"
        )
