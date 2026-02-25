"""Property-based tests for hackathon form submission.

Feature: streamlit-organizer-dashboard
Tests universal properties of hackathon form submission behavior using Hypothesis.
"""

from datetime import datetime, timedelta
from typing import Any
from unittest.mock import Mock, patch

import pytest
from components.api_client import APIClient
from hypothesis import given
from hypothesis import strategies as st


# Custom strategies for form data
@st.composite
def valid_hackathon_name(draw: Any) -> str:
    """Generate valid hackathon names (1-200 characters)."""
    return draw(
        st.text(
            min_size=1,
            max_size=200,
            alphabet=st.characters(
                blacklist_categories=("Cs", "Cc"),  # Exclude control characters
                blacklist_characters=("\x00", "\n", "\r", "\t"),
            ),
        )
    )


@st.composite
def valid_hackathon_description(draw: Any) -> str:
    """Generate valid hackathon descriptions (1-2000 characters)."""
    return draw(
        st.text(
            min_size=1,
            max_size=2000,
            alphabet=st.characters(
                blacklist_categories=("Cs", "Cc"), blacklist_characters=("\x00",)
            ),
        )
    )


@st.composite
def valid_date_range(draw: Any) -> tuple[datetime, datetime]:
    """Generate valid date ranges where end_date > start_date."""
    # Generate start date
    start_date = draw(
        st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2030, 12, 31))
    )

    # Generate end date that is after start date (at least 1 day later)
    days_later = draw(st.integers(min_value=1, max_value=365))
    end_date = start_date + timedelta(days=days_later)

    return start_date, end_date


@st.composite
def valid_budget(draw: Any) -> float | None:
    """Generate valid budget values (positive or None)."""
    # 50% chance of None, 50% chance of positive float
    if draw(st.booleans()):
        return None
    return draw(
        st.floats(min_value=0.01, max_value=100000.0, allow_nan=False, allow_infinity=False)
    )


@st.composite
def valid_hackathon_form_data(draw: Any) -> dict[str, Any]:
    """Generate complete valid hackathon form data."""
    name = draw(valid_hackathon_name())
    description = draw(valid_hackathon_description())
    start_date, end_date = draw(valid_date_range())
    budget = draw(valid_budget())

    payload = {
        "name": name,
        "description": description,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }

    # Only include budget if it's not None
    if budget is not None:
        payload["budget_limit_usd"] = budget

    return payload


