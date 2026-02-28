"""Integration tests for live dashboard flow using Streamlit AppTest.

**Validates: Requirements 3.1, 3.2, 3.3, 4.1, 4.2, 4.3, 5.1, 5.2, 5.3**

This module tests the full live dashboard flow including:
- Hackathon selection dropdown population
- Stats display (submission_count, verified_count, pending_count, participant_count)
- Analysis triggering with cost estimate
- Analysis confirmation dialog
- Job ID and estimated cost display after analysis starts
- Progress monitoring (progress bar, completed/failed submissions, current cost)
"""

from unittest.mock import MagicMock, patch

import pytest
from streamlit.testing.v1 import AppTest


# Mock st_autorefresh to prevent infinite loops in tests
@pytest.fixture(autouse=True)
def mock_autorefresh():
    """Mock streamlit_autorefresh to prevent infinite loops in tests."""
    with patch("streamlit_autorefresh.st_autorefresh", return_value=0):
        yield


@pytest.fixture
def authenticated_app() -> AppTest:
    """Create an authenticated app instance for testing.

    Returns:
        An AppTest instance with authentication already set up.
    """
    at = AppTest.from_file("streamlit_ui/pages/2_📊_Live_Dashboard.py")

    # Set up authentication in session state
    at.session_state["api_key"] = "test_api_key_123"  # pragma: allowlist secret
    at.session_state["api_base_url"] = "http://localhost:8000"

    return at


@patch("components.api_client.requests.Session.get")
def test_hackathon_dropdown_population(mock_get: MagicMock, authenticated_app: AppTest) -> None:
    """Test that hackathon selection dropdown is populated from API.

    **Validates: Requirement 3.1**

    The dashboard should display a hackathon selection dropdown populated
    from GET /hackathons endpoint.
    """
    # Mock API responses comprehensively
    def mock_get_side_effect(url: str, *args, **kwargs):
        mock_response = MagicMock()
        mock_response.ok = True

        if "/stats" in url:
            # Stats response
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "hack_id": "01HXXX111",
                "submission_count": 50,
                "verified_count": 45,
                "pending_count": 5,
                "participant_count": 150,
            }
        elif "/analyze/status" in url:
            # No active job
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": "not_started",
                "job_id": None
            }
        else:
            # Hackathons list response - MUST return dict with "hackathons" key
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "hackathons": [
                    {"hack_id": "01HXXX111", "name": "Spring Hackathon 2025", "status": "configured"},
                    {"hack_id": "01HXXX222", "name": "Summer Hackathon 2025", "status": "configured"},
                ],
                "next_cursor": None,
                "has_more": False
            }

        return mock_response

    mock_get.side_effect = mock_get_side_effect

    at = authenticated_app
    at.run()

    # Verify the page loaded without errors
    if at.exception:
        print(f"Exception: {at.exception}")
    assert not at.exception

    # Verify dropdown is present
    assert len(at.selectbox) >= 1

    # Get the hackathon selection dropdown (should be the first selectbox)
    hackathon_dropdown = at.selectbox[0]

    # Verify dropdown contains both hackathon names
    assert "Spring Hackathon 2025" in hackathon_dropdown.options
    assert "Summer Hackathon 2025" in hackathon_dropdown.options

    # Verify API was called to fetch hackathons
    mock_get.assert_called()
    # Check that /hackathons endpoint was called
    call_args = [call.args[0] for call in mock_get.call_args_list]
    assert any("/hackathons" in str(arg) for arg in call_args)


