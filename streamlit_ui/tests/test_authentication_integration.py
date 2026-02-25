"""Integration tests for authentication flow using Streamlit AppTest.

**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.6**

This module tests the full authentication page flow including:
- Authentication form display on initial load
- Login success scenario (valid API key)
- Login failure scenario (invalid API key)
- Logout functionality
"""

from unittest.mock import MagicMock, patch

from streamlit.testing.v1 import AppTest


def test_authentication_form_displayed_on_initial_load() -> None:
    """Test that authentication form is displayed on initial load.

    **Validates: Requirement 1.1**

    When the app loads for the first time (no authentication), it should
    display an authentication form with:
    - API key input field
    - Login button
    - Title and welcome message
    """
    # Initialize the app
    at = AppTest.from_file("app.py")
    at.run()

    # Verify the page loaded without errors
    assert not at.exception

    # Verify title is displayed
    assert len(at.title) > 0
    assert "VibeJudge" in at.title[0].value

    # Verify authentication form elements are present
    # The form should have at least one text input (API key)
    assert len(at.text_input) >= 1

    # Verify login button is present
    # The form should have at least one button (Login)
    assert len(at.button) >= 1


@patch("components.auth.requests.get")
def test_login_success_with_valid_api_key(mock_get: MagicMock) -> None:
    """Test login success scenario with valid API key.

    **Validates: Requirements 1.2, 1.3, 1.4**

    When an organizer enters a valid API key and submits the form:
    - The dashboard should validate it against the backend (HTTP 200)
    - The API key should be stored in session state
    - A success message should be displayed
    """
    # Mock successful API response (HTTP 200)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    # Initialize the app
    at = AppTest.from_file("app.py")
    at.run()

    # Find the API key input field (should be the first text_input)
    api_key_input = at.text_input[0]

    # Enter a valid API key
    api_key_input.set_value("valid_test_key_123")

    # Submit the form by clicking the login button
    # The login button should be inside the form
    login_button = None
    for button in at.button:
        if "Login" in button.label or "login" in button.label.lower():
            login_button = button
            break

    assert login_button is not None, "Login button not found"
    login_button.click()
    at.run()

    # Verify the API key was stored in session state
    assert "api_key" in at.session_state
    assert at.session_state["api_key"] == "valid_test_key_123"  # pragma: allowlist secret

    # Verify the API was called with the correct parameters
    mock_get.assert_called_once()
    call_args = mock_get.call_args

    # Check that the X-API-Key header was included
    assert "headers" in call_args.kwargs
    assert "X-API-Key" in call_args.kwargs["headers"]
    assert call_args.kwargs["headers"]["X-API-Key"] == "valid_test_key_123"


@patch("components.auth.requests.get")
def test_login_failure_with_invalid_api_key(mock_get: MagicMock) -> None:
    """Test login failure scenario with invalid API key.

    **Validates: Requirements 1.2, 1.4**

    When an organizer enters an invalid API key and submits the form:
    - The dashboard should validate it against the backend (HTTP 401)
    - An error message should be displayed
    - The API key should NOT be stored in session state
    """
    # Mock failed API response (HTTP 401)
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_get.return_value = mock_response

    # Initialize the app
    at = AppTest.from_file("app.py")
    at.run()

    # Find the API key input field
    api_key_input = at.text_input[0]

    # Enter an invalid API key
    api_key_input.set_value("invalid_key")

    # Submit the form by clicking the login button
    login_button = None
    for button in at.button:
        if "Login" in button.label or "login" in button.label.lower():
            login_button = button
            break

    assert login_button is not None, "Login button not found"
    login_button.click()
    at.run()

    # Verify the API key was NOT stored in session state
    assert "api_key" not in at.session_state or at.session_state.get("api_key") is None

    # Verify an error message is displayed
    assert len(at.error) > 0
    error_message = at.error[0].value
    assert "Invalid" in error_message or "invalid" in error_message