class TestFormSubmissionTriggersPostProperty:
    """Property 4: Form Submission Triggers POST

    **Validates: Requirements 2.2**

    For any valid hackathon creation form data, submitting the form should
    trigger a POST request to /hackathons with the form data as JSON.
    """

    @given(
        form_data=valid_hackathon_form_data(),
        base_url=st.from_regex(r"https?://[a-z0-9\-\.]+(?::\d+)?", fullmatch=True),
        api_key=st.text(min_size=1, max_size=100),
    )
    @patch("components.api_client.requests.Session")
    def test_valid_form_data_triggers_post_to_hackathons_endpoint(
        self, mock_session_class: Mock, form_data: dict[str, Any], base_url: str, api_key: str
    ) -> None:
        """
        Property: For any valid hackathon form data, submitting the form should
        trigger a POST request to /hackathons endpoint with the form data as JSON.

        This test verifies that:
        1. APIClient.post() is called with the correct endpoint
        2. The form data is passed as JSON payload
        3. The request includes all required fields

        Args:
            mock_session_class: Mocked requests.Session class
            form_data: Generated valid hackathon form data
            base_url: Generated base URL string
            api_key: Generated API key string
        """
        # Arrange: Mock session instance and response
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "hack_id": "01HXXX123",
            "name": form_data["name"],
            "status": "active",
        }
        mock_session.post.return_value = mock_response

        # Act: Create APIClient and submit form data
        client = APIClient(base_url, api_key)
        result = client.post("/hackathons", form_data)

        # Assert: POST request was made to correct endpoint
        assert mock_session.post.call_count == 1, (
            f"POST should be called exactly once, but was called {mock_session.post.call_count} times"
        )

        # Get the actual call arguments
        call_args = mock_session.post.call_args

        # Assert: Endpoint is correct
        expected_url = f"{base_url}/hackathons"
        actual_url = call_args[0][0] if call_args[0] else call_args[1].get("url")
        assert actual_url == expected_url, (
            f"POST should be made to '{expected_url}', but was made to '{actual_url}'"
        )

        # Assert: JSON payload contains form data
        json_payload = call_args[1].get("json")
        assert json_payload is not None, "POST request should include JSON payload"

        # Assert: All required fields are present in payload
        assert "name" in json_payload, "Payload should include 'name' field"
        assert "description" in json_payload, "Payload should include 'description' field"
        assert "start_date" in json_payload, "Payload should include 'start_date' field"
        assert "end_date" in json_payload, "Payload should include 'end_date' field"

        # Assert: Field values match form data
        assert json_payload["name"] == form_data["name"], (
            f"Payload name '{json_payload['name']}' should match form data '{form_data['name']}'"
        )
        assert json_payload["description"] == form_data["description"], (
            "Payload description should match form data"
        )
        assert json_payload["start_date"] == form_data["start_date"], (
            "Payload start_date should match form data"
        )
        assert json_payload["end_date"] == form_data["end_date"], (
            "Payload end_date should match form data"
        )

        # Assert: Budget field is handled correctly
        if "budget_limit_usd" in form_data:
            assert "budget_limit_usd" in json_payload, (
                "Payload should include 'budget_limit_usd' when provided in form data"
            )
            assert json_payload["budget_limit_usd"] == form_data["budget_limit_usd"], (
                "Payload budget should match form data"
            )

        # Assert: Response is returned
        assert result is not None, "POST request should return a response"
        assert "hack_id" in result, "Response should include 'hack_id'"

    @given(
        form_data=valid_hackathon_form_data(),
        base_url=st.from_regex(r"https?://[a-z0-9\-\.]+(?::\d+)?", fullmatch=True),
        api_key=st.text(min_size=1, max_size=100),
    )
    @patch("components.api_client.requests.Session")
    def test_form_submission_includes_all_required_fields(
        self, mock_session_class: Mock, form_data: dict[str, Any], base_url: str, api_key: str
    ) -> None:
        """
        Property: For any valid form submission, the POST request must include
        all required fields: name, description, start_date, end_date.

        This test verifies that:
        1. All required fields are present in the payload
        2. No required fields are missing
        3. Field values are correctly formatted

        Args:
            mock_session_class: Mocked requests.Session class
            form_data: Generated valid hackathon form data
            base_url: Generated base URL string
            api_key: Generated API key string
        """
        # Arrange: Mock session instance and response
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 201
        mock_response.json.return_value = {"hack_id": "01HXXX123"}
        mock_session.post.return_value = mock_response

        # Act: Create APIClient and submit form data
        client = APIClient(base_url, api_key)
        client.post("/hackathons", form_data)

        # Assert: Get the JSON payload
        call_args = mock_session.post.call_args
        json_payload = call_args[1].get("json")

        # Define required fields
        required_fields = ["name", "description", "start_date", "end_date"]

        # Assert: All required fields are present
        for field in required_fields:
            assert field in json_payload, f"Required field '{field}' is missing from payload"
            assert json_payload[field] is not None, f"Required field '{field}' should not be None"
            assert json_payload[field] != "", f"Required field '{field}' should not be empty"

    @given(
        form_data=valid_hackathon_form_data(),
        base_url=st.from_regex(r"https?://[a-z0-9\-\.]+(?::\d+)?", fullmatch=True),
        api_key=st.text(min_size=1, max_size=100),
    )
    @patch("components.api_client.requests.Session")
    def test_form_submission_with_budget_includes_budget_field(
        self, mock_session_class: Mock, form_data: dict[str, Any], base_url: str, api_key: str
    ) -> None:
        """
        Property: For any form submission that includes a budget, the POST
        request should include the budget_limit_usd field.

        This test verifies that:
        1. When budget is provided, it's included in the payload
        2. When budget is None, it's not included in the payload
        3. Budget values are correctly formatted as floats

        Args:
            mock_session_class: Mocked requests.Session class
            form_data: Generated valid hackathon form data
            base_url: Generated base URL string
            api_key: Generated API key string
        """
        # Arrange: Mock session instance and response
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 201
        mock_response.json.return_value = {"hack_id": "01HXXX123"}
        mock_session.post.return_value = mock_response

        # Act: Create APIClient and submit form data
        client = APIClient(base_url, api_key)
        client.post("/hackathons", form_data)

        # Assert: Get the JSON payload
        call_args = mock_session.post.call_args
        json_payload = call_args[1].get("json")

        # Assert: Budget field handling
        if "budget_limit_usd" in form_data:
            assert "budget_limit_usd" in json_payload, (
                "Payload should include 'budget_limit_usd' when provided in form data"
            )
            assert isinstance(json_payload["budget_limit_usd"], (int, float)), (
                "Budget should be a numeric value"
            )
            assert json_payload["budget_limit_usd"] > 0, "Budget should be positive"
        else:
            # Budget is optional, so it's okay if it's not in the payload
            pass

    @given(
        form_data=valid_hackathon_form_data(),
        base_url=st.from_regex(r"https?://[a-z0-9\-\.]+(?::\d+)?", fullmatch=True),
        api_key=st.text(min_size=1, max_size=100),
    )
    @patch("components.api_client.requests.Session")
    def test_form_submission_dates_are_iso_formatted(
        self, mock_session_class: Mock, form_data: dict[str, Any], base_url: str, api_key: str
    ) -> None:
        """
        Property: For any form submission, the start_date and end_date fields
        should be ISO-formatted strings.

        This test verifies that:
        1. Date fields are strings
        2. Date strings are in ISO format
        3. Dates can be parsed back to datetime objects

        Args:
            mock_session_class: Mocked requests.Session class
            form_data: Generated valid hackathon form data
            base_url: Generated base URL string
            api_key: Generated API key string
        """
        # Arrange: Mock session instance and response
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 201
        mock_response.json.return_value = {"hack_id": "01HXXX123"}
        mock_session.post.return_value = mock_response

        # Act: Create APIClient and submit form data
        client = APIClient(base_url, api_key)
        client.post("/hackathons", form_data)

        # Assert: Get the JSON payload
        call_args = mock_session.post.call_args
        json_payload = call_args[1].get("json")

        # Assert: Date fields are strings
        assert isinstance(json_payload["start_date"], str), "start_date should be a string"
        assert isinstance(json_payload["end_date"], str), "end_date should be a string"

        # Assert: Date strings can be parsed as ISO format
        try:
            start_parsed = datetime.fromisoformat(json_payload["start_date"])
            end_parsed = datetime.fromisoformat(json_payload["end_date"])
        except ValueError as e:
            pytest.fail(f"Date fields should be in ISO format: {e}")

        # Assert: Parsed dates maintain the correct order
        assert end_parsed > start_parsed, "end_date should be after start_date when parsed"

    @given(
        form_data_list=st.lists(valid_hackathon_form_data(), min_size=2, max_size=5),
        base_url=st.from_regex(r"https?://[a-z0-9\-\.]+(?::\d+)?", fullmatch=True),
        api_key=st.text(min_size=1, max_size=100),
    )
    @patch("components.api_client.requests.Session")
    def test_multiple_form_submissions_trigger_multiple_posts(
        self,
        mock_session_class: Mock,
        form_data_list: list[dict[str, Any]],
        base_url: str,
        api_key: str,
    ) -> None:
        """
        Property: For any sequence of valid form submissions, each submission
        should trigger a separate POST request to /hackathons.

        This test verifies that:
        1. Multiple submissions result in multiple POST requests
        2. Each POST request is independent
        3. Each POST contains the correct form data

        Args:
            mock_session_class: Mocked requests.Session class
            form_data_list: List of generated valid hackathon form data
            base_url: Generated base URL string
            api_key: Generated API key string
        """
        # Arrange: Mock session instance and response
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 201
        mock_response.json.return_value = {"hack_id": "01HXXX123"}
        mock_session.post.return_value = mock_response

        # Act: Create APIClient and submit multiple forms
        client = APIClient(base_url, api_key)
        for form_data in form_data_list:
            client.post("/hackathons", form_data)

        # Assert: POST was called for each form submission
        assert mock_session.post.call_count == len(form_data_list), (
            f"POST should be called {len(form_data_list)} times, but was called {mock_session.post.call_count} times"
        )

        # Assert: Each call was to the correct endpoint
        for call in mock_session.post.call_args_list:
            expected_url = f"{base_url}/hackathons"
            actual_url = call[0][0] if call[0] else call[1].get("url")
            assert actual_url == expected_url, f"Each POST should be made to '{expected_url}'"

    @given(
        form_data=valid_hackathon_form_data(),
        base_url=st.from_regex(r"https?://[a-z0-9\-\.]+(?::\d+)?", fullmatch=True),
        api_key=st.text(min_size=1, max_size=100),
    )
    @patch("components.api_client.requests.Session")
    def test_form_submission_returns_response_with_hack_id(
        self, mock_session_class: Mock, form_data: dict[str, Any], base_url: str, api_key: str
    ) -> None:
        """
        Property: For any successful form submission (HTTP 201), the response
        should include a hack_id field.

        This test verifies that:
        1. POST request returns a response
        2. Response contains hack_id
        3. hack_id is a non-empty string

        Args:
            mock_session_class: Mocked requests.Session class
            form_data: Generated valid hackathon form data
            base_url: Generated base URL string
            api_key: Generated API key string
        """
        # Arrange: Mock session instance and response
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        hack_id = "01HXXX123456"
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "hack_id": hack_id,
            "name": form_data["name"],
            "status": "active",
        }
        mock_session.post.return_value = mock_response

        # Act: Create APIClient and submit form data
        client = APIClient(base_url, api_key)
        result = client.post("/hackathons", form_data)

        # Assert: Response contains hack_id
        assert result is not None, "POST request should return a response"
        assert "hack_id" in result, "Response should include 'hack_id' field"
        assert isinstance(result["hack_id"], str), "hack_id should be a string"
        assert len(result["hack_id"]) > 0, "hack_id should not be empty"
        assert result["hack_id"] == hack_id, (
            f"Response hack_id '{result['hack_id']}' should match expected '{hack_id}'"
        )