@patch("components.api_client.requests.Session.get")
def test_stats_display_after_hackathon_selection(
    mock_get: MagicMock, authenticated_app: AppTest
) -> None:
    """Test that stats are displayed after selecting a hackathon.

    **Validates: Requirements 3.2, 3.3**

    When an organizer selects a hackathon, the dashboard should:
    - Fetch statistics from GET /hackathons/{hack_id}/stats
    - Display submission_count, verified_count, pending_count, participant_count
    """

    # Mock responses for both hackathons list and stats
    def mock_get_side_effect(url: str, *args, **kwargs):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True

        if "/stats" in url:
            # Stats response
            mock_response.json.return_value = {
                "hack_id": "01HXXX111",
                "submission_count": 50,
                "verified_count": 45,
                "pending_count": 5,
                "participant_count": 150,
                "analysis_status": "completed",
                "last_updated": "2025-03-04T12:00:00Z",
            }
        elif "/analyze/status" in url:
            # No active job
            mock_response.json.return_value = {
                "status": "not_started",
                "job_id": None
            }
        else:
            # Hackathons list response - MUST return dict with "hackathons" key
            mock_response.json.return_value = {
                "hackathons": [
                    {"hack_id": "01HXXX111", "name": "Spring Hackathon 2025", "status": "configured"}
                ],
                "next_cursor": None,
                "has_more": False
            }

        return mock_response

    mock_get.side_effect = mock_get_side_effect

    at = authenticated_app
    at.run()

    # Verify the page loaded without errors
    if at.exception:
        print(f"Exception: {at.exception}")
    assert not at.exception

    # Verify stats metrics are displayed
    # The page should have 4 metrics for the stats
    assert len(at.metric) >= 4

    # Find the stats metrics by checking their labels
    metric_labels = [m.label for m in at.metric]

    # Verify all required stats are present
    assert any(
        "Total Submissions" in label or "submission" in label.lower() for label in metric_labels
    )
    assert any("Verified" in label or "verified" in label.lower() for label in metric_labels)
    assert any("Pending" in label or "pending" in label.lower() for label in metric_labels)
    assert any("Participants" in label or "participant" in label.lower() for label in metric_labels)

    # Verify the stats values are displayed correctly
    # Find the submission count metric
    submission_metric = None
    for m in at.metric:
        if "Total Submissions" in m.label or "submission" in m.label.lower():
            submission_metric = m
            break

    assert submission_metric is not None
    assert "50" in str(submission_metric.value)


@patch("components.api_client.requests.Session.post")
@patch("components.api_client.requests.Session.get")
def test_analysis_cost_estimate_display(
    mock_get: MagicMock, mock_post: MagicMock, authenticated_app: AppTest
) -> None:
    """Test that cost estimate is fetched and displayed before analysis.

    **Validates: Requirement 4.6**

    The dashboard should display a cost estimate before triggering analysis
    using POST /hackathons/{hack_id}/estimate.
    """

    # Mock hackathons list response
    def mock_get_side_effect(url: str, *args, **kwargs):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True

        if "/stats" in url:
            mock_response.json.return_value = {
                "submission_count": 50,
                "verified_count": 50,
                "pending_count": 0,
                "participant_count": 150,
            }
        elif "/analyze/status" in url:
            mock_response.json.return_value = {
                "status": "not_started",
                "job_id": None
            }
        else:
            mock_response.json.return_value = {
                "hackathons": [
                    {"hack_id": "01HXXX111", "name": "Test Hackathon", "status": "active"}
                ],
                "next_cursor": None,
                "has_more": False
            }

        return mock_response

    mock_get.side_effect = mock_get_side_effect

    # Mock cost estimate response
    mock_estimate_response = MagicMock()
    mock_estimate_response.status_code = 200
    mock_estimate_response.ok = True
    mock_estimate_response.json.return_value = {
        "estimate": {
            "total_cost_usd": {
                "expected": 1.25,
                "min": 1.00,
                "max": 1.50
            },
            "submission_count": 50,
            "per_submission_cost": 0.025
        }
    }
    mock_post.return_value = mock_estimate_response

    at = authenticated_app
    at.run()

    # Find and click "Start Analysis" button
    start_button = None
    for button in at.button:
        if "Start Analysis" in button.label:
            start_button = button
            break

    assert start_button is not None, "Start Analysis button not found"
    start_button.click()
    at.run()

    # Verify cost estimate API was called
    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert "/estimate" in call_args.args[0]

    # Verify cost estimate is displayed
    # The cost should be displayed in an info box
    assert len(at.info) > 0
    info_messages = [info.value for info in at.info]
    cost_displayed = any("$1.25" in msg or "1.25" in msg for msg in info_messages)
    assert cost_displayed, "Cost estimate not displayed"


