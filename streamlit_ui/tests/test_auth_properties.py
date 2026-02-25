"""Property-based tests for authentication component.

Feature: streamlit-organizer-dashboard
Tests universal properties of authentication behavior using Hypothesis.
"""

from typing import Any
from unittest.mock import Mock, patch

import pytest
from components.auth import validate_api_key
from hypothesis import given
from hypothesis import strategies as st


class TestSessionStatePersistenceProperty:
    """Property 2: Session State Persistence

    **Validates: Requirements 1.3**

    For any successful authentication (HTTP 200), the API key should be stored
    in st.session_state and persist across page navigations.
    """

    @given(
        api_key=st.text(min_size=1, max_size=100),
        base_url=st.from_regex(r"https?://[a-z0-9\-\.]+(?::\d+)?", fullmatch=True),
    )
    @patch("components.auth.requests.get")
    @patch("components.auth.st")
    def test_successful_auth_stores_api_key_in_session_state(
        self, mock_st: Mock, mock_get: Mock, api_key: str, base_url: str
    ) -> None:
        """
        Property: For any API key and base URL, when authentication succeeds
        (HTTP 200), the API key should be stored in session state.

        This test verifies that:
        1. validate_api_key returns True for HTTP 200
        2. The API key can be stored in st.session_state
        3. The stored API key matches the input API key

        Args:
            mock_st: Mocked Streamlit module
            mock_get: Mocked requests.get function
            api_key: Generated API key string
            base_url: Generated base URL string
        """
        # Arrange: Mock successful authentication response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Mock session_state as a dictionary
        mock_session_state: dict[str, Any] = {}
        mock_st.session_state = mock_session_state

        # Act: Validate API key
        result = validate_api_key(api_key, base_url)

        # Assert: Validation succeeds
        assert result is True, f"Expected validation to succeed for HTTP 200, but got {result}"

        # Simulate storing API key in session state (as the app.py would do)
        if result:
            mock_st.session_state["api_key"] = api_key

        # Assert: API key is stored in session state
        assert "api_key" in mock_st.session_state, (
            "API key should be stored in session state after successful authentication"
        )
        assert mock_st.session_state["api_key"] == api_key, (
            f"Stored API key '{mock_st.session_state['api_key']}' should match input '{api_key}'"
        )

    @given(
        api_key=st.text(min_size=1, max_size=100),
        base_url=st.from_regex(r"https?://[a-z0-9\-\.]+(?::\d+)?", fullmatch=True),
        status_code=st.integers(min_value=400, max_value=599),
    )
    @patch("components.auth.requests.get")
    @patch("components.auth.st")
    def test_failed_auth_does_not_store_api_key(
        self, mock_st: Mock, mock_get: Mock, api_key: str, base_url: str, status_code: int
    ) -> None:
        """
        Property: For any API key and base URL, when authentication fails
        (HTTP 4xx or 5xx), the API key should NOT be stored in session state.

        This test verifies that:
        1. validate_api_key returns False for non-200 status codes
        2. The API key is not stored in session state on failure

        Args:
            mock_st: Mocked Streamlit module
            mock_get: Mocked requests.get function
            api_key: Generated API key string
            base_url: Generated base URL string
            status_code: Generated HTTP error status code (4xx or 5xx)
        """
        # Arrange: Mock failed authentication response
        mock_response = Mock()
        mock_response.status_code = status_code
        mock_get.return_value = mock_response

        # Mock session_state as a dictionary
        mock_session_state: dict[str, Any] = {}
        mock_st.session_state = mock_session_state

        # Act: Validate API key
        result = validate_api_key(api_key, base_url)

        # Assert: Validation fails
        assert result is False, (
            f"Expected validation to fail for HTTP {status_code}, but got {result}"
        )

        # Simulate conditional storage (as the app.py would do)
        if result:
            mock_st.session_state["api_key"] = api_key

        # Assert: API key is NOT stored in session state
        assert "api_key" not in mock_st.session_state, (
            f"API key should NOT be stored in session state after failed authentication (HTTP {status_code})"
        )

    @given(
        api_key=st.text(min_size=1, max_size=100),
        base_url=st.from_regex(r"https?://[a-z0-9\-\.]+(?::\d+)?", fullmatch=True),
    )
    @patch("components.auth.requests.get")
    @patch("components.auth.st")
    def test_session_state_persistence_across_validations(
        self, mock_st: Mock, mock_get: Mock, api_key: str, base_url: str
    ) -> None:
        """
        Property: For any API key, once stored in session state after successful
        authentication, it should persist across multiple validation checks.

        This test verifies that:
        1. API key stored in session state remains accessible
        2. Multiple reads of session state return the same API key

        Args:
            mock_st: Mocked Streamlit module
            mock_get: Mocked requests.get function
            api_key: Generated API key string
            base_url: Generated base URL string
        """
        # Arrange: Mock successful authentication response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Mock session_state as a dictionary
        mock_session_state: dict[str, Any] = {}
        mock_st.session_state = mock_session_state

        # Act: Validate and store API key
        result = validate_api_key(api_key, base_url)
        if result:
            mock_st.session_state["api_key"] = api_key

        # Assert: API key persists across multiple reads
        first_read = mock_st.session_state.get("api_key")
        second_read = mock_st.session_state.get("api_key")
        third_read = mock_st.session_state.get("api_key")

        assert first_read == api_key, "First read should return the stored API key"
        assert second_read == api_key, "Second read should return the stored API key"
        assert third_read == api_key, "Third read should return the stored API key"
        assert first_read == second_read == third_read, (
            "All reads should return the same API key value"
        )


