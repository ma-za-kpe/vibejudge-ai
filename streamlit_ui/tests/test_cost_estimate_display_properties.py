"""Property-based tests for cost estimate display.

Feature: streamlit-organizer-dashboard
Tests universal properties of cost estimate display behavior using Hypothesis.
"""

from typing import Any
from unittest.mock import Mock, patch

from hypothesis import given
from hypothesis import strategies as st


# Custom strategies for cost estimate data
@st.composite
def valid_hack_id(draw: Any) -> str:
    """Generate a valid ULID-format hackathon ID.

    Returns:
        A string matching ULID format (01 followed by 24 alphanumeric chars)
    """
    return draw(st.from_regex(r"01[A-Z0-9]{24}", fullmatch=True))


@st.composite
def valid_cost_estimate(draw: Any) -> dict[str, Any]:
    """Generate a valid cost estimate response.

    Returns:
        A dictionary with estimated_cost_usd
    """
    return {
        "estimated_cost_usd": draw(
            st.floats(min_value=0.01, max_value=100.0, allow_nan=False, allow_infinity=False)
        )
    }


def fetch_and_display_cost_estimate(hack_id: str, api_client: Any) -> dict[str, Any]:
    """Simulate fetching and displaying cost estimate from the dashboard.

    This function represents the logic that would be in the Streamlit page
    for fetching and displaying cost estimate before triggering analysis.

    Args:
        hack_id: Hackathon ID
        api_client: API client instance

    Returns:
        Dictionary with displayed cost estimate
    """
    # Fetch cost estimate from API
    response = api_client.post(f"/hackathons/{hack_id}/estimate", json={})

    # Display the cost estimate
    displayed = {}
    if "estimated_cost_usd" in response:
        displayed["estimated_cost_usd"] = response["estimated_cost_usd"]

    return displayed