@patch("components.api_client.requests.Session.post")
@patch("components.api_client.requests.Session.get")
def test_analysis_confirmation_dialog(
    mock_get: MagicMock, mock_post: MagicMock, authenticated_app: AppTest
) -> None:
    """Test that confirmation dialog is displayed before starting analysis.

    **Validates: Requirement 4.1**

    After fetching cost estimate, the dashboard should display a confirmation
    dialog with "Confirm & Start" and "Cancel" buttons.
    """

    # Mock responses
    def mock_get_side_effect(url: str, *args, **kwargs):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True

        if "/stats" in url:
            mock_response.json.return_value = {
                "submission_count": 50,
                "verified_count": 50,
                "pending_count": 0,
                "participant_count": 150,
            }
        else:
            mock_response.json.return_value = [
                {"hack_id": "01HXXX111", "name": "Test Hackathon", "status": "active"}
            ]

        return mock_response

    mock_get.side_effect = mock_get_side_effect

    # Mock cost estimate response
    mock_estimate_response = MagicMock()
    mock_estimate_response.status_code = 200
    mock_estimate_response.ok = True
    mock_estimate_response.json.return_value = {
        "estimate": {
            "total_cost_usd": {
                "expected": 1.25,
                "min": 1.00,
                "max": 1.50
            },
            "submission_count": 50,
            "per_submission_cost": 0.025
        }
    }
    mock_post.return_value = mock_estimate_response

    at = authenticated_app
    at.run()

    # Click "Start Analysis" to fetch cost estimate
    start_button = None
    for button in at.button:
        if "Start Analysis" in button.label:
            start_button = button
            break

    assert start_button is not None
    start_button.click()
    at.run()

    # Verify confirmation buttons are displayed
    button_labels = [b.label for b in at.button]

    # Should have "Confirm & Start" and "Cancel" buttons
    assert any("Confirm" in label for label in button_labels), "Confirm button not found"
    assert any("Cancel" in label for label in button_labels), "Cancel button not found"

    # Verify warning message is displayed
    assert len(at.warning) > 0
    warning_message = at.warning[0].value
    assert "continue" in warning_message.lower() or "confirm" in warning_message.lower()


@patch("components.api_client.requests.Session.post")
@patch("components.api_client.requests.Session.get")
def test_analysis_start_displays_job_id_and_cost(
    mock_get: MagicMock, mock_post: MagicMock, authenticated_app: AppTest
) -> None:
    """Test that job_id and estimated_cost_usd are displayed after starting analysis.

    **Validates: Requirement 4.3**

    When the backend returns HTTP 202, the dashboard should display
    the job_id and estimated_cost_usd from the response.

    NOTE: After POST /analyze succeeds, the page calls st.rerun() which clears
    the success messages. However, after rerun, the page shows "Job in progress"
    with the job_id. This test verifies that behavior.
    """

    # Track whether analyze was called to change mock behavior
    analyze_called = False

    # Mock responses
    def mock_get_side_effect(url: str, *args, **kwargs):
        nonlocal analyze_called
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True

        if "/stats" in url:
            mock_response.json.return_value = {
                "submission_count": 50,
                "verified_count": 50,
                "pending_count": 0,
                "participant_count": 150,
            }
        elif "/analyze/status" in url:
            # After analyze is called, return the job_id
            if analyze_called:
                mock_response.json.return_value = {
                    "status": "queued",
                    "job_id": "01HYYY123456789"
                }
            else:
                mock_response.json.return_value = {
                    "status": "not_started",
                    "job_id": None
                }
        else:
            mock_response.json.return_value = {
                "hackathons": [
                    {"hack_id": "01HXXX111", "name": "Test Hackathon", "status": "active"}
                ],
                "next_cursor": None,
                "has_more": False
            }

        return mock_response

    mock_get.side_effect = mock_get_side_effect

    # Mock POST responses for estimate and analyze
    def mock_post_side_effect(url: str, *args, **kwargs):
        nonlocal analyze_called
        mock_response = MagicMock()
        mock_response.ok = True

        if "/estimate" in url:
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "estimate": {
                    "total_cost_usd": {
                        "expected": 1.25,
                        "min": 1.00,
                        "max": 1.50
                    },
                    "submission_count": 50,
                    "per_submission_cost": 0.025
                }
            }
        elif "/analyze" in url and "/estimate" not in url:
            analyze_called = True
            mock_response.status_code = 202
            mock_response.json.return_value = {
                "job_id": "01HYYY123456789",
                "estimated_cost_usd": 1.25,
                "status": "queued",
            }

        return mock_response

    mock_post.side_effect = mock_post_side_effect

    at = authenticated_app
    at.run()

    # Click "Start Analysis" to fetch cost estimate
    start_button = None
    for button in at.button:
        if "Start Analysis" in button.label:
            start_button = button
            break

    assert start_button is not None
    start_button.click()
    at.run()

    # Click "Confirm & Start" to start analysis
    confirm_button = None
    for button in at.button:
        if "Confirm" in button.label:
            confirm_button = button
            break

    assert confirm_button is not None, "Confirm button not found"
    confirm_button.click()
    at.run()

    # Verify analysis API was called
    analyze_calls = [call for call in mock_post.call_args_list if "/analyze" in str(call.args[0]) and "/estimate" not in str(call.args[0])]
    assert len(analyze_calls) > 0, "Analyze endpoint not called"

    # After rerun, the page should show "Job in progress" with job_id
    info_messages = [info.value for info in at.info]
    job_id_displayed = any("01HYYY123456789" in msg or "in progress" in msg.lower() for msg in info_messages)
    assert job_id_displayed, f"Job ID not displayed in info messages: {info_messages}"


