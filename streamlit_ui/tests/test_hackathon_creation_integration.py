"""Integration tests for hackathon creation flow using Streamlit AppTest.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6**

This module tests the full hackathon creation form submission flow including:
- Form display with all required fields
- Successful form submission (HTTP 201)
- Validation errors (HTTP 422)
- Date range validation (end_date must be after start_date)
- Budget validation (must be positive or empty)
- Success message display with hack_id
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from streamlit.testing.v1 import AppTest


@pytest.fixture
def authenticated_app() -> AppTest:
    """Create an authenticated app instance for testing.

    Returns:
        An AppTest instance with authentication already set up.
    """
    at = AppTest.from_file("streamlit_ui/pages/1_🎯_Create_Hackathon.py")

    # Set up authentication in session state
    at.session_state["api_key"] = "test_api_key_123"  # pragma: allowlist secret
    at.session_state["api_base_url"] = "http://localhost:8000"

    at.run()
    return at


def test_hackathon_creation_form_displayed(authenticated_app: AppTest) -> None:
    """Test that hackathon creation form is displayed with all required fields.

    **Validates: Requirement 2.1**

    The dashboard should provide a hackathon creation form with:
    - Name input field
    - Description textarea
    - Start date input
    - End date input
    - Budget limit input (optional)
    - Submit button
    """
    at = authenticated_app

    # Verify the page loaded without errors
    assert not at.exception

    # Verify title is displayed
    assert len(at.title) > 0
    assert "Create" in at.title[0].value or "Hackathon" in at.title[0].value

    # Verify form elements are present
    # Should have at least 1 text input (name)
    assert len(at.text_input) >= 1

    # Should have at least 1 text area (description)
    assert len(at.text_area) >= 1

    # Should have at least 2 date inputs (start_date, end_date)
    assert len(at.date_input) >= 2

    # Should have at least 1 number input (budget)
    assert len(at.number_input) >= 1

    # Should have at least 1 button (submit)
    assert len(at.button) >= 1


@patch("components.api_client.requests.Session.post")
def test_successful_hackathon_creation(mock_post: MagicMock, authenticated_app: AppTest) -> None:
    """Test successful form submission with HTTP 201 response.

    **Validates: Requirements 2.2, 2.3**

    When an organizer submits a valid hackathon creation form:
    - The dashboard should send a POST request to /hackathons endpoint
    - When the backend returns HTTP 201, the dashboard should display
      the created hackathon details including hack_id
    """
    # Mock successful API response (HTTP 201)
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "hack_id": "01HXXX123456789",
        "name": "Test Hackathon",
        "description": "A test hackathon",
        "status": "active",
        "start_date": "2025-03-01T00:00:00Z",
        "end_date": "2025-03-03T23:59:59Z",
        "created_at": "2025-02-01T10:00:00Z",
    }
    mock_post.return_value = mock_response

    at = authenticated_app

    # Fill in the form fields
    # Name field (first text_input)
    at.text_input[0].set_value("Test Hackathon")

    # Description field (first text_area)
    at.text_area[0].set_value("A test hackathon for integration testing")

    # Start date (first date_input)
    start_date = datetime.now().date()
    at.date_input[0].set_value(start_date)

    # End date (second date_input) - must be after start date
    end_date = (datetime.now() + timedelta(days=3)).date()
    at.date_input[1].set_value(end_date)

    # Budget (first number_input) - optional, set to 100.0
    at.number_input[0].set_value(100.0)

    # Submit the form
    submit_button = None
    for button in at.button:
        if "Create" in button.label or "create" in button.label.lower():
            submit_button = button
            break

    assert submit_button is not None, "Submit button not found"
    submit_button.click()
    at.run()

    # Verify the API was called with correct endpoint
    mock_post.assert_called_once()
    call_args = mock_post.call_args

    # Check the endpoint
    assert "/hackathons" in call_args.args[0]

    # Check the payload
    payload = call_args.kwargs.get("json")
    assert payload is not None
    assert payload["name"] == "Test Hackathon"
    assert payload["description"] == "A test hackathon for integration testing"
    assert "start_date" in payload
    assert "end_date" in payload
    assert payload["budget_limit_usd"] == 100.0

    # Verify success message is displayed
    assert len(at.success) > 0
    success_message = at.success[0].value
    assert "success" in success_message.lower() or "created" in success_message.lower()

    # Verify hack_id is displayed
    # The hack_id should be displayed in an info box or similar
    assert len(at.info) > 0
    # Check if any info box contains the hack_id
    hack_id_displayed = any("01HXXX123456789" in info.value for info in at.info)
    assert hack_id_displayed, "hack_id not displayed in response"


@patch("components.api_client.requests.Session.post")
def test_validation_error_display(mock_post: MagicMock, authenticated_app: AppTest) -> None:
    """Test validation error display with HTTP 422 response.

    **Validates: Requirement 2.4**

    When the backend returns HTTP 422 (validation error):
    - The dashboard should display validation errors inline with the form fields
    """
    # Mock validation error response (HTTP 422)
    mock_response = MagicMock()
    mock_response.status_code = 422
    mock_response.ok = False  # Important: response.ok must be False for error handling
    mock_response.json.return_value = {
        "detail": [
            {"loc": ["body", "name"], "msg": "field required", "type": "value_error.missing"}
        ]
    }
    mock_post.return_value = mock_response

    at = authenticated_app

    # Fill in the form with valid data (to trigger API call)
    at.text_input[0].set_value("Test Hackathon")
    at.text_area[0].set_value("A test hackathon")

    start_date = datetime.now().date()
    at.date_input[0].set_value(start_date)

    end_date = (datetime.now() + timedelta(days=3)).date()
    at.date_input[1].set_value(end_date)

    # Submit the form
    submit_button = None
    for button in at.button:
        if "Create" in button.label or "create" in button.label.lower():
            submit_button = button
            break

    assert submit_button is not None, "Submit button not found"
    submit_button.click()
    at.run()

    # Verify an error message is displayed
    assert len(at.error) > 0
    error_message = at.error[0].value
    assert "Validation" in error_message or "validation" in error_message.lower()


def test_date_range_validation_rejects_invalid_range(authenticated_app: AppTest) -> None:
    """Test date range validation rejects end_date before start_date.

    **Validates: Requirement 2.5**

    The dashboard should validate that end_date is after start_date before submission.
    If end_date is not after start_date, an error should be displayed.
    """
    at = authenticated_app

    # Fill in the form with invalid date range
    at.text_input[0].set_value("Test Hackathon")
    at.text_area[0].set_value("A test hackathon")

    # Set end_date BEFORE start_date (invalid)
    start_date = datetime.now().date()
    end_date = (datetime.now() - timedelta(days=1)).date()  # One day before start

    at.date_input[0].set_value(start_date)
    at.date_input[1].set_value(end_date)

    # Submit the form
    submit_button = None
    for button in at.button:
        if "Create" in button.label or "create" in button.label.lower():
            submit_button = button
            break

    assert submit_button is not None, "Submit button not found"
    submit_button.click()
    at.run()

    # Verify an error message is displayed
    assert len(at.error) > 0
    error_message = at.error[0].value
    assert "date" in error_message.lower() or "after" in error_message.lower()


def test_date_range_validation_accepts_valid_range(authenticated_app: AppTest) -> None:
    """Test date range validation accepts end_date after start_date.

    **Validates: Requirement 2.5**

    The dashboard should accept valid date ranges where end_date is after start_date.
    """
    at = authenticated_app

    # Fill in the form with valid date range
    at.text_input[0].set_value("Test Hackathon")
    at.text_area[0].set_value("A test hackathon")

    # Set end_date AFTER start_date (valid)
    start_date = datetime.now().date()
    end_date = (datetime.now() + timedelta(days=3)).date()

    at.date_input[0].set_value(start_date)
    at.date_input[1].set_value(end_date)

    # Mock successful API response to avoid actual API call
    with patch("components.api_client.requests.Session.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "hack_id": "01HXXX123456789",
            "name": "Test Hackathon",
            "status": "active",
        }
        mock_post.return_value = mock_response

        # Submit the form
        submit_button = None
        for button in at.button:
            if "Create" in button.label or "create" in button.label.lower():
                submit_button = button
                break

        assert submit_button is not None, "Submit button not found"
        submit_button.click()
        at.run()

        # Verify NO date validation error is displayed
        # (there might be other errors, but not date-related)
        if len(at.error) > 0:
            for error in at.error:
                assert "date" not in error.value.lower() or "after" not in error.value.lower()


def test_budget_validation_rejects_zero_value(authenticated_app: AppTest) -> None:
    """Test budget validation rejects zero value.

    **Validates: Requirement 2.6**

    The dashboard should validate that budget_limit_usd is a positive number.
    Zero and negative values should be rejected with an error message.

    Note: Streamlit's number_input with min_value=0.0 prevents negative input
    in the UI, but zero should still be rejected by validation logic.
    """
    at = authenticated_app

    # Fill in the form with zero budget
    at.text_input[0].set_value("Test Hackathon")
    at.text_area[0].set_value("A test hackathon")

    start_date = datetime.now().date()
    end_date = (datetime.now() + timedelta(days=3)).date()

    at.date_input[0].set_value(start_date)
    at.date_input[1].set_value(end_date)

    # Set zero budget (invalid - must be positive)
    at.number_input[0].set_value(0.0)

    # Submit the form
    submit_button = None
    for button in at.button:
        if "Create" in button.label or "create" in button.label.lower():
            submit_button = button
            break

    assert submit_button is not None, "Submit button not found"
    submit_button.click()
    at.run()

    # Verify an error message is displayed
    assert len(at.error) > 0
    error_message = at.error[0].value
    assert "budget" in error_message.lower() or "positive" in error_message.lower()


def test_budget_validation_accepts_positive_value(authenticated_app: AppTest) -> None:
    """Test budget validation accepts positive values.

    **Validates: Requirement 2.6**

    The dashboard should accept positive budget values.
    """
    at = authenticated_app

    # Fill in the form with positive budget
    at.text_input[0].set_value("Test Hackathon")
    at.text_area[0].set_value("A test hackathon")

    start_date = datetime.now().date()
    end_date = (datetime.now() + timedelta(days=3)).date()

    at.date_input[0].set_value(start_date)
    at.date_input[1].set_value(end_date)

    # Set positive budget (valid)
    at.number_input[0].set_value(100.0)

    # Mock successful API response
    with patch("components.api_client.requests.Session.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "hack_id": "01HXXX123456789",
            "name": "Test Hackathon",
            "status": "active",
        }
        mock_post.return_value = mock_response

        # Submit the form
        submit_button = None
        for button in at.button:
            if "Create" in button.label or "create" in button.label.lower():
                submit_button = button
                break

        assert submit_button is not None, "Submit button not found"
        submit_button.click()
        at.run()

        # Verify NO budget validation error is displayed
        if len(at.error) > 0:
            for error in at.error:
                assert "budget" not in error.value.lower() or "positive" not in error.value.lower()


def test_budget_validation_accepts_empty_value(authenticated_app: AppTest) -> None:
    """Test budget validation accepts empty/None values.

    **Validates: Requirement 2.6**

    The dashboard should accept empty budget values (no limit).
    """
    at = authenticated_app

    # Fill in the form without budget (leave as None)
    at.text_input[0].set_value("Test Hackathon")
    at.text_area[0].set_value("A test hackathon")

    start_date = datetime.now().date()
    end_date = (datetime.now() + timedelta(days=3)).date()

    at.date_input[0].set_value(start_date)
    at.date_input[1].set_value(end_date)

    # Leave budget as None (default)
    # Don't set any value for number_input

    # Mock successful API response
    with patch("components.api_client.requests.Session.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "hack_id": "01HXXX123456789",
            "name": "Test Hackathon",
            "status": "active",
        }
        mock_post.return_value = mock_response

        # Submit the form
        submit_button = None
        for button in at.button:
            if "Create" in button.label or "create" in button.label.lower():
                submit_button = button
                break

        assert submit_button is not None, "Submit button not found"
        submit_button.click()
        at.run()

        # Verify the API was called
        mock_post.assert_called_once()

        # Verify the payload does NOT include budget_limit_usd (or it's None)
        payload = mock_post.call_args.kwargs.get("json")
        assert payload is not None
        # Budget should either not be in payload or be None
        assert "budget_limit_usd" not in payload or payload.get("budget_limit_usd") is None


def test_required_field_validation_name(authenticated_app: AppTest) -> None:
    """Test that empty name field is rejected.

    **Validates: Requirement 2.1**

    The name field is required. Submitting without a name should display an error.
    """
    at = authenticated_app

    # Fill in the form WITHOUT name
    # Leave name empty
    at.text_area[0].set_value("A test hackathon")

    start_date = datetime.now().date()
    end_date = (datetime.now() + timedelta(days=3)).date()

    at.date_input[0].set_value(start_date)
    at.date_input[1].set_value(end_date)

    # Submit the form
    submit_button = None
    for button in at.button:
        if "Create" in button.label or "create" in button.label.lower():
            submit_button = button
            break

    assert submit_button is not None, "Submit button not found"
    submit_button.click()
    at.run()

    # Verify an error message is displayed
    assert len(at.error) > 0
    error_message = at.error[0].value
    assert "name" in error_message.lower() or "required" in error_message.lower()


def test_required_field_validation_description(authenticated_app: AppTest) -> None:
    """Test that empty description field is rejected.

    **Validates: Requirement 2.1**

    The description field is required. Submitting without a description should display an error.
    """
    at = authenticated_app

    # Fill in the form WITHOUT description
    at.text_input[0].set_value("Test Hackathon")
    # Leave description empty

    start_date = datetime.now().date()
    end_date = (datetime.now() + timedelta(days=3)).date()

    at.date_input[0].set_value(start_date)
    at.date_input[1].set_value(end_date)

    # Submit the form
    submit_button = None
    for button in at.button:
        if "Create" in button.label or "create" in button.label.lower():
            submit_button = button
            break

    assert submit_button is not None, "Submit button not found"
    submit_button.click()
    at.run()

    # Verify an error message is displayed
    assert len(at.error) > 0
    error_message = at.error[0].value
    assert "description" in error_message.lower() or "required" in error_message.lower()


@patch("components.api_client.requests.Session.post")
def test_success_message_includes_next_steps(
    mock_post: MagicMock, authenticated_app: AppTest
) -> None:
    """Test that success message includes next steps guidance.

    **Validates: Requirement 2.3**

    After successful creation, the dashboard should display next steps
    to guide the organizer on what to do next.
    """
    # Mock successful API response
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "hack_id": "01HXXX123456789",
        "name": "Test Hackathon",
        "status": "active",
    }
    mock_post.return_value = mock_response

    at = authenticated_app

    # Fill in the form
    at.text_input[0].set_value("Test Hackathon")
    at.text_area[0].set_value("A test hackathon")

    start_date = datetime.now().date()
    end_date = (datetime.now() + timedelta(days=3)).date()

    at.date_input[0].set_value(start_date)
    at.date_input[1].set_value(end_date)

    # Submit the form
    submit_button = None
    for button in at.button:
        if "Create" in button.label or "create" in button.label.lower():
            submit_button = button
            break

    assert submit_button is not None, "Submit button not found"
    submit_button.click()
    at.run()

    # Verify success message is displayed
    assert len(at.success) > 0

    # Verify next steps are mentioned in the markdown content
    # The page should have markdown sections with next steps
    assert len(at.markdown) > 0
    markdown_content = " ".join([md.value for md in at.markdown])
    assert "next" in markdown_content.lower() or "step" in markdown_content.lower()