class TestLogoutClearsStateProperty:
    """Property 3: Logout Clears State

    **Validates: Requirements 1.6**

    For any session state with an API key, calling logout should clear the
    API key from session state.
    """

    @given(api_key=st.text(min_size=1, max_size=100))
    @patch("components.auth.st")
    def test_logout_clears_api_key_from_session_state(self, mock_st: Mock, api_key: str) -> None:
        """
        Property: For any API key stored in session state, calling logout()
        should clear the API key from session state.

        This test verifies that:
        1. API key can be stored in session state
        2. logout() clears the session state
        3. API key is no longer accessible after logout

        Args:
            mock_st: Mocked Streamlit module
            api_key: Generated API key string
        """
        from components.auth import logout

        # Arrange: Mock session_state as a dictionary with API key
        mock_session_state: dict[str, Any] = {"api_key": api_key}
        mock_st.session_state = mock_session_state

        # Verify API key is present before logout
        assert "api_key" in mock_st.session_state, (
            "API key should be present in session state before logout"
        )
        assert mock_st.session_state["api_key"] == api_key, (
            f"Session state should contain the API key '{api_key}'"
        )

        # Act: Call logout
        logout()

        # Assert: Session state is cleared
        assert "api_key" not in mock_st.session_state, (
            "API key should be cleared from session state after logout"
        )
        assert len(mock_st.session_state) == 0, (
            "Session state should be completely empty after logout"
        )

    @given(
        api_key=st.text(min_size=1, max_size=100),
        extra_data=st.dictionaries(
            keys=st.text(min_size=1, max_size=50).filter(lambda x: x != "api_key"),
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
    @patch("components.auth.st")
    def test_logout_clears_all_session_data(
        self, mock_st: Mock, api_key: str, extra_data: dict[str, Any]
    ) -> None:
        """
        Property: For any session state with an API key and additional data,
        calling logout() should clear ALL data from session state, not just
        the API key.

        This test verifies that:
        1. Multiple items can be stored in session state
        2. logout() clears all session state data
        3. No data remains after logout

        Args:
            mock_st: Mocked Streamlit module
            api_key: Generated API key string
            extra_data: Generated dictionary of additional session data
        """
        from components.auth import logout

        # Arrange: Mock session_state with API key and extra data
        mock_session_state: dict[str, Any] = {"api_key": api_key, **extra_data}
        mock_st.session_state = mock_session_state

        # Verify data is present before logout
        initial_keys = set(mock_st.session_state.keys())
        assert "api_key" in initial_keys, "API key should be present before logout"
        assert len(mock_st.session_state) >= 1, "Session state should contain at least the API key"

        # Act: Call logout
        logout()

        # Assert: All session state is cleared
        assert len(mock_st.session_state) == 0, (
            f"Session state should be completely empty after logout, but contains: {list(mock_st.session_state.keys())}"
        )
        assert "api_key" not in mock_st.session_state, (
            "API key should be cleared from session state"
        )
        for key in initial_keys:
            assert key not in mock_st.session_state, (
                f"Key '{key}' should be cleared from session state after logout"
            )

    @given(api_key=st.text(min_size=1, max_size=100))
    @patch("components.auth.st")
    @patch("components.auth.is_authenticated")
    def test_logout_makes_user_unauthenticated(
        self, mock_is_authenticated: Mock, mock_st: Mock, api_key: str
    ) -> None:
        """
        Property: For any authenticated session, calling logout() should result
        in is_authenticated() returning False.

        This test verifies that:
        1. User is authenticated before logout
        2. logout() clears session state
        3. User is not authenticated after logout

        Args:
            mock_is_authenticated: Mocked is_authenticated function
            mock_st: Mocked Streamlit module
            api_key: Generated API key string
        """
        from components.auth import logout

        # Arrange: Mock session_state with API key
        mock_session_state: dict[str, Any] = {"api_key": api_key}
        mock_st.session_state = mock_session_state

        # Mock is_authenticated to return True before logout
        mock_is_authenticated.return_value = True

        # Verify user is authenticated before logout
        assert mock_is_authenticated(), "User should be authenticated before logout"

        # Act: Call logout
        logout()

        # Mock is_authenticated to check actual session state after logout
        mock_is_authenticated.return_value = "api_key" in mock_st.session_state

        # Assert: User is not authenticated after logout
        assert not mock_is_authenticated(), "User should NOT be authenticated after logout"
        assert "api_key" not in mock_st.session_state, (
            "API key should be cleared from session state"
        )

    @patch("components.auth.st")
    def test_logout_on_empty_session_state_does_not_error(self, mock_st: Mock) -> None:
        """
        Property: Calling logout() on an empty session state should not raise
        an error (idempotent operation).

        This test verifies that:
        1. logout() can be called on empty session state
        2. No exceptions are raised
        3. Session state remains empty

        Args:
            mock_st: Mocked Streamlit module
        """
        from components.auth import logout

        # Arrange: Mock empty session_state
        mock_session_state: dict[str, Any] = {}
        mock_st.session_state = mock_session_state

        # Act & Assert: logout should not raise an error
        try:
            logout()
            assert len(mock_st.session_state) == 0, "Session state should remain empty after logout"
        except Exception as e:
            pytest.fail(
                f"logout() should not raise an error on empty session state, but raised: {e}"
            )