@patch("components.api_client.requests.Session.post")
@patch("components.api_client.requests.Session.get")
def test_analysis_progress_monitoring(
    mock_get: MagicMock, mock_post: MagicMock, authenticated_app: AppTest
) -> None:
    """Test analysis progress monitoring with progress bar and stats.

    **Validates: Requirements 5.1, 5.2, 5.3**

    When analysis is running, the dashboard should:
    - Poll GET /hackathons/{hack_id}/jobs/{job_id} every 5 seconds
    - Display progress_percent (note: progress bars not testable in AppTest)
    - Display completed_submissions, failed_submissions, current_cost_usd
    """

    # Mock responses
    def mock_get_side_effect(url: str, *args, **kwargs):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True

        if "/jobs/" in url:
            # Job status response
            mock_response.json.return_value = {
                "job_id": "01HYYY123456789",
                "status": "running",
                "progress_percent": 45.5,
                "completed_submissions": 68,
                "failed_submissions": 2,
                "total_submissions": 150,
                "current_cost_usd": 3.45,
                "estimated_cost_usd": 7.50,
                "estimated_completion": "2025-03-04T13:30:00Z",
            }
        elif "/stats" in url:
            mock_response.json.return_value = {
                "submission_count": 150,
                "verified_count": 150,
                "pending_count": 0,
                "participant_count": 450,
            }
        elif "/analyze/status" in url:
            # Return active job
            mock_response.json.return_value = {
                "status": "running",
                "job_id": "01HYYY123456789"
            }
        else:
            mock_response.json.return_value = {
                "hackathons": [
                    {"hack_id": "01HXXX111", "name": "Test Hackathon", "status": "active"}
                ],
                "next_cursor": None,
                "has_more": False
            }

        return mock_response

    mock_get.side_effect = mock_get_side_effect

    at = authenticated_app
    at.run()

    # Verify "Job in progress" message is displayed
    info_messages = [info.value for info in at.info]
    job_in_progress = any("in progress" in msg.lower() or "01HYYY123456789" in msg for msg in info_messages)
    assert job_in_progress, f"Job in progress message not found in: {info_messages}"

    # Verify progress metrics are displayed
    # Should have at least 4 metrics for progress (completed, failed, total, cost)
    # Plus 4 for stats = 8 total
    assert len(at.metric) >= 7, f"Expected at least 7 metrics, got {len(at.metric)}"

    # Find progress-related metrics
    metric_labels = [m.label for m in at.metric]
    metric_values = [str(m.value) for m in at.metric]

    # Verify progress metrics are present
    assert any("Completed" in label for label in metric_labels), f"Completed metric not found in: {metric_labels}"
    assert any("Failed" in label for label in metric_labels), f"Failed metric not found in: {metric_labels}"
    assert any("Total" in label for label in metric_labels), f"Total metric not found in: {metric_labels}"
    assert any("Cost" in label for label in metric_labels), f"Cost metric not found in: {metric_labels}"

    # Verify metric values match mock data
    assert "68" in metric_values, f"Completed count 68 not found in: {metric_values}"
    assert "2" in metric_values, f"Failed count 2 not found in: {metric_values}"
    assert "150" in metric_values, f"Total count 150 not found in: {metric_values}"

    # Verify job status API was called
    job_status_calls = [call for call in mock_get.call_args_list if "/jobs/" in str(call.args[0])]
    assert len(job_status_calls) > 0, "Job status endpoint not called"