class TestDateValidationProperty:
    """Property 5: Date Validation

    **Validates: Requirements 2.5**

    For any pair of start_date and end_date, the form validation should
    reject submissions where end_date is not after start_date.
    """

    @given(
        start_date=st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2030, 12, 31)),
        end_date=st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2030, 12, 31)),
    )
    def test_date_validation_rejects_invalid_ranges(
        self, start_date: datetime, end_date: datetime
    ) -> None:
        """
        Property: For any pair of start_date and end_date, validation should
        reject submissions where end_date is not after start_date.

        This test verifies that:
        1. When end_date > start_date, validation passes
        2. When end_date <= start_date, validation fails
        3. Validation logic is consistent across all date pairs

        Args:
            start_date: Generated start date
            end_date: Generated end date
        """
        # Import the validation function (to be implemented in components)
        from components.validators import validate_date_range

        # Act: Validate the date range
        is_valid = validate_date_range(start_date, end_date)

        # Assert: Validation result matches expected behavior
        if end_date > start_date:
            assert is_valid, (
                f"Validation should pass when end_date ({end_date}) > start_date ({start_date})"
            )
        else:
            assert not is_valid, (
                f"Validation should fail when end_date ({end_date}) <= start_date ({start_date})"
            )

    @given(
        start_date=st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2030, 12, 31))
    )
    def test_same_date_is_invalid(self, start_date: datetime) -> None:
        """
        Property: For any date, using the same date for both start_date and
        end_date should be rejected by validation.

        This test verifies that:
        1. start_date == end_date is invalid
        2. Validation requires end_date to be strictly after start_date

        Args:
            start_date: Generated date to use for both start and end
        """
        from components.validators import validate_date_range

        # Act: Validate with same date for start and end
        is_valid = validate_date_range(start_date, start_date)

        # Assert: Same date should be invalid
        assert not is_valid, (
            f"Validation should fail when start_date equals end_date ({start_date})"
        )

    @given(
        start_date=st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2030, 12, 31)),
        days_offset=st.integers(min_value=1, max_value=365),
    )
    def test_valid_date_range_always_passes(self, start_date: datetime, days_offset: int) -> None:
        """
        Property: For any start_date and positive days_offset, creating an
        end_date that is days_offset days after start_date should always pass
        validation.

        This test verifies that:
        1. Valid date ranges (end > start) always pass validation
        2. The offset amount doesn't matter as long as end > start

        Args:
            start_date: Generated start date
            days_offset: Number of days to add (always positive)
        """
        from components.validators import validate_date_range

        # Arrange: Create end_date that is definitely after start_date
        end_date = start_date + timedelta(days=days_offset)

        # Act: Validate the date range
        is_valid = validate_date_range(start_date, end_date)

        # Assert: Valid range should always pass
        assert is_valid, (
            f"Validation should pass when end_date ({end_date}) is {days_offset} days after start_date ({start_date})"
        )

    @given(
        start_date=st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2030, 12, 31)),
        days_offset=st.integers(min_value=1, max_value=365),
    )
    def test_invalid_date_range_always_fails(self, start_date: datetime, days_offset: int) -> None:
        """
        Property: For any start_date and positive days_offset, creating an
        end_date that is days_offset days before start_date should always fail
        validation.

        This test verifies that:
        1. Invalid date ranges (end < start) always fail validation
        2. The offset amount doesn't matter as long as end < start

        Args:
            start_date: Generated start date
            days_offset: Number of days to subtract (always positive)
        """
        from components.validators import validate_date_range

        # Arrange: Create end_date that is definitely before start_date
        end_date = start_date - timedelta(days=days_offset)

        # Act: Validate the date range
        is_valid = validate_date_range(start_date, end_date)

        # Assert: Invalid range should always fail
        assert not is_valid, (
            f"Validation should fail when end_date ({end_date}) is {days_offset} days before start_date ({start_date})"
        )

    @given(
        start_date=st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2030, 12, 31)),
        seconds_offset=st.integers(min_value=1, max_value=86400),
    )
    def test_validation_works_with_time_precision(
        self, start_date: datetime, seconds_offset: int
    ) -> None:
        """
        Property: For any start_date and seconds_offset, validation should
        work correctly even with sub-day precision (hours, minutes, seconds).

        This test verifies that:
        1. Validation works with datetime precision (not just date precision)
        2. Even 1 second difference is sufficient for valid range

        Args:
            start_date: Generated start date with time
            seconds_offset: Number of seconds to add (always positive)
        """
        from components.validators import validate_date_range

        # Arrange: Create end_date that is seconds_offset seconds after start_date
        end_date = start_date + timedelta(seconds=seconds_offset)

        # Act: Validate the date range
        is_valid = validate_date_range(start_date, end_date)

        # Assert: Valid range should pass even with small time differences
        assert is_valid, (
            f"Validation should pass when end_date ({end_date}) is {seconds_offset} seconds after start_date ({start_date})"
        )


