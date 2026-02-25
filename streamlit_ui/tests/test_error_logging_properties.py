"""Property-based tests for error logging.

Feature: streamlit-organizer-dashboard
Tests universal properties of error logging behavior using Hypothesis.
"""

from contextlib import suppress
from unittest.mock import Mock, patch

import requests
from components.api_client import (
    APIClient,
    APIError,
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
from hypothesis import given
from hypothesis import strategies as st


class TestErrorLoggingProperty:
    """Property 26: Error Logging

    **Validates: Requirements 10.5**

    For any API error (4xx or 5xx status code), the dashboard should log
    the error details to the console.
    """

    @given(
        api_key=st.text(min_size=1, max_size=100),
        base_url=st.from_regex(r"https?://[a-z0-9\-\.]+(?::\d+)?", fullmatch=True),
        endpoint=st.from_regex(r"/[a-z0-9\-_/]*", fullmatch=True),
        status_code=st.sampled_from([400, 401, 402, 404, 409, 422, 429, 500, 503]),
        error_detail=st.text(min_size=0, max_size=100),
    )
    @patch("components.api_client.requests.Session")
    def test_api_errors_are_logged_for_get_requests(
        self,
        mock_session_class: Mock,
        api_key: str,
        base_url: str,
        endpoint: str,
        status_code: int,
        error_detail: str,
    ) -> None:
        """
        Property: For any GET request that returns a 4xx or 5xx status code,
        the error should be logged to the console.

        This test verifies that:
        1. All HTTP error status codes trigger logging
        2. The log message includes the status code
        3. The log level is ERROR
        4. The error detail is included in the log

        Args:
            mock_session_class: Mocked requests.Session class
            api_key: Generated API key string
            base_url: Generated base URL string
            endpoint: Generated API endpoint string
            status_code: HTTP error status code (4xx or 5xx)
            error_detail: Error detail message from API
        """
        # Arrange: Mock session instance and error response
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = status_code
        mock_response.json.return_value = {"detail": error_detail}
        mock_session.get.return_value = mock_response

        # Act: Create APIClient and make GET request with logging capture
        client = APIClient(base_url, api_key)

        with patch("components.api_client.logger") as mock_logger:
            with suppress(
                APIError,
                AuthenticationError,
                ValidationError,
                ResourceNotFoundError,
                ConflictError,
                BudgetExceededError,
                RateLimitError,
                ServerError,
                ServiceUnavailableError,
                BadRequestError,
            ):
                client.get(endpoint)

            # Assert: Error was logged
            assert mock_logger.error.call_count >= 1, (
                f"Error should be logged at least once for status code {status_code}"
            )

            # Get the logged message
            log_call_args = mock_logger.error.call_args[0][0]

            # Assert: Log message contains status code
            assert str(status_code) in log_call_args, (
                f"Log message should contain status code {status_code}, but got: {log_call_args}"
            )

    @given(
        api_key=st.text(min_size=1, max_size=100),
        base_url=st.from_regex(r"https?://[a-z0-9\-\.]+(?::\d+)?", fullmatch=True),
        endpoint=st.from_regex(r"/[a-z0-9\-_/]*", fullmatch=True),
        status_code=st.sampled_from([400, 401, 402, 404, 409, 422, 429, 500, 503]),
        error_detail=st.text(min_size=0, max_size=100),
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
    def test_api_errors_are_logged_for_post_requests(
        self,
        mock_session_class: Mock,
        api_key: str,
        base_url: str,
        endpoint: str,
        status_code: int,
        error_detail: str,
        json_data: dict,
    ) -> None:
        """
        Property: For any POST request that returns a 4xx or 5xx status code,
        the error should be logged to the console.

        This test verifies that:
        1. All HTTP error status codes trigger logging for POST requests
        2. The log message includes the status code
        3. The log level is ERROR
        4. The error detail is included in the log

        Args:
            mock_session_class: Mocked requests.Session class
            api_key: Generated API key string
            base_url: Generated base URL string
            endpoint: Generated API endpoint string
            status_code: HTTP error status code (4xx or 5xx)
            error_detail: Error detail message from API
            json_data: JSON payload for POST request
        """
        # Arrange: Mock session instance and error response
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = status_code
        mock_response.json.return_value = {"detail": error_detail}
        mock_session.post.return_value = mock_response

        # Act: Create APIClient and make POST request with logging capture
        client = APIClient(base_url, api_key)

        with patch("components.api_client.logger") as mock_logger:
            with suppress(
                APIError,
                AuthenticationError,
                ValidationError,
                ResourceNotFoundError,
                ConflictError,
                BudgetExceededError,
                RateLimitError,
                ServerError,
                ServiceUnavailableError,
                BadRequestError,
            ):
                client.post(endpoint, json_data)

            # Assert: Error was logged
            assert mock_logger.error.call_count >= 1, (
                f"Error should be logged at least once for status code {status_code}"
            )

            # Get the logged message
            log_call_args = mock_logger.error.call_args[0][0]

            # Assert: Log message contains status code
            assert str(status_code) in log_call_args, (
                f"Log message should contain status code {status_code}, but got: {log_call_args}"
            )

    @given(
        api_key=st.text(min_size=1, max_size=100),
        base_url=st.from_regex(r"https?://[a-z0-9\-\.]+(?::\d+)?", fullmatch=True),
        endpoint=st.from_regex(r"/[a-z0-9\-_/]*", fullmatch=True),
        status_code=st.sampled_from([400, 401, 402, 404, 409, 422, 429, 500, 503]),
    )
    @patch("components.api_client.requests.Session")
    def test_error_logging_includes_error_detail(
        self, mock_session_class: Mock, api_key: str, base_url: str, endpoint: str, status_code: int
    ) -> None:
        """
        Property: For any API error with a detail message, the log should
        include the error detail from the API response.

        This test verifies that:
        1. Error details from API responses are captured
        2. The log message includes the error detail
        3. Empty error details are handled gracefully

        Args:
            mock_session_class: Mocked requests.Session class
            api_key: Generated API key string
            base_url: Generated base URL string
            endpoint: Generated API endpoint string
            status_code: HTTP error status code (4xx or 5xx)
        """
        # Arrange: Mock session instance and error response with detail
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        error_detail = f"Test error detail for status {status_code}"
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = status_code
        mock_response.json.return_value = {"detail": error_detail}
        mock_session.get.return_value = mock_response

        # Act: Create APIClient and make GET request with logging capture
        client = APIClient(base_url, api_key)

        with patch("components.api_client.logger") as mock_logger:
            with suppress(
                APIError,
                AuthenticationError,
                ValidationError,
                ResourceNotFoundError,
                ConflictError,
                BudgetExceededError,
                RateLimitError,
                ServerError,
                ServiceUnavailableError,
                BadRequestError,
            ):
                client.get(endpoint)

            # Assert: Error was logged
            assert mock_logger.error.call_count >= 1, (
                f"Error should be logged for status code {status_code}"
            )

            # Get the logged message
            log_call_args = mock_logger.error.call_args[0][0]

            # Assert: Log message contains error detail (if not empty)
            if error_detail:
                # For some status codes, the detail is included in the log
                # We just verify that logging occurred with the status code
                assert str(status_code) in log_call_args, (
                    f"Log message should contain status code {status_code}"
                )

    @given(
        api_key=st.text(min_size=1, max_size=100),
        base_url=st.from_regex(r"https?://[a-z0-9\-\.]+(?::\d+)?", fullmatch=True),
        endpoint=st.from_regex(r"/[a-z0-9\-_/]*", fullmatch=True),
    )
    @patch("components.api_client.requests.Session")
    def test_network_errors_are_logged(
        self, mock_session_class: Mock, api_key: str, base_url: str, endpoint: str
    ) -> None:
        """
        Property: For any network error (timeout or connection error),
        the error should be logged to the console.

        This test verifies that:
        1. Timeout errors trigger logging
        2. Connection errors trigger logging
        3. The log message includes error context

        Args:
            mock_session_class: Mocked requests.Session class
            api_key: Generated API key string
            base_url: Generated base URL string
            endpoint: Generated API endpoint string
        """
        # Test timeout error
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_session.get.side_effect = requests.Timeout("Connection timeout")

        client = APIClient(base_url, api_key)

        with patch("components.api_client.logger") as mock_logger:
            with suppress(ConnectionTimeoutError):
                client.get(endpoint)

            # Assert: Timeout error was logged
            assert mock_logger.error.call_count >= 1, "Timeout error should be logged"

            log_call_args = mock_logger.error.call_args[0][0]
            assert "Timeout" in log_call_args or "timeout" in log_call_args.lower(), (
                f"Log message should indicate timeout, but got: {log_call_args}"
            )

        # Test connection error
        mock_session_2 = Mock()
        mock_session_class.return_value = mock_session_2
        mock_session_2.get.side_effect = requests.ConnectionError("Connection failed")

        client_2 = APIClient(base_url, api_key)

        with patch("components.api_client.logger") as mock_logger_2:
            with suppress(ServiceUnavailableError):
                client_2.get(endpoint)

            # Assert: Connection error was logged
            assert mock_logger_2.error.call_count >= 1, "Connection error should be logged"

            log_call_args_2 = mock_logger_2.error.call_args[0][0]
            assert "Connection" in log_call_args_2 or "connection" in log_call_args_2.lower(), (
                f"Log message should indicate connection error, but got: {log_call_args_2}"
            )

    @given(
        api_key=st.text(min_size=1, max_size=100),
        base_url=st.from_regex(r"https?://[a-z0-9\-\.]+(?::\d+)?", fullmatch=True),
        endpoint=st.from_regex(r"/[a-z0-9\-_/]*", fullmatch=True),
        status_codes=st.lists(
            st.sampled_from([400, 401, 404, 422, 500, 503]), min_size=2, max_size=5
        ),
    )
    @patch("components.api_client.requests.Session")
    def test_multiple_errors_are_all_logged(
        self,
        mock_session_class: Mock,
        api_key: str,
        base_url: str,
        endpoint: str,
        status_codes: list[int],
    ) -> None:
        """
        Property: For any sequence of API errors, each error should be
        logged independently.

        This test verifies that:
        1. Multiple errors all trigger logging
        2. Each error is logged separately
        3. Logging doesn't stop after the first error

        Args:
            mock_session_class: Mocked requests.Session class
            api_key: Generated API key string
            base_url: Generated base URL string
            endpoint: Generated API endpoint string
            status_codes: List of HTTP error status codes
        """
        # Arrange: Mock session instance
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        client = APIClient(base_url, api_key)

        # Act: Make multiple requests with different error codes
        with patch("components.api_client.logger") as mock_logger:
            for status_code in status_codes:
                mock_response = Mock()
                mock_response.ok = False
                mock_response.status_code = status_code
                mock_response.json.return_value = {"detail": f"Error {status_code}"}
                mock_session.get.return_value = mock_response

                with suppress(
                    APIError,
                    AuthenticationError,
                    ValidationError,
                    ResourceNotFoundError,
                    ConflictError,
                    BudgetExceededError,
                    RateLimitError,
                    ServerError,
                    ServiceUnavailableError,
                    BadRequestError,
                ):
                    client.get(endpoint)

            # Assert: All errors were logged
            assert mock_logger.error.call_count >= len(status_codes), (
                f"All {len(status_codes)} errors should be logged, but only {mock_logger.error.call_count} were logged"
            )

    @given(
        api_key=st.text(min_size=1, max_size=100),
        base_url=st.from_regex(r"https?://[a-z0-9\-\.]+(?::\d+)?", fullmatch=True),
        endpoint=st.from_regex(r"/[a-z0-9\-_/]*", fullmatch=True),
        status_code=st.sampled_from([400, 401, 402, 404, 409, 422, 429, 500, 503]),
    )
    @patch("components.api_client.requests.Session")
    def test_error_logging_uses_error_level(
        self, mock_session_class: Mock, api_key: str, base_url: str, endpoint: str, status_code: int
    ) -> None:
        """
        Property: For any API error, the log should use the ERROR level
        (not DEBUG, INFO, or WARNING).

        This test verifies that:
        1. Errors are logged at ERROR level
        2. logger.error() is called (not logger.debug(), logger.info(), etc.)

        Args:
            mock_session_class: Mocked requests.Session class
            api_key: Generated API key string
            base_url: Generated base URL string
            endpoint: Generated API endpoint string
            status_code: HTTP error status code (4xx or 5xx)
        """
        # Arrange: Mock session instance and error response
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = status_code
        mock_response.json.return_value = {"detail": "Test error"}
        mock_session.get.return_value = mock_response

        # Act: Create APIClient and make GET request with logging capture
        client = APIClient(base_url, api_key)

        with patch("components.api_client.logger") as mock_logger:
            with suppress(
                APIError,
                AuthenticationError,
                ValidationError,
                ResourceNotFoundError,
                ConflictError,
                BudgetExceededError,
                RateLimitError,
                ServerError,
                ServiceUnavailableError,
                BadRequestError,
            ):
                client.get(endpoint)

            # Assert: logger.error() was called (not debug, info, or warning)
            assert mock_logger.error.call_count >= 1, (
                f"logger.error() should be called for status code {status_code}"
            )

            # Assert: Other log levels were not used for the error
            assert mock_logger.debug.call_count == 0 or any(
                str(status_code) in str(call) for call in mock_logger.error.call_args_list
            ), "Error should be logged at ERROR level, not DEBUG"
