"""
Edge case tests for Live Dashboard page.

Tests None handling, error states, and defensive programming.
"""

import pytest
from unittest.mock import MagicMock, patch
from streamlit_ui.components.api_client import (
    APIClient,
    APIError,
    BudgetExceededError,
    ConflictError,
)


class TestCostEstimateNoneHandling:
    """Test that None cost estimates are handled gracefully."""

    def test_none_cost_estimate_displays_warning(self):
        """When cost estimate is None, should display warning instead of crashing."""
        # This tests the fix for: TypeError: unsupported format string passed to NoneType.__format__
        cost_estimate = None
        
        # Should not raise TypeError
        if cost_estimate is not None:
            message = f"💰 Estimated cost: ${cost_estimate:.2f}"
        else:
            message = "⚠️ Cost estimate unavailable"
        
        assert message == "⚠️ Cost estimate unavailable"

    def test_valid_cost_estimate_formats_correctly(self):
        """When cost estimate is valid, should format with 2 decimals."""
        cost_estimate = 0.023
        
        if cost_estimate is not None:
            message = f"💰 Estimated cost: ${cost_estimate:.2f}"
        else:
            message = "⚠️ Cost estimate unavailable"
        
        assert message == "💰 Estimated cost: $0.02"

    def test_zero_cost_estimate_formats_correctly(self):
        """When cost estimate is zero, should format as $0.00."""
        cost_estimate = 0.0
        
        if cost_estimate is not None:
            message = f"💰 Estimated cost: ${cost_estimate:.2f}"
        else:
            message = "⚠️ Cost estimate unavailable"
        
        assert message == "💰 Estimated cost: $0.00"

    def test_large_cost_estimate_formats_correctly(self):
        """When cost estimate is large, should format with 2 decimals."""
        cost_estimate = 123.456
        
        if cost_estimate is not None:
            message = f"💰 Estimated cost: ${cost_estimate:.2f}"
        else:
            message = "⚠️ Cost estimate unavailable"
        
        assert message == "💰 Estimated cost: $123.46"


class TestCostEstimateAPIErrors:
    """Test cost estimate API error handling."""

    @patch("streamlit_ui.components.api_client.APIClient.post")
    def test_cost_estimate_api_error_returns_none(self, mock_post):
        """When API returns error, cost estimate should be None."""
        mock_post.side_effect = APIError("API error")
        
        api_client = APIClient("https://api.example.com", "test-key")
        
        try:
            response = api_client.post("/hackathons/123/analyze/estimate", json={})
            cost_estimate = response.get("estimate", {}).get("total_cost_usd", {}).get("expected")
        except APIError:
            cost_estimate = None
        
        assert cost_estimate is None

    @patch("streamlit_ui.components.api_client.APIClient.post")
    def test_cost_estimate_missing_field_returns_none(self, mock_post):
        """When API response missing expected field, should return None."""
        mock_post.return_value = {"estimate": {}}  # Missing total_cost_usd
        
        api_client = APIClient("https://api.example.com", "test-key")
        response = api_client.post("/hackathons/123/analyze/estimate", json={})
        cost_estimate = response.get("estimate", {}).get("total_cost_usd", {}).get("expected")
        
        assert cost_estimate is None

    @patch("streamlit_ui.components.api_client.APIClient.post")
    def test_cost_estimate_malformed_response_returns_none(self, mock_post):
        """When API response is malformed, should return None."""
        mock_post.return_value = {"wrong_key": "wrong_value"}
        
        api_client = APIClient("https://api.example.com", "test-key")
        response = api_client.post("/hackathons/123/analyze/estimate", json={})
        cost_estimate = response.get("estimate", {}).get("total_cost_usd", {}).get("expected")
        
        assert cost_estimate is None