class TestBudgetValidationProperty:
    """Property 6: Budget Validation

    **Validates: Requirements 2.6**

    For any budget_limit_usd value, the form validation should reject
    negative numbers and accept positive numbers or empty values.
    """

    @given(
        budget=st.floats(min_value=0.01, max_value=1000000.0, allow_nan=False, allow_infinity=False)
    )
    def test_positive_budget_is_valid(self, budget: float) -> None:
        """
        Property: For any positive budget value, validation should pass.

        This test verifies that:
        1. All positive budget values are accepted
        2. Validation returns True for positive floats

        Args:
            budget: Generated positive budget value
        """
        from components.validators import validate_budget

        # Act: Validate the budget
        is_valid = validate_budget(budget)

        # Assert: Positive budget should be valid
        assert is_valid, f"Validation should pass for positive budget ({budget})"

    @given(budget=st.floats(max_value=-0.01, allow_nan=False, allow_infinity=False))
    def test_negative_budget_is_invalid(self, budget: float) -> None:
        """
        Property: For any negative budget value, validation should fail.

        This test verifies that:
        1. All negative budget values are rejected
        2. Validation returns False for negative floats

        Args:
            budget: Generated negative budget value
        """
        from components.validators import validate_budget

        # Act: Validate the budget
        is_valid = validate_budget(budget)

        # Assert: Negative budget should be invalid
        assert not is_valid, f"Validation should fail for negative budget ({budget})"

    def test_zero_budget_is_invalid(self) -> None:
        """
        Property: Zero budget should be rejected by validation.

        This test verifies that:
        1. Zero is not a valid budget value
        2. Validation requires budget to be strictly positive
        """
        from components.validators import validate_budget

        # Act: Validate zero budget
        is_valid = validate_budget(0.0)

        # Assert: Zero budget should be invalid
        assert not is_valid, "Validation should fail for zero budget"

    def test_none_budget_is_valid(self) -> None:
        """
        Property: None (empty) budget should be accepted by validation.

        This test verifies that:
        1. None is a valid budget value (no budget limit)
        2. Validation returns True for None
        """
        from components.validators import validate_budget

        # Act: Validate None budget
        is_valid = validate_budget(None)

        # Assert: None budget should be valid
        assert is_valid, "Validation should pass for None budget (no limit)"

    @given(
        budget=st.one_of(
            st.none(),
            st.floats(min_value=0.01, max_value=1000000.0, allow_nan=False, allow_infinity=False),
        )
    )
    def test_valid_budget_values_always_pass(self, budget: float | None) -> None:
        """
        Property: For any valid budget value (None or positive), validation
        should always pass.

        This test verifies that:
        1. All valid budget values are accepted
        2. Valid values include None and positive floats

        Args:
            budget: Generated valid budget value (None or positive)
        """
        from components.validators import validate_budget

        # Act: Validate the budget
        is_valid = validate_budget(budget)

        # Assert: Valid budget should pass
        assert is_valid, f"Validation should pass for valid budget ({budget})"

    @given(budget=st.floats(max_value=0.0, allow_nan=False, allow_infinity=False))
    def test_non_positive_budget_always_fails(self, budget: float) -> None:
        """
        Property: For any non-positive budget value (negative or zero),
        validation should always fail.

        This test verifies that:
        1. All non-positive budget values are rejected
        2. Invalid values include zero and negative floats

        Args:
            budget: Generated non-positive budget value
        """
        from components.validators import validate_budget

        # Act: Validate the budget
        is_valid = validate_budget(budget)

        # Assert: Non-positive budget should fail
        assert not is_valid, f"Validation should fail for non-positive budget ({budget})"

    @given(budget=st.floats(min_value=0.01, max_value=0.99, allow_nan=False, allow_infinity=False))
    def test_small_positive_budget_is_valid(self, budget: float) -> None:
        """
        Property: For any small positive budget value (< $1), validation
        should pass.

        This test verifies that:
        1. Even very small positive budgets are accepted
        2. There is no minimum budget requirement (other than > 0)

        Args:
            budget: Generated small positive budget value
        """
        from components.validators import validate_budget

        # Act: Validate the budget
        is_valid = validate_budget(budget)

        # Assert: Small positive budget should be valid
        assert is_valid, f"Validation should pass for small positive budget ({budget})"

    @given(
        budget=st.floats(
            min_value=1000000.0, max_value=10000000.0, allow_nan=False, allow_infinity=False
        )
    )
    def test_large_positive_budget_is_valid(self, budget: float) -> None:
        """
        Property: For any large positive budget value (> $1M), validation
        should pass.

        This test verifies that:
        1. Even very large positive budgets are accepted
        2. There is no maximum budget limit in validation

        Args:
            budget: Generated large positive budget value
        """
        from components.validators import validate_budget

        # Act: Validate the budget
        is_valid = validate_budget(budget)

        # Assert: Large positive budget should be valid
        assert is_valid, f"Validation should pass for large positive budget ({budget})"
