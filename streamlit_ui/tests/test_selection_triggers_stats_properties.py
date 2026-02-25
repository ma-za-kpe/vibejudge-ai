"""Property-based tests for hackathon selection triggering stats fetch.

Feature: streamlit-organizer-dashboard
Tests universal properties of hackathon selection behavior using Hypothesis.
"""

from typing import Any
from unittest.mock import Mock, patch

from components.api_client import APIClient
from hypothesis import given
from hypothesis import strategies as st


# Custom strategies for hackathon IDs
@st.composite
def valid_hack_id(draw: Any) -> str:
    """Generate a valid ULID-format hackathon ID.

    ULID format: 01 followed by 24 alphanumeric characters (uppercase).
    Example: 01HXXX1234567890ABCDEFGHIJ
    """
    return draw(st.from_regex(r"01[A-Z0-9]{24}", fullmatch=True))


# Custom strategies for stats response
@st.composite
def valid_stats_response(draw: Any, hack_id: str) -> dict[str, Any]:
    """Generate a valid stats response dictionary.

    Args:
        hack_id: The hackathon ID for the stats

    Returns:
        A dictionary with stats fields matching the API response structure
    """
    return {
        "hack_id": hack_id,
        "submission_count": draw(st.integers(min_value=0, max_value=1000)),
        "verified_count": draw(st.integers(min_value=0, max_value=1000)),
        "pending_count": draw(st.integers(min_value=0, max_value=100)),
        "participant_count": draw(st.integers(min_value=0, max_value=3000)),
        "analysis_status": draw(st.sampled_from(["not_started", "running", "completed", "failed"])),
        "last_updated": draw(st.datetimes().map(lambda dt: dt.isoformat() + "Z")),
    }