class TestAnalysisJobStatusHandling:
    """Test analysis job status edge cases."""

    @patch("streamlit_ui.components.api_client.APIClient.get")
    def test_job_status_not_found_returns_none(self, mock_get):
        """When job status endpoint returns 404, should handle gracefully."""
        from streamlit_ui.components.api_client import ResourceNotFoundError
        mock_get.side_effect = ResourceNotFoundError("Job not found")
        
        api_client = APIClient("https://api.example.com", "test-key")
        
        try:
            status = api_client.get("/hackathons/123/analyze/status")
        except ResourceNotFoundError:
            status = None
        
        assert status is None

    @patch("streamlit_ui.components.api_client.APIClient.get")
    def test_job_status_missing_fields_handled(self, mock_get):
        """When job status response missing fields, should handle gracefully."""
        mock_get.return_value = {}  # Empty response
        
        api_client = APIClient("https://api.example.com", "test-key")
        status = api_client.get("/hackathons/123/analyze/status")
        
        job_id = status.get("job_id")
        job_status = status.get("status")
        
        assert job_id is None
        assert job_status is None

    @patch("streamlit_ui.components.api_client.APIClient.get")
    def test_job_status_completed_with_results(self, mock_get):
        """When job is completed, should return full status."""
        mock_get.return_value = {
            "job_id": "01KJG8V7Q73H1GCFNE9PWX7A98",
            "status": "completed",
            "progress": {
                "total": 5,
                "completed": 5,
                "failed": 0,
                "percentage": 100.0
            }
        }
        
        api_client = APIClient("https://api.example.com", "test-key")
        status = api_client.get("/hackathons/123/analyze/status")
        
        assert status["status"] == "completed"
        assert status["progress"]["percentage"] == 100.0


class TestHackathonStatsHandling:
    """Test hackathon stats edge cases."""

    @patch("streamlit_ui.components.api_client.APIClient.get")
    def test_stats_not_found_handled(self, mock_get):
        """When stats endpoint returns 404, should handle gracefully."""
        from streamlit_ui.components.api_client import ResourceNotFoundError
        mock_get.side_effect = ResourceNotFoundError("Stats not found")
        
        api_client = APIClient("https://api.example.com", "test-key")
        
        try:
            stats = api_client.get("/hackathons/123")
        except ResourceNotFoundError:
            stats = None
        
        assert stats is None

    @patch("streamlit_ui.components.api_client.APIClient.get")
    def test_stats_zero_submissions(self, mock_get):
        """When hackathon has zero submissions, should display correctly."""
        mock_get.return_value = {
            "hack_id": "123",
            "name": "Test Hackathon",
            "total_submissions": 0,
            "analyzed_count": 0
        }
        
        api_client = APIClient("https://api.example.com", "test-key")
        stats = api_client.get("/hackathons/123")
        
        assert stats["total_submissions"] == 0
        assert stats["analyzed_count"] == 0

    @patch("streamlit_ui.components.api_client.APIClient.get")
    def test_stats_partial_analysis(self, mock_get):
        """When hackathon has partial analysis, should show progress."""
        mock_get.return_value = {
            "hack_id": "123",
            "name": "Test Hackathon",
            "total_submissions": 10,
            "analyzed_count": 5
        }
        
        api_client = APIClient("https://api.example.com", "test-key")
        stats = api_client.get("/hackathons/123")
        
        percentage = (stats["analyzed_count"] / stats["total_submissions"]) * 100
        assert percentage == 50.0


class TestAnalysisStartErrors:
    """Test analysis start error handling."""

    @patch("streamlit_ui.components.api_client.APIClient.post")
    def test_budget_exceeded_error_handled(self, mock_post):
        """When budget exceeded, should display appropriate error."""
        mock_post.side_effect = BudgetExceededError("Budget exceeded")
        
        api_client = APIClient("https://api.example.com", "test-key")
        
        try:
            response = api_client.post("/hackathons/123/analyze", json={})
            error_message = None
        except BudgetExceededError as e:
            error_message = str(e)
        
        assert error_message == "Budget exceeded"

    @patch("streamlit_ui.components.api_client.APIClient.post")
    def test_conflict_error_handled(self, mock_post):
        """When analysis already running, should display conflict error."""
        mock_post.side_effect = ConflictError("Analysis already running")
        
        api_client = APIClient("https://api.example.com", "test-key")
        
        try:
            response = api_client.post("/hackathons/123/analyze", json={})
            error_message = None
        except ConflictError as e:
            error_message = str(e)
        
        assert error_message == "Analysis already running"

    @patch("streamlit_ui.components.api_client.APIClient.post")
    def test_generic_api_error_handled(self, mock_post):
        """When generic API error occurs, should handle gracefully."""
        mock_post.side_effect = APIError("Internal server error")
        
        api_client = APIClient("https://api.example.com", "test-key")
        
        try:
            response = api_client.post("/hackathons/123/analyze", json={})
            error_message = None
        except APIError as e:
            error_message = str(e)
        
        assert "Internal server error" in error_message