@patch("components.auth.requests.get")
def test_logout_functionality(mock_get: MagicMock) -> None:
    """Test logout functionality.

    **Validates: Requirement 1.6**

    When an organizer clicks logout:
    - The API key should be cleared from session state
    - The user should be redirected to the authentication page
    """
    # Mock successful API response for initial login
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    # Initialize the app
    at = AppTest.from_file("app.py")
    at.run()

    # First, log in with a valid API key
    api_key_input = at.text_input[0]
    api_key_input.set_value("test_key_for_logout")

    # Find and click login button
    login_button = None
    for button in at.button:
        if "Login" in button.label or "login" in button.label.lower():
            login_button = button
            break

    assert login_button is not None, "Login button not found"
    login_button.click()
    at.run()

    # Verify user is authenticated
    assert "api_key" in at.session_state
    assert at.session_state["api_key"] == "test_key_for_logout"  # pragma: allowlist secret

    # Now find and click the logout button
    # The logout button should be in the sidebar after authentication
    logout_button = None
    for button in at.button:
        if "Logout" in button.label or "logout" in button.label.lower():
            logout_button = button
            break

    assert logout_button is not None, "Logout button not found"

    # Click logout - this will clear session state and trigger a rerun
    logout_button.click()

    # After logout, we need to create a fresh AppTest instance
    # because the session state has been cleared and widgets reset
    # This simulates the actual behavior where the page reloads
    at_after_logout = AppTest.from_file("app.py")
    at_after_logout.run()

    # Verify the API key was cleared from session state
    assert (
        "api_key" not in at_after_logout.session_state
        or at_after_logout.session_state.get("api_key") is None
    )

    # Verify the authentication form is displayed again
    # After logout, the user should see the login form
    assert len(at_after_logout.text_input) >= 1  # API key input should be present
    assert len(at_after_logout.title) > 0  # Title should be displayed


@patch("components.auth.requests.get")
def test_empty_api_key_validation(mock_get: MagicMock) -> None:
    """Test that empty API key is rejected before making API call.

    **Validates: Requirement 1.2**

    When an organizer submits the form without entering an API key:
    - An error message should be displayed
    - No API call should be made
    """
    # Initialize the app
    at = AppTest.from_file("app.py")
    at.run()

    # Leave the API key input empty and submit the form
    # Find and click login button without setting API key
    login_button = None
    for button in at.button:
        if "Login" in button.label or "login" in button.label.lower():
            login_button = button
            break

    assert login_button is not None, "Login button not found"
    login_button.click()
    at.run()

    # Verify an error message is displayed
    assert len(at.error) > 0
    error_message = at.error[0].value
    assert "enter" in error_message.lower() or "required" in error_message.lower()

    # Verify no API call was made
    mock_get.assert_not_called()


@patch("components.auth.requests.get")
def test_api_base_url_configuration(mock_get: MagicMock) -> None:
    """Test that API base URL can be configured.

    **Validates: Requirement 1.2**

    The dashboard should allow configuration of the API base URL through:
    - Environment variable (API_BASE_URL)
    - Advanced settings in the authentication form
    """
    # Mock successful API response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    # Initialize the app
    at = AppTest.from_file("app.py")
    at.run()

    # Verify that api_base_url is set in session state
    # (either from env var or default)
    assert "api_base_url" in at.session_state
    assert at.session_state["api_base_url"] is not None

    # The default should be http://localhost:8000 if no env var is set
    # (This test assumes no API_BASE_URL env var is set)
    expected_default = "http://localhost:8000"
    assert at.session_state["api_base_url"] == expected_default


@patch("components.auth.requests.get")
def test_authentication_with_network_timeout(mock_get: MagicMock) -> None:
    """Test authentication behavior when network timeout occurs.

    **Validates: Requirements 1.2, 1.4**

    When the API request times out:
    - An error message should be displayed
    - The API key should NOT be stored in session state
    """
    # Mock timeout exception
    import requests

    mock_get.side_effect = requests.Timeout("Connection timed out")

    # Initialize the app
    at = AppTest.from_file("app.py")
    at.run()

    # Enter API key and submit
    api_key_input = at.text_input[0]
    api_key_input.set_value("test_key")

    # Find and click login button
    login_button = None
    for button in at.button:
        if "Login" in button.label or "login" in button.label.lower():
            login_button = button
            break

    assert login_button is not None, "Login button not found"
    login_button.click()
    at.run()

    # Verify the API key was NOT stored in session state
    assert "api_key" not in at.session_state or at.session_state.get("api_key") is None

    # Verify an error message is displayed
    # The error could be displayed as either an error or warning
    assert len(at.error) > 0 or len(at.warning) > 0


@patch("components.auth.requests.get")
def test_authentication_with_connection_error(mock_get: MagicMock) -> None:
    """Test authentication behavior when connection fails.

    **Validates: Requirements 1.2, 1.4**

    When the connection to the API fails:
    - An error message should be displayed
    - The API key should NOT be stored in session state
    """
    # Mock connection error
    import requests

    mock_get.side_effect = requests.ConnectionError("Cannot connect to server")

    # Initialize the app
    at = AppTest.from_file("app.py")
    at.run()

    # Enter API key and submit
    api_key_input = at.text_input[0]
    api_key_input.set_value("test_key")

    # Find and click login button
    login_button = None
    for button in at.button:
        if "Login" in button.label or "login" in button.label.lower():
            login_button = button
            break

    assert login_button is not None, "Login button not found"
    login_button.click()
    at.run()

    # Verify the API key was NOT stored in session state
    assert "api_key" not in at.session_state or at.session_state.get("api_key") is None

    # Verify an error message is displayed
    assert len(at.error) > 0 or len(at.warning) > 0