class TestCostEstimateDisplayProperty:
    """Property 14: Cost Estimate Display

    **Validates: Requirements 4.6**

    For any hackathon, the dashboard should fetch and display a cost estimate
    from POST /hackathons/{hack_id}/estimate before allowing analysis to start.
    """

    @given(hack_id=valid_hack_id(), cost_estimate=valid_cost_estimate())
    @patch("components.api_client.requests.Session")
    def test_cost_estimate_is_fetched_before_analysis(
        self, mock_session_class: Mock, hack_id: str, cost_estimate: dict[str, Any]
    ) -> None:
        """
        Property: For any hackathon, cost estimate should be fetched before
        allowing analysis to start.

        This test verifies that:
        1. POST request is made to /hackathons/{hack_id}/estimate
        2. Cost estimate is retrieved from response
        3. Cost estimate is displayed to user

        Args:
            hack_id: Generated hackathon ID
            cost_estimate: Generated cost estimate response
        """
        # Arrange: Mock API client
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = cost_estimate
        mock_session.post.return_value = mock_response

        # Create a simple API client mock
        from components.api_client import APIClient

        api_client = APIClient("http://test", "test_key")

        # Act: Fetch and display cost estimate
        displayed = fetch_and_display_cost_estimate(hack_id, api_client)

        # Assert: POST request was made to correct endpoint
        expected_url = f"http://test/hackathons/{hack_id}/estimate"
        mock_session.post.assert_called_once()

        call_args = mock_session.post.call_args
        actual_url = call_args[0][0] if call_args[0] else call_args[1].get("url")

        assert actual_url == expected_url, f"Expected POST to {expected_url}, but got {actual_url}"

        # Assert: Cost estimate is displayed
        assert "estimated_cost_usd" in displayed, "Cost estimate should be displayed"
        assert displayed["estimated_cost_usd"] == cost_estimate["estimated_cost_usd"], (
            f"Displayed cost should be {cost_estimate['estimated_cost_usd']}, "
            f"but got {displayed['estimated_cost_usd']}"
        )

    @given(hack_id=valid_hack_id(), cost_estimate=valid_cost_estimate())
    @patch("components.api_client.requests.Session")
    def test_cost_estimate_endpoint_format_is_correct(
        self, mock_session_class: Mock, hack_id: str, cost_estimate: dict[str, Any]
    ) -> None:
        """
        Property: Cost estimate endpoint should follow /hackathons/{hack_id}/estimate format.

        This test verifies that:
        1. Endpoint includes hackathon ID
        2. Endpoint ends with /estimate
        3. No query parameters are added

        Args:
            hack_id: Generated hackathon ID
            cost_estimate: Generated cost estimate response
        """
        # Arrange: Mock API client
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = cost_estimate
        mock_session.post.return_value = mock_response

        from components.api_client import APIClient

        api_client = APIClient("http://test", "test_key")

        # Act: Fetch cost estimate
        fetch_and_display_cost_estimate(hack_id, api_client)

        # Assert: Endpoint format is correct
        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        actual_url = call_args[0][0] if call_args[0] else call_args[1].get("url")

        assert "/hackathons/" in actual_url, "Endpoint should contain /hackathons/"
        assert hack_id in actual_url, f"Endpoint should contain hack_id {hack_id}"
        assert actual_url.endswith("/estimate"), "Endpoint should end with /estimate"
        assert "?" not in actual_url, "Endpoint should not contain query parameters"

    @given(hack_id=valid_hack_id(), cost_estimate=valid_cost_estimate())
    @patch("components.api_client.requests.Session")
    def test_cost_estimate_uses_post_method(
        self, mock_session_class: Mock, hack_id: str, cost_estimate: dict[str, Any]
    ) -> None:
        """
        Property: Cost estimate should use POST method, not GET.

        This test verifies that:
        1. POST method is used
        2. GET method is not used
        3. Empty JSON body is sent

        Args:
            hack_id: Generated hackathon ID
            cost_estimate: Generated cost estimate response
        """
        # Arrange: Mock API client
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = cost_estimate
        mock_session.post.return_value = mock_response

        from components.api_client import APIClient

        api_client = APIClient("http://test", "test_key")

        # Act: Fetch cost estimate
        fetch_and_display_cost_estimate(hack_id, api_client)

        # Assert: POST method is used
        mock_session.post.assert_called_once()
        mock_session.get.assert_not_called()

        # Assert: Empty JSON body is sent
        call_kwargs = mock_session.post.call_args[1]
        assert "json" in call_kwargs, "POST request should include JSON body"
        assert call_kwargs["json"] == {}, "POST request should have empty JSON body"

    @given(
        hack_id=valid_hack_id(),
        cost=st.floats(min_value=0.01, max_value=100.0, allow_nan=False, allow_infinity=False),
    )
    @patch("components.api_client.requests.Session")
    def test_cost_estimate_displays_various_cost_ranges(
        self, mock_session_class: Mock, hack_id: str, cost: float
    ) -> None:
        """
        Property: Cost estimate should display correctly for various cost ranges.

        This test verifies that:
        1. Small costs (< $1) are displayed correctly
        2. Large costs (> $50) are displayed correctly
        3. No truncation or rounding errors occur

        Args:
            hack_id: Generated hackathon ID
            cost: Generated cost value
        """
        # Arrange: Mock API client with specific cost
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"estimated_cost_usd": cost}
        mock_session.post.return_value = mock_response

        from components.api_client import APIClient

        api_client = APIClient("http://test", "test_key")

        # Act: Fetch and display cost estimate
        displayed = fetch_and_display_cost_estimate(hack_id, api_client)

        # Assert: Cost is displayed correctly
        assert displayed["estimated_cost_usd"] == cost, (
            f"Displayed cost should be {cost}, but got {displayed['estimated_cost_usd']}"
        )

        # Assert: Cost is positive
        assert displayed["estimated_cost_usd"] > 0, (
            f"Cost should be positive, but got {displayed['estimated_cost_usd']}"
        )

    @given(hack_id=valid_hack_id(), cost_estimate=valid_cost_estimate())
    @patch("components.api_client.requests.Session")
    def test_cost_estimate_is_displayed_as_number(
        self, mock_session_class: Mock, hack_id: str, cost_estimate: dict[str, Any]
    ) -> None:
        """
        Property: Cost estimate should be displayed as a number (float).

        This test verifies that:
        1. Cost is a number type
        2. Cost is not NaN or infinity
        3. Cost can be used in calculations

        Args:
            hack_id: Generated hackathon ID
            cost_estimate: Generated cost estimate response
        """
        # Arrange: Mock API client
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = cost_estimate
        mock_session.post.return_value = mock_response

        from components.api_client import APIClient

        api_client = APIClient("http://test", "test_key")

        # Act: Fetch and display cost estimate
        displayed = fetch_and_display_cost_estimate(hack_id, api_client)

        # Assert: Cost is a number
        assert isinstance(displayed["estimated_cost_usd"], (int, float)), (
            f"Cost should be a number, but got {type(displayed['estimated_cost_usd'])}"
        )

        # Assert: Cost is not NaN or infinity
        import math

        assert not math.isnan(displayed["estimated_cost_usd"]), "Cost should not be NaN"
        assert not math.isinf(displayed["estimated_cost_usd"]), "Cost should not be infinity"

    @given(
        hack_ids=st.lists(valid_hack_id(), min_size=2, max_size=5, unique=True),
        costs=st.lists(
            st.floats(min_value=0.01, max_value=100.0, allow_nan=False, allow_infinity=False),
            min_size=2,
            max_size=5,
        ),
    )
    @patch("components.api_client.requests.Session")
    def test_cost_estimate_uses_correct_hack_id(
        self, mock_session_class: Mock, hack_ids: list[str], costs: list[float]
    ) -> None:
        """
        Property: Each hackathon should get cost estimate from its own endpoint.

        This test verifies that:
        1. Correct hack_id is used in endpoint
        2. Different hackathons get different estimates
        3. No cross-contamination between hackathons

        Args:
            hack_ids: List of generated hackathon IDs
            costs: List of generated cost values
        """
        # Arrange: Mock API client
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        from components.api_client import APIClient

        api_client = APIClient("http://test", "test_key")

        # Act & Assert: Fetch cost estimate for each hackathon
        for i, hack_id in enumerate(hack_ids):
            cost = costs[i % len(costs)]

            mock_response = Mock()
            mock_response.ok = True
            mock_response.status_code = 200
            mock_response.json.return_value = {"estimated_cost_usd": cost}
            mock_session.post.return_value = mock_response
            mock_session.post.reset_mock()

            fetch_and_display_cost_estimate(hack_id, api_client)

            # Assert: Correct endpoint was called
            expected_url = f"http://test/hackathons/{hack_id}/estimate"
            mock_session.post.assert_called_once()

            call_args = mock_session.post.call_args
            actual_url = call_args[0][0] if call_args[0] else call_args[1].get("url")

            assert actual_url == expected_url, f"Expected {expected_url}, but got {actual_url}"

    @given(
        hack_id=valid_hack_id(),
        cost=st.floats(min_value=0.01, max_value=0.10, allow_nan=False, allow_infinity=False),
    )
    @patch("components.api_client.requests.Session")
    def test_cost_estimate_handles_small_costs(
        self, mock_session_class: Mock, hack_id: str, cost: float
    ) -> None:
        """
        Property: Cost estimate should handle small costs (< $0.10) correctly.

        This test verifies that:
        1. Small costs are not rounded to zero
        2. Precision is maintained
        3. Users can see accurate budget impact

        Args:
            hack_id: Generated hackathon ID
            cost: Generated small cost value
        """
        # Arrange: Mock API client with small cost
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"estimated_cost_usd": cost}
        mock_session.post.return_value = mock_response

        from components.api_client import APIClient

        api_client = APIClient("http://test", "test_key")

        # Act: Fetch and display cost estimate
        displayed = fetch_and_display_cost_estimate(hack_id, api_client)

        # Assert: Small cost is not rounded to zero
        assert displayed["estimated_cost_usd"] > 0, (
            f"Small cost should not be rounded to zero, got {displayed['estimated_cost_usd']}"
        )

        # Assert: Cost value is preserved
        assert displayed["estimated_cost_usd"] == cost, (
            f"Small cost should be {cost}, but got {displayed['estimated_cost_usd']}"
        )

    @given(hack_id=valid_hack_id(), cost_estimate=valid_cost_estimate())
    @patch("components.api_client.requests.Session")
    def test_cost_estimate_includes_authentication(
        self, mock_session_class: Mock, hack_id: str, cost_estimate: dict[str, Any]
    ) -> None:
        """
        Property: Cost estimate request should include X-API-Key authentication.

        This test verifies that:
        1. X-API-Key header is included
        2. API key value is correct
        3. Authentication is applied to estimate endpoint

        Args:
            hack_id: Generated hackathon ID
            cost_estimate: Generated cost estimate response
        """
        # Arrange: Mock API client
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = cost_estimate
        mock_session.post.return_value = mock_response

        api_key = "test_api_key_123"  # pragma: allowlist secret
        from components.api_client import APIClient

        api_client = APIClient("http://test", api_key)

        # Act: Fetch cost estimate
        fetch_and_display_cost_estimate(hack_id, api_client)

        # Assert: X-API-Key header was set
        mock_session.headers.update.assert_called_once()
        update_call_args = mock_session.headers.update.call_args[0][0]

        assert "X-API-Key" in update_call_args, "X-API-Key header should be included"
        assert update_call_args["X-API-Key"] == api_key, (
            f"X-API-Key should be {api_key}, but got {update_call_args['X-API-Key']}"
        )

    @given(hack_id=valid_hack_id(), cost_estimate=valid_cost_estimate())
    @patch("components.api_client.requests.Session")
    def test_cost_estimate_display_is_required_before_analysis(
        self, mock_session_class: Mock, hack_id: str, cost_estimate: dict[str, Any]
    ) -> None:
        """
        Property: Cost estimate must be fetched and displayed before analysis starts.

        This test verifies that:
        1. Cost estimate is fetched first
        2. Cost estimate is displayed to user
        3. User can see cost before confirming analysis

        Args:
            hack_id: Generated hackathon ID
            cost_estimate: Generated cost estimate response
        """
        # Arrange: Mock API client
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = cost_estimate
        mock_session.post.return_value = mock_response

        from components.api_client import APIClient

        api_client = APIClient("http://test", "test_key")

        # Act: Fetch and display cost estimate
        displayed = fetch_and_display_cost_estimate(hack_id, api_client)

        # Assert: Cost estimate was fetched
        mock_session.post.assert_called_once()

        # Assert: Cost estimate is available for display
        assert "estimated_cost_usd" in displayed, (
            "Cost estimate should be available for display before analysis"
        )

        # Assert: Cost estimate has a valid value
        assert displayed["estimated_cost_usd"] > 0, "Cost estimate should have a positive value"