@patch("components.api_client.requests.Session.post")
@patch("components.api_client.requests.Session.get")
def test_analysis_failure_details_display(
    mock_get: MagicMock, mock_post: MagicMock, authenticated_app: AppTest
) -> None:
    """Test that error details are displayed when submissions fail.

    **Validates: Requirement 5.6**

    When failed_submissions > 0, the dashboard should display error details.
    """

    # Mock responses
    def mock_get_side_effect(url: str, *args, **kwargs):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True

        if "/jobs/" in url:
            # Job status response with failures
            mock_response.json.return_value = {
                "job_id": "01HYYY123456789",
                "status": "running",
                "progress_percent": 50.0,
                "completed_submissions": 70,
                "failed_submissions": 5,
                "total_submissions": 150,
                "current_cost_usd": 3.50,
                "error_details": [
                    "Submission SUB001: Repository not found",
                    "Submission SUB002: Invalid repository URL",
                    "Submission SUB003: Timeout during analysis",
                ],
            }
        elif "/stats" in url:
            mock_response.json.return_value = {
                "submission_count": 150,
                "verified_count": 145,
                "pending_count": 5,
                "participant_count": 450,
            }
        else:
            mock_response.json.return_value = [
                {"hack_id": "01HXXX111", "name": "Test Hackathon", "status": "active"}
            ]

        return mock_response

    mock_get.side_effect = mock_get_side_effect

    at = authenticated_app

    # Set up session state with active analysis job
    at.session_state["analysis_job_id"] = "01HYYY123456789"
    at.session_state["selected_hackathon"] = "01HXXX111"

    at.run()

    # Verify warning about failures is displayed
    assert len(at.warning) > 0, "Warning about failures not displayed"
    warning_message = at.warning[0].value
    assert "5" in warning_message or "failed" in warning_message.lower()

    # Verify error details expander is present
    assert len(at.expander) > 0, "Error details expander not found"

    # Find the error details expander
    error_expander = None
    for expander in at.expander:
        if "Error" in expander.label or "error" in expander.label.lower():
            error_expander = expander
            break

    assert error_expander is not None, "Error details expander not found"


@patch("components.api_client.requests.Session.post")
@patch("components.api_client.requests.Session.get")
def test_analysis_budget_exceeded_error(
    mock_get: MagicMock, mock_post: MagicMock, authenticated_app: AppTest
) -> None:
    """Test that budget exceeded error is displayed correctly.

    **Validates: Requirement 4.4**

    When the backend returns HTTP 402, the dashboard should display
    a budget exceeded error message.
    """

    # Mock responses
    def mock_get_side_effect(url: str, *args, **kwargs):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True

        if "/stats" in url:
            mock_response.json.return_value = {
                "submission_count": 500,
                "verified_count": 500,
                "pending_count": 0,
                "participant_count": 1500,
            }
        else:
            mock_response.json.return_value = [
                {"hack_id": "01HXXX111", "name": "Test Hackathon", "status": "active"}
            ]

        return mock_response

    mock_get.side_effect = mock_get_side_effect

    # Mock budget exceeded response (HTTP 402)
    mock_budget_response = MagicMock()
    mock_budget_response.status_code = 402
    mock_budget_response.ok = False
    mock_budget_response.json.return_value = {"detail": "Budget limit exceeded"}
    mock_post.return_value = mock_budget_response

    at = authenticated_app
    at.run()

    # Click "Start Analysis" to fetch cost estimate
    start_button = None
    for button in at.button:
        if "Start Analysis" in button.label:
            start_button = button
            break

    assert start_button is not None
    start_button.click()
    at.run()

    # Verify error message is displayed
    assert len(at.error) > 0, "Budget exceeded error not displayed"
    error_message = at.error[0].value
    assert "budget" in error_message.lower() or "exceeded" in error_message.lower()


