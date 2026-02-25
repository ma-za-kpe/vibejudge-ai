"""Property-based tests for analysis trigger functionality.

Feature: streamlit-organizer-dashboard
Tests universal properties of analysis trigger behavior using Hypothesis.
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

    Returns:
        A string matching ULID format (01 followed by 24 alphanumeric chars)
    """
    return draw(st.from_regex(r"01[A-Z0-9]{24}", fullmatch=True))


class TestAnalysisTriggerProperty:
    """Property 12: Analysis Trigger

    **Validates: Requirements 4.2**

    For any hackathon with pending submissions, clicking "Start Analysis"
    should send a POST request to /hackathons/{hack_id}/analyze.
    """

    @given(
        hack_id=valid_hack_id(),
        base_url=st.from_regex(r"https?://[a-z0-9\-\.]+(?::\d+)?", fullmatch=True),
        api_key=st.text(min_size=1, max_size=100),
    )
    @patch("components.api_client.requests.Session")
    def test_start_analysis_sends_post_request(
        self, mock_session_class: Mock, hack_id: str, base_url: str, api_key: str
    ) -> None:
        """Property: For any hackathon ID, clicking Start Analysis sends POST.

        Verifies POST request to /hackathons/{hack_id}/analyze endpoint.
        """
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 202
        mock_response.json.return_value = {
            "job_id": "01HYYY123456789ABCDEFGHIJK",
            "estimated_cost_usd": 5.50,
        }
        mock_session.post.return_value = mock_response

        client = APIClient(base_url, api_key)
        response = client.post(f"/hackathons/{hack_id}/analyze", json={})

        expected_url = f"{base_url}/hackathons/{hack_id}/analyze"
        mock_session.post.assert_called_once()

        call_args = mock_session.post.call_args
        actual_url = call_args[0][0] if call_args[0] else call_args[1].get("url")

        assert actual_url == expected_url
        assert response is not None
        assert "job_id" in response

    @given(
        hack_id=valid_hack_id(),
        base_url=st.from_regex(r"https?://[a-z0-9\-\.]+(?::\d+)?", fullmatch=True),
        api_key=st.text(min_size=1, max_size=100),
    )
    @patch("components.api_client.requests.Session")
    def test_analysis_trigger_includes_authentication(
        self, mock_session_class: Mock, hack_id: str, base_url: str, api_key: str
    ) -> None:
        """Property: Analysis trigger includes X-API-Key authentication header."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 202
        mock_response.json.return_value = {"job_id": "01HYYY", "estimated_cost_usd": 5.50}
        mock_session.post.return_value = mock_response

        APIClient(base_url, api_key)

        mock_session.headers.update.assert_called_once()
        update_call_args = mock_session.headers.update.call_args[0][0]

        assert "X-API-Key" in update_call_args
        assert update_call_args["X-API-Key"] == api_key

    @given(
        hack_id=valid_hack_id(),
        base_url=st.from_regex(r"https?://[a-z0-9\-\.]+(?::\d+)?", fullmatch=True),
        api_key=st.text(min_size=1, max_size=100),
    )
    @patch("components.api_client.requests.Session")
    def test_analysis_trigger_sends_empty_json_body(
        self, mock_session_class: Mock, hack_id: str, base_url: str, api_key: str
    ) -> None:
        """Property: Analysis trigger sends empty JSON body."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 202
        mock_response.json.return_value = {"job_id": "01HYYY", "estimated_cost_usd": 5.50}
        mock_session.post.return_value = mock_response

        client = APIClient(base_url, api_key)
        client.post(f"/hackathons/{hack_id}/analyze", json={})

        mock_session.post.assert_called_once()
        call_kwargs = mock_session.post.call_args[1]

        assert "json" in call_kwargs
        assert call_kwargs["json"] == {}

    @given(
        hack_ids=st.lists(valid_hack_id(), min_size=2, max_size=5, unique=True),
        base_url=st.from_regex(r"https?://[a-z0-9\-\.]+(?::\d+)?", fullmatch=True),
        api_key=st.text(min_size=1, max_size=100),
    )
    @patch("components.api_client.requests.Session")
    def test_analysis_trigger_uses_correct_hack_id(
        self, mock_session_class: Mock, hack_ids: list[str], base_url: str, api_key: str
    ) -> None:
        """Property: Each hackathon gets correct endpoint with its hack_id."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 202
        mock_response.json.return_value = {"job_id": "01HYYY", "estimated_cost_usd": 5.50}
        mock_session.post.return_value = mock_response

        client = APIClient(base_url, api_key)

        for hack_id in hack_ids:
            mock_session.post.reset_mock()
            client.post(f"/hackathons/{hack_id}/analyze", json={})

            expected_url = f"{base_url}/hackathons/{hack_id}/analyze"
            mock_session.post.assert_called_once()

            call_args = mock_session.post.call_args
            actual_url = call_args[0][0] if call_args[0] else call_args[1].get("url")

            assert actual_url == expected_url

    @given(
        hack_id=valid_hack_id(),
        base_url=st.from_regex(r"https?://[a-z0-9\-\.]+(?::\d+)?", fullmatch=True),
        api_key=st.text(min_size=1, max_size=100),
        job_id=st.from_regex(r"01[A-Z0-9]{24}", fullmatch=True),
        estimated_cost=st.floats(min_value=0.01, max_value=100.0),
    )
    @patch("components.api_client.requests.Session")
    def test_analysis_trigger_returns_job_id_and_cost(
        self,
        mock_session_class: Mock,
        hack_id: str,
        base_url: str,
        api_key: str,
        job_id: str,
        estimated_cost: float,
    ) -> None:
        """Property: Successful trigger returns job_id and estimated_cost_usd."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 202
        mock_response.json.return_value = {"job_id": job_id, "estimated_cost_usd": estimated_cost}
        mock_session.post.return_value = mock_response

        client = APIClient(base_url, api_key)
        response = client.post(f"/hackathons/{hack_id}/analyze", json={})

        assert "job_id" in response
        assert response["job_id"] == job_id
        assert "estimated_cost_usd" in response
        assert response["estimated_cost_usd"] == estimated_cost

    @given(
        hack_id=valid_hack_id(),
        base_url=st.from_regex(r"https?://[a-z0-9\-\.]+(?::\d+)?", fullmatch=True),
        api_key=st.text(min_size=1, max_size=100),
    )
    @patch("components.api_client.requests.Session")
    def test_analysis_trigger_uses_post_method_not_get(
        self, mock_session_class: Mock, hack_id: str, base_url: str, api_key: str
    ) -> None:
        """Property: Analysis trigger uses POST method, not GET or others."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 202
        mock_response.json.return_value = {"job_id": "01HYYY", "estimated_cost_usd": 5.50}
        mock_session.post.return_value = mock_response

        client = APIClient(base_url, api_key)
        client.post(f"/hackathons/{hack_id}/analyze", json={})

        mock_session.post.assert_called_once()
        mock_session.get.assert_not_called()

    @given(
        hack_id=valid_hack_id(),
        base_url=st.from_regex(r"https?://[a-z0-9\-\.]+(?::\d+)?", fullmatch=True),
        api_key=st.text(min_size=1, max_size=100),
    )
    @patch("components.api_client.requests.Session")
    def test_analysis_trigger_endpoint_format_is_correct(
        self, mock_session_class: Mock, hack_id: str, base_url: str, api_key: str
    ) -> None:
        """Property: Endpoint follows /hackathons/{hack_id}/analyze format."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 202
        mock_response.json.return_value = {"job_id": "01HYYY", "estimated_cost_usd": 5.50}
        mock_session.post.return_value = mock_response

        client = APIClient(base_url, api_key)
        client.post(f"/hackathons/{hack_id}/analyze", json={})

        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        actual_url = call_args[0][0] if call_args[0] else call_args[1].get("url")

        expected_url = f"{base_url}/hackathons/{hack_id}/analyze"
        assert actual_url == expected_url
        assert "/hackathons/" in actual_url
        assert hack_id in actual_url
        assert actual_url.endswith("/analyze")
        assert "?" not in actual_url