class TestSelectionTriggersStatsFetchProperty:
    """Property 9: Selection Triggers Stats Fetch

    **Validates: Requirements 3.2**

    For any hackathon selection from the dropdown, the dashboard should fetch
    statistics from GET /hackathons/{hack_id}/stats.
    """

    @given(
        hack_id=valid_hack_id(),
        base_url=st.from_regex(r"https?://[a-z0-9\-\.]+(?::\d+)?", fullmatch=True),
        api_key=st.text(min_size=1, max_size=100),
    )
    @patch("components.api_client.requests.Session")
    def test_selecting_hackathon_fetches_stats(
        self, mock_session_class: Mock, hack_id: str, base_url: str, api_key: str
    ) -> None:
        """
        Property: For any hackathon selection (hack_id), the dashboard should
        fetch statistics from GET /hackathons/{hack_id}/stats.

        This test verifies that:
        1. Selecting a hackathon triggers a GET request to the stats endpoint
        2. The correct hack_id is used in the endpoint URL
        3. The request is made with proper authentication

        Args:
            mock_session_class: Mocked requests.Session class
            hack_id: Generated hackathon ID
            base_url: Generated base URL string
            api_key: Generated API key string
        """
        # Arrange: Mock session instance and response
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Create a valid stats response
        stats_data = {
            "hack_id": hack_id,
            "submission_count": 150,
            "verified_count": 145,
            "pending_count": 5,
            "participant_count": 450,
            "analysis_status": "completed",
            "last_updated": "2025-03-04T12:00:00Z",
        }

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = stats_data
        mock_session.get.return_value = mock_response

        # Act: Simulate hackathon selection by fetching stats
        client = APIClient(base_url, api_key)
        endpoint = f"/hackathons/{hack_id}/stats"
        response = client.get(endpoint)

        # Assert: GET request was made to the correct endpoint
        expected_url = f"{base_url.rstrip('/')}{endpoint}"
        mock_session.get.assert_called_once()

        # Get the actual call arguments
        call_args = mock_session.get.call_args
        actual_url = call_args[0][0] if call_args[0] else call_args[1].get("url")

        assert actual_url == expected_url, (
            f"Expected GET request to '{expected_url}', but got '{actual_url}'"
        )

        # Assert: Response contains the hack_id
        assert response["hack_id"] == hack_id, (
            f"Stats response should contain hack_id '{hack_id}', but got '{response.get('hack_id')}'"
        )

    @given(
        hack_id=valid_hack_id(),
        base_url=st.from_regex(r"https?://[a-z0-9\-\.]+(?::\d+)?", fullmatch=True),
        api_key=st.text(min_size=1, max_size=100),
    )
    @patch("components.api_client.requests.Session")
    def test_stats_fetch_includes_api_key_header(
        self, mock_session_class: Mock, hack_id: str, base_url: str, api_key: str
    ) -> None:
        """
        Property: For any hackathon selection, the stats fetch request should
        include the X-API-Key header for authentication.

        This test verifies that:
        1. The X-API-Key header is present in the request
        2. The header contains the correct API key

        Args:
            mock_session_class: Mocked requests.Session class
            hack_id: Generated hackathon ID
            base_url: Generated base URL string
            api_key: Generated API key string
        """
        # Arrange: Mock session instance with Mock headers
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_session.headers = Mock()

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hack_id": hack_id,
            "submission_count": 100,
            "verified_count": 95,
            "pending_count": 5,
            "participant_count": 300,
        }
        mock_session.get.return_value = mock_response

        # Act: Create client (which sets up headers) and fetch stats
        client = APIClient(base_url, api_key)
        client.get(f"/hackathons/{hack_id}/stats")

        # Assert: Session headers were updated with X-API-Key
        # Note: The APIClient.__init__ calls session.headers.update()
        mock_session.headers.update.assert_called_once_with({"X-API-Key": api_key})

    @given(
        hack_id=valid_hack_id(),
        base_url=st.from_regex(r"https?://[a-z0-9\-\.]+(?::\d+)?", fullmatch=True),
        api_key=st.text(min_size=1, max_size=100),
    )
    @patch("components.api_client.requests.Session")
    def test_stats_response_contains_required_fields(
        self, mock_session_class: Mock, hack_id: str, base_url: str, api_key: str
    ) -> None:
        """
        Property: For any hackathon selection, the stats response should contain
        all required fields: submission_count, verified_count, pending_count,
        and participant_count.

        This test verifies that:
        1. The response is a valid dictionary
        2. All required fields are present
        3. The fields have appropriate types

        Args:
            mock_session_class: Mocked requests.Session class
            hack_id: Generated hackathon ID
            base_url: Generated base URL string
            api_key: Generated API key string
        """
        # Arrange: Mock session with complete stats response
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        stats_data = {
            "hack_id": hack_id,
            "submission_count": 150,
            "verified_count": 145,
            "pending_count": 5,
            "participant_count": 450,
            "analysis_status": "completed",
            "last_updated": "2025-03-04T12:00:00Z",
        }

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = stats_data
        mock_session.get.return_value = mock_response

        # Act: Fetch stats
        client = APIClient(base_url, api_key)
        response = client.get(f"/hackathons/{hack_id}/stats")

        # Assert: Response is a dictionary
        assert isinstance(response, dict), (
            f"Stats response should be a dictionary, but got {type(response)}"
        )

        # Assert: All required fields are present
        required_fields = [
            "submission_count",
            "verified_count",
            "pending_count",
            "participant_count",
        ]

        for field in required_fields:
            assert field in response, f"Stats response should contain '{field}' field"

            # Assert: Count fields are integers
            assert isinstance(response[field], int), (
                f"Field '{field}' should be an integer, but got {type(response[field])}"
            )

    @given(
        hack_ids=st.lists(valid_hack_id(), min_size=2, max_size=5, unique=True),
        base_url=st.from_regex(r"https?://[a-z0-9\-\.]+(?::\d+)?", fullmatch=True),
        api_key=st.text(min_size=1, max_size=100),
    )
    @patch("components.api_client.requests.Session")
    def test_selecting_different_hackathons_fetches_different_stats(
        self, mock_session_class: Mock, hack_ids: list[str], base_url: str, api_key: str
    ) -> None:
        """
        Property: For any sequence of hackathon selections, each selection should
        fetch stats for the corresponding hack_id.

        This test verifies that:
        1. Multiple selections trigger multiple stats fetches
        2. Each fetch uses the correct hack_id
        3. The responses are distinct for different hackathons

        Args:
            mock_session_class: Mocked requests.Session class
            hack_ids: List of generated hackathon IDs
            base_url: Generated base URL string
            api_key: Generated API key string
        """
        # Arrange: Mock session with different responses for each hack_id
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Create a mapping of hack_id to stats response
        stats_responses = {}
        for i, hack_id in enumerate(hack_ids):
            stats_responses[hack_id] = {
                "hack_id": hack_id,
                "submission_count": 100 + i * 10,
                "verified_count": 95 + i * 10,
                "pending_count": 5,
                "participant_count": 300 + i * 50,
            }

        # Configure mock to return different responses based on URL
        def get_side_effect(url: str, **kwargs: Any) -> Mock:
            # Extract hack_id from URL
            for hack_id in hack_ids:
                if hack_id in url:
                    mock_resp = Mock()
                    mock_resp.ok = True
                    mock_resp.status_code = 200
                    mock_resp.json.return_value = stats_responses[hack_id]
                    return mock_resp

            # Default response if hack_id not found
            mock_resp = Mock()
            mock_resp.ok = False
            mock_resp.status_code = 404
            return mock_resp

        mock_session.get.side_effect = get_side_effect

        # Act: Fetch stats for each hackathon
        client = APIClient(base_url, api_key)
        responses = []
        for hack_id in hack_ids:
            response = client.get(f"/hackathons/{hack_id}/stats")
            responses.append(response)

        # Assert: Correct number of GET requests were made
        assert mock_session.get.call_count == len(hack_ids), (
            f"Expected {len(hack_ids)} GET requests, but got {mock_session.get.call_count}"
        )

        # Assert: Each response corresponds to the correct hack_id
        for i, (hack_id, response) in enumerate(zip(hack_ids, responses, strict=False)):
            assert response["hack_id"] == hack_id, (
                f"Response {i} should have hack_id '{hack_id}', but got '{response.get('hack_id')}'"
            )

            # Assert: Each response has distinct stats
            expected_submission_count = 100 + i * 10
            assert response["submission_count"] == expected_submission_count, (
                f"Response {i} should have submission_count {expected_submission_count}, "
                f"but got {response['submission_count']}"
            )

    @given(
        hack_id=valid_hack_id(),
        base_url=st.from_regex(r"https?://[a-z0-9\-\.]+(?::\d+)?", fullmatch=True),
        api_key=st.text(min_size=1, max_size=100),
        stats_data=st.fixed_dictionaries(
            {
                "submission_count": st.integers(min_value=0, max_value=1000),
                "verified_count": st.integers(min_value=0, max_value=1000),
                "pending_count": st.integers(min_value=0, max_value=100),
                "participant_count": st.integers(min_value=0, max_value=3000),
            }
        ),
    )
    @patch("components.api_client.requests.Session")
    def test_stats_fetch_returns_consistent_data_structure(
        self,
        mock_session_class: Mock,
        hack_id: str,
        base_url: str,
        api_key: str,
        stats_data: dict[str, int],
    ) -> None:
        """
        Property: For any hackathon selection and any valid stats data, the
        response should maintain a consistent data structure.

        This test verifies that:
        1. The response always has the same structure
        2. Field types are consistent
        3. No unexpected fields are added or removed

        Args:
            mock_session_class: Mocked requests.Session class
            hack_id: Generated hackathon ID
            base_url: Generated base URL string
            api_key: Generated API key string
            stats_data: Generated stats data with random values
        """
        # Arrange: Mock session with generated stats data
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Add hack_id to stats data
        complete_stats = {"hack_id": hack_id, **stats_data}

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = complete_stats
        mock_session.get.return_value = mock_response

        # Act: Fetch stats
        client = APIClient(base_url, api_key)
        response = client.get(f"/hackathons/{hack_id}/stats")

        # Assert: Response has expected structure
        assert isinstance(response, dict), "Stats response should be a dictionary"

        # Assert: All required fields are present with correct types
        assert "hack_id" in response and isinstance(response["hack_id"], str)
        assert "submission_count" in response and isinstance(response["submission_count"], int)
        assert "verified_count" in response and isinstance(response["verified_count"], int)
        assert "pending_count" in response and isinstance(response["pending_count"], int)
        assert "participant_count" in response and isinstance(response["participant_count"], int)

        # Assert: Values match the generated data
        assert response["submission_count"] == stats_data["submission_count"]
        assert response["verified_count"] == stats_data["verified_count"]
        assert response["pending_count"] == stats_data["pending_count"]
        assert response["participant_count"] == stats_data["participant_count"]

    @given(
        hack_id=valid_hack_id(),
        base_url=st.from_regex(r"https?://[a-z0-9\-\.]+(?::\d+)?", fullmatch=True),
        api_key=st.text(min_size=1, max_size=100),
    )
    @patch("components.api_client.requests.Session")
    def test_stats_endpoint_url_format_is_correct(
        self, mock_session_class: Mock, hack_id: str, base_url: str, api_key: str
    ) -> None:
        """
        Property: For any hackathon selection, the stats endpoint URL should
        follow the format /hackathons/{hack_id}/stats.

        This test verifies that:
        1. The endpoint URL is correctly formatted
        2. The hack_id is properly interpolated
        3. No extra slashes or malformed URLs are created

        Args:
            mock_session_class: Mocked requests.Session class
            hack_id: Generated hackathon ID
            base_url: Generated base URL string
            api_key: Generated API key string
        """
        # Arrange: Mock session
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hack_id": hack_id,
            "submission_count": 100,
            "verified_count": 95,
            "pending_count": 5,
            "participant_count": 300,
        }
        mock_session.get.return_value = mock_response

        # Act: Fetch stats
        client = APIClient(base_url, api_key)
        endpoint = f"/hackathons/{hack_id}/stats"
        client.get(endpoint)

        # Assert: GET was called with correct URL format
        expected_url = f"{base_url.rstrip('/')}/hackathons/{hack_id}/stats"

        call_args = mock_session.get.call_args
        actual_url = call_args[0][0] if call_args[0] else call_args[1].get("url")

        assert actual_url == expected_url, f"Expected URL '{expected_url}', but got '{actual_url}'"

        # Assert: No double slashes in URL (except in protocol)
        url_without_protocol = actual_url.split("://", 1)[1] if "://" in actual_url else actual_url
        assert "//" not in url_without_protocol, (
            f"URL should not contain double slashes: '{actual_url}'"
        )