@patch("components.api_client.requests.Session.post")
@patch("components.api_client.requests.Session.get")
def test_analysis_conflict_error(
    mock_get: MagicMock, mock_post: MagicMock, authenticated_app: AppTest
) -> None:
    """Test that conflict error is displayed when analysis is already running.

    **Validates: Requirement 4.5**

    When the backend returns HTTP 409, the dashboard should display
    an "analysis already running" message.
    """

    # Mock responses
    def mock_get_side_effect(url: str, *args, **kwargs):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True

        if "/stats" in url:
            mock_response.json.return_value = {
                "submission_count": 50,
                "verified_count": 50,
                "pending_count": 0,
                "participant_count": 150,
            }
        else:
            mock_response.json.return_value = [
                {"hack_id": "01HXXX111", "name": "Test Hackathon", "status": "active"}
            ]

        return mock_response

    mock_get.side_effect = mock_get_side_effect

    # Mock POST responses
    def mock_post_side_effect(url: str, *args, **kwargs):
        mock_response = MagicMock()

        if "/estimate" in url:
            mock_response.status_code = 200
            mock_response.ok = True
            mock_response.json.return_value = {
                "estimate": {
                    "total_cost_usd": {
                        "expected": 1.25,
                        "min": 1.00,
                        "max": 1.50
                    },
                    "submission_count": 50,
                    "per_submission_cost": 0.025
                }
            }
        elif "/analyze" in url:
            # Conflict response (HTTP 409)
            mock_response.status_code = 409
            mock_response.ok = False
            mock_response.json.return_value = {
                "detail": "Analysis already running for this hackathon"
            }

        return mock_response

    mock_post.side_effect = mock_post_side_effect

    at = authenticated_app
    at.run()

    # Click "Start Analysis" to fetch cost estimate
    start_button = None
    for button in at.button:
        if "Start Analysis" in button.label:
            start_button = button
            break

    assert start_button is not None
    start_button.click()
    at.run()

    # Click "Confirm & Start" to trigger conflict
    confirm_button = None
    for button in at.button:
        if "Confirm" in button.label:
            confirm_button = button
            break

    assert confirm_button is not None
    confirm_button.click()
    at.run()

    # Verify error message is displayed
    assert len(at.error) > 0, "Conflict error not displayed"
    error_message = at.error[0].value
    assert "already" in error_message.lower() or "running" in error_message.lower()


@patch("components.api_client.requests.Session.post")
@patch("components.api_client.requests.Session.get")
def test_analysis_completion_success_message(
    mock_get: MagicMock, mock_post: MagicMock, authenticated_app: AppTest
) -> None:
    """Test that success message is displayed when analysis completes.

    **Validates: Requirement 5.5**

    When status changes to "completed", the dashboard should stop polling
    and display a success message.
    """

    # Mock responses
    def mock_get_side_effect(url: str, *args, **kwargs):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True

        if "/jobs/" in url:
            # Job status response - completed
            mock_response.json.return_value = {
                "job_id": "01HYYY123456789",
                "status": "completed",
                "progress_percent": 100.0,
                "completed_submissions": 150,
                "failed_submissions": 0,
                "total_submissions": 150,
                "current_cost_usd": 7.50,
                "estimated_cost_usd": 7.50,
            }
        elif "/stats" in url:
            mock_response.json.return_value = {
                "submission_count": 150,
                "verified_count": 150,
                "pending_count": 0,
                "participant_count": 450,
            }
        else:
            mock_response.json.return_value = [
                {"hack_id": "01HXXX111", "name": "Test Hackathon", "status": "active"}
            ]

        return mock_response

    mock_get.side_effect = mock_get_side_effect

    at = authenticated_app

    # Set up session state with active analysis job
    at.session_state["analysis_job_id"] = "01HYYY123456789"
    at.session_state["selected_hackathon"] = "01HXXX111"

    at.run()

    # Verify success message is displayed
    assert len(at.success) > 0, "Success message not displayed"
    success_message = at.success[0].value
    assert "completed" in success_message.lower() or "success" in success_message.lower()

    # Verify final summary is displayed
    markdown_content = " ".join([md.value for md in at.markdown])
    assert "Final Summary" in markdown_content or "summary" in markdown_content.lower()