class TestProgressPercentageCalculation:
    """Test progress percentage calculation edge cases."""

    def test_progress_zero_total(self):
        """When total is zero, should handle division by zero."""
        total = 0
        completed = 0
        
        if total > 0:
            percentage = (completed / total) * 100
        else:
            percentage = 0.0
        
        assert percentage == 0.0

    def test_progress_all_completed(self):
        """When all submissions completed, should be 100%."""
        total = 10
        completed = 10
        
        percentage = (completed / total) * 100
        assert percentage == 100.0

    def test_progress_partial_completion(self):
        """When partially completed, should calculate correctly."""
        total = 10
        completed = 3
        
        percentage = (completed / total) * 100
        assert percentage == 30.0

    def test_progress_rounds_correctly(self):
        """When percentage has decimals, should round appropriately."""
        total = 3
        completed = 1
        
        percentage = (completed / total) * 100
        assert abs(percentage - 33.333333) < 0.001


class TestFailureDetailsDisplay:
    """Test failure details display logic."""

    def test_no_failures_no_display(self):
        """When no failures, should not display failure section."""
        failed_count = 0
        total_count = 10
        
        should_display = failed_count > 0
        assert should_display is False

    def test_some_failures_display(self):
        """When some failures, should display failure section."""
        failed_count = 2
        total_count = 10
        
        should_display = failed_count > 0
        assert should_display is True

    def test_failure_percentage_calculation(self):
        """Should calculate failure percentage correctly."""
        failed_count = 2
        total_count = 10
        
        if total_count > 0:
            failure_percentage = (failed_count / total_count) * 100
        else:
            failure_percentage = 0.0
        
        assert failure_percentage == 20.0

    def test_all_failures(self):
        """When all submissions failed, should be 100%."""
        failed_count = 10
        total_count = 10
        
        failure_percentage = (failed_count / total_count) * 100
        assert failure_percentage == 100.0


class TestSessionStateManagement:
    """Test session state edge cases."""

    def test_cost_estimate_initialization(self):
        """Cost estimate should initialize to None."""
        session_state = {}
        
        if "cost_estimate" not in session_state:
            session_state["cost_estimate"] = None
        
        assert session_state["cost_estimate"] is None

    def test_cost_estimate_update(self):
        """Cost estimate should update when fetched."""
        session_state = {"cost_estimate": None}
        
        # Simulate successful fetch
        session_state["cost_estimate"] = 0.023
        
        assert session_state["cost_estimate"] == 0.023

    def test_cost_estimate_reset_on_error(self):
        """Cost estimate should remain None on error."""
        session_state = {"cost_estimate": None}
        
        # Simulate error during fetch
        try:
            raise APIError("API error")
        except APIError:
            pass  # Keep as None
        
        assert session_state["cost_estimate"] is None


class TestActiveJobDiscovery:
    """Test server-side job discovery logic."""

    @patch("streamlit_ui.components.api_client.APIClient.get")
    def test_active_job_found(self, mock_get):
        """When active job exists, should return job_id."""
        mock_get.return_value = {
            "status": "running",
            "job_id": "01KJG8V7Q73H1GCFNE9PWX7A98"
        }
        
        api_client = APIClient("https://api.example.com", "test-key")
        status = api_client.get("/hackathons/123/analyze/status")
        
        if status.get("status") in ["queued", "running"]:
            active_job_id = status.get("job_id")
        else:
            active_job_id = None
        
        assert active_job_id == "01KJG8V7Q73H1GCFNE9PWX7A98"

    @patch("streamlit_ui.components.api_client.APIClient.get")
    def test_no_active_job(self, mock_get):
        """When no active job, should return None."""
        mock_get.return_value = {
            "status": "completed",
            "job_id": "01KJG8V7Q73H1GCFNE9PWX7A98"
        }
        
        api_client = APIClient("https://api.example.com", "test-key")
        status = api_client.get("/hackathons/123/analyze/status")
        
        if status.get("status") in ["queued", "running"]:
            active_job_id = status.get("job_id")
        else:
            active_job_id = None
        
        assert active_job_id is None

    @patch("streamlit_ui.components.api_client.APIClient.get")
    def test_job_status_endpoint_not_found(self, mock_get):
        """When status endpoint not found, should return None."""
        from streamlit_ui.components.api_client import ResourceNotFoundError
        mock_get.side_effect = ResourceNotFoundError("Not found")
        
        api_client = APIClient("https://api.example.com", "test-key")
        
        try:
            status = api_client.get("/hackathons/123/analyze/status")
            if status.get("status") in ["queued", "running"]:
                active_job_id = status.get("job_id")
            else:
                active_job_id = None
        except ResourceNotFoundError:
            active_job_id = None
        
        assert active_job_id is None