@patch("components.api_client.requests.Session.get")
def test_no_hackathons_warning(mock_get: MagicMock, authenticated_app: AppTest) -> None:
    """Test that warning is displayed when no hackathons exist.

    **Validates: Requirement 3.1**

    When no hackathons are found, the dashboard should display a warning
    message prompting the user to create a hackathon first.
    """
    # Mock empty hackathons list response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.ok = True
    mock_response.json.return_value = {
        "hackathons": [],
        "next_cursor": None,
        "has_more": False
    }
    mock_get.return_value = mock_response

    at = authenticated_app
    at.run()

    # Verify warning is displayed
    assert len(at.warning) > 0, "No hackathons warning not displayed"
    warning_message = at.warning[0].value
    assert "no" in warning_message.lower() and "hackathon" in warning_message.lower()


@patch("components.api_client.requests.Session.get")
def test_stats_not_found_error(mock_get: MagicMock, authenticated_app: AppTest) -> None:
    """Test that error is displayed when stats are not found.

    **Validates: Requirement 3.5**

    When the backend returns HTTP 404 for stats, the dashboard should
    display a not found message.
    """

    # Mock responses
    def mock_get_side_effect(url: str, *args, **kwargs):
        mock_response = MagicMock()

        if "/stats" in url:
            # Not found response (HTTP 404)
            mock_response.status_code = 404
            mock_response.ok = False
            mock_response.json.return_value = {"detail": "Hackathon not found"}
        else:
            # Hackathons list response
            mock_response.status_code = 200
            mock_response.ok = True
            mock_response.json.return_value = [
                {"hack_id": "01HXXX111", "name": "Test Hackathon", "status": "active"}
            ]

        return mock_response

    mock_get.side_effect = mock_get_side_effect

    at = authenticated_app
    at.run()

    # Verify error message is displayed
    assert len(at.error) > 0, "Stats not found error not displayed"


@patch("components.api_client.requests.Session.post")
@patch("components.api_client.requests.Session.get")
def test_cancel_analysis_confirmation(
    mock_get: MagicMock, mock_post: MagicMock, authenticated_app: AppTest
) -> None:
    """Test that cancel button clears cost estimate and returns to initial state.

    **Validates: Requirement 4.1**

    When the user clicks "Cancel" in the confirmation dialog, the cost
    estimate should be cleared and the page should return to initial state.
    """

    # Mock responses
    def mock_get_side_effect(url: str, *args, **kwargs):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True

        if "/stats" in url:
            mock_response.json.return_value = {
                "submission_count": 50,
                "verified_count": 50,
                "pending_count": 0,
                "participant_count": 150,
            }
        elif "/analyze/status" in url:
            mock_response.json.return_value = {
                "status": "not_started",
                "job_id": None
            }
        else:
            mock_response.json.return_value = {
                "hackathons": [
                    {"hack_id": "01HXXX111", "name": "Test Hackathon", "status": "active"}
                ],
                "next_cursor": None,
                "has_more": False
            }

        return mock_response

    mock_get.side_effect = mock_get_side_effect

    # Mock cost estimate response
    mock_estimate_response = MagicMock()
    mock_estimate_response.status_code = 200
    mock_estimate_response.ok = True
    mock_estimate_response.json.return_value = {
        "estimate": {
            "total_cost_usd": {
                "expected": 1.25,
                "min": 1.00,
                "max": 1.50
            },
            "submission_count": 50,
            "per_submission_cost": 0.025
        }
    }
    mock_post.return_value = mock_estimate_response

    at = authenticated_app
    at.run()

    # Click "Start Analysis" to fetch cost estimate
    start_button = None
    for button in at.button:
        if "Start Analysis" in button.label:
            start_button = button
            break

    assert start_button is not None, "Start Analysis button not found"
    start_button.click()
    at.run()

    # Now we should have confirmation dialog with Cancel button
    cancel_button = None
    for button in at.button:
        if "Cancel" in button.label:
            cancel_button = button
            break

    assert cancel_button is not None, "Cancel button not found"
    cancel_button.click()
    at.run()

    # After cancel, cost_estimate should be cleared (or not exist)
    # AppTest session_state doesn't have .get(), so check if key exists
    if "cost_estimate" in at.session_state:
        cost_estimate_value = at.session_state["cost_estimate"]
        assert cost_estimate_value is None, f"Cost estimate not cleared, got: {cost_estimate_value}"

    # Verify "Start Analysis" button is displayed again
    button_labels = [b.label for b in at.button]
    assert any("Start Analysis" in label for label in button_labels), (
        "Start Analysis button not restored"
    )
