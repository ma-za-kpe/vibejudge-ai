"""
E2E tests for Category 4: Analysis Lifecycle Flows (10 flows).

Tests the complex 7-state analysis lifecycle state machine:
- STATE 1: No active job → Button visible
- STATE 2: Click Start → Fetch cost estimate
- STATE 3: Cost estimate shown → Confirmation dialog
- STATE 3a: Cancel → Back to STATE 1
- STATE 3b: Confirm → Analysis starts
- STATE 4: Job created → Button disappears, progress appears
- STATE 5: Job running → Progress updates
- STATE 6: Job completes → Success message, button reappears

Tests:
- 4.1: Complete Analysis Lifecycle (7 states)
- 4.2: Cost Estimate Flow
- 4.3: Budget Exceeded Error Flow (HTTP 402)
- 4.4: Concurrent Analysis Conflict Flow (HTTP 409)
- 4.5: Analysis Progress Polling Flow
- 4.6: Analysis Auto-Refresh Flow
- 4.7: Manual Refresh Flow
- 4.8: Failed Submissions Error Details Flow
- 4.9: Job Status Fetch Failure Flow
- 4.10: Analysis Cancel Flow
"""

import time

import pytest
from pages.live_dashboard_page import LiveDashboardPage
from playwright.sync_api import Page


@pytest.mark.critical
@pytest.mark.slow
def test_complete_analysis_lifecycle_with_mock(authenticated_page: Page, mock_api):
    """
    Test Flow 4.1: Complete 7-state analysis lifecycle with fast mock.

    This tests ALL state transitions in the analysis lifecycle.
    """
    hack_id = "test_hack_001"

    # Mock all endpoints
    mock_api.mock_hackathons_list(
        [{"hack_id": hack_id, "name": "Test Hackathon", "status": "configured"}]
    )
    mock_api.mock_hackathon_stats(hack_id)
    mock_api.mock_cost_estimate(hack_id, cost=15.75)
    mock_api.mock_start_analysis(hack_id, job_id="job_e2e_001", cost=15.75)
    mock_api.mock_analysis_lifecycle(hack_id, job_id="job_e2e_001")

    dashboard = LiveDashboardPage(authenticated_page)
    dashboard.navigate()
    dashboard.select_hackathon("Test Hackathon")

    # ========================================================================
    # STATE 1: No active job
    # ========================================================================
    assert dashboard.get_current_state() == "no_job", "Should start in no_job state"
    assert dashboard.is_analysis_button_visible(), "Start Analysis button should be visible"
    assert not dashboard.is_job_in_progress(), "No job should be in progress"

    # Take screenshot for visual regression
    dashboard.take_screenshot("state_1_no_job")

    # ========================================================================
    # STATE 2: Click Start Analysis → Fetch cost estimate
    # ========================================================================
    dashboard.start_analysis()

    # ========================================================================
    # STATE 3: Cost estimate displayed
    # ========================================================================
    assert dashboard.get_current_state() == "confirming", "Should be in confirming state"
    dashboard.assert_cost_estimate_displayed()

    cost = dashboard.get_cost_estimate()
    assert cost == 15.75, f"Expected cost $15.75, got ${cost}"

    dashboard.take_screenshot("state_3_cost_estimate")

    # ========================================================================
    # STATE 3a: Test cancel path
    # ========================================================================
    dashboard.cancel_analysis()

    # Should return to STATE 1
    assert dashboard.get_current_state() == "no_job", "Should return to no_job after cancel"
    assert dashboard.is_analysis_button_visible(), "Button should reappear after cancel"

    # ========================================================================
    # Go through confirm path
    # ========================================================================
    dashboard.start_analysis()
    dashboard.assert_cost_estimate_displayed()

    # STATE 3b: Confirm & Start
    dashboard.confirm_analysis()

    # ========================================================================
    # STATE 4: Job created
    # ========================================================================
    assert dashboard.get_current_state() == "running", "Should be in running state"
    assert not dashboard.is_analysis_button_visible(), "Button should disappear after start"
    assert dashboard.is_job_in_progress(), "Job progress section should appear"

    job_id = dashboard.get_job_id()
    assert job_id == "job_e2e_001", f"Expected job_id job_e2e_001, got {job_id}"

    dashboard.take_screenshot("state_4_job_created")

    # ========================================================================
    # STATE 5: Job running - Verify progress metrics
    # ========================================================================
    dashboard.assert_progress_valid()

    progress = dashboard.get_progress_percent()
    completed = dashboard.get_completed_count()
    total = dashboard.get_total_count()

    assert 0 <= progress <= 100, f"Progress should be 0-100, got {progress}"
    assert completed <= total, f"Completed ({completed}) should not exceed total ({total})"

    dashboard.take_screenshot("state_5_job_running")

    # ========================================================================
    # STATE 6: Wait for completion (mocked to complete after 3-4 polls)
    # ========================================================================
    # Poll manually 4 times to trigger mock completion
    for i in range(4):
        time.sleep(0.5)
        dashboard.manual_refresh()

        if dashboard.is_analysis_complete():
            break

    # Verify completion
    assert dashboard.is_analysis_complete(), "Analysis should complete"
    dashboard.assert_state_completed()

    # Get final summary
    summary = dashboard.get_final_summary()
    assert summary["completed"] == 10, "All submissions should complete"
    assert summary["failed"] == 0, "No failures expected"
    assert summary["cost"] == 12.45, "Final cost should match"

    dashboard.take_screenshot("state_6_completed")


@pytest.mark.smoke
@pytest.mark.critical
def test_budget_exceeded_during_estimate(authenticated_page: Page, mock_api):
    """Test Flow 4.3: Budget Exceeded Error during cost estimate (HTTP 402)."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list(
        [{"hack_id": hack_id, "name": "Test Hackathon", "status": "configured"}]
    )
    mock_api.mock_hackathon_stats(hack_id)

    # Mock 402 on estimate
    mock_api.mock_budget_exceeded(hack_id, endpoint="estimate")

    dashboard = LiveDashboardPage(authenticated_page)
    dashboard.navigate()
    dashboard.select_hackathon("Test Hackathon")

    # Click Start Analysis
    dashboard.start_analysis()

    # Should show budget error
    assert dashboard.has_budget_error(), "Should show budget exceeded error"
    dashboard.assert_error("Budget limit exceeded")

    # Button should stay visible (not in confirmation state)
    assert dashboard.is_analysis_button_visible(), "Button should remain visible after budget error"
    assert not dashboard.is_cost_estimate_visible(), "Cost estimate should not be shown"


@pytest.mark.smoke
@pytest.mark.critical
def test_budget_exceeded_during_start(authenticated_page: Page, mock_api):
    """Test Flow 4.3: Budget Exceeded Error during analysis start (HTTP 402)."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list(
        [{"hack_id": hack_id, "name": "Test Hackathon", "status": "configured"}]
    )
    mock_api.mock_hackathon_stats(hack_id)
    mock_api.mock_cost_estimate(hack_id, cost=10.0)

    # Estimate succeeds, but start fails with 402
    mock_api.mock_budget_exceeded(hack_id, endpoint="start")

    dashboard = LiveDashboardPage(authenticated_page)
    dashboard.navigate()
    dashboard.select_hackathon("Test Hackathon")

    # Start and confirm
    dashboard.start_analysis()
    dashboard.confirm_analysis()

    # Should show budget error
    assert dashboard.has_budget_error(), "Should show budget exceeded error"

    # Button should reappear (cost estimate cleared)
    time.sleep(1)  # Wait for state to update
    assert dashboard.is_analysis_button_visible(), "Button should reappear after budget error"


@pytest.mark.critical
def test_concurrent_analysis_conflict(authenticated_page: Page, mock_api):
    """Test Flow 4.4: Concurrent Analysis Conflict (HTTP 409)."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list(
        [{"hack_id": hack_id, "name": "Test Hackathon", "status": "configured"}]
    )
    mock_api.mock_hackathon_stats(hack_id)
    mock_api.mock_cost_estimate(hack_id, cost=10.0)

    # Estimate succeeds, but start returns 409
    mock_api.mock_analysis_conflict(hack_id)

    dashboard = LiveDashboardPage(authenticated_page)
    dashboard.navigate()
    dashboard.select_hackathon("Test Hackathon")

    dashboard.start_analysis()
    dashboard.confirm_analysis()

    # Should show conflict error
    assert dashboard.has_conflict_error(), "Should show conflict error"
    dashboard.assert_error("already running")

    # Button should reappear
    time.sleep(1)
    assert dashboard.is_analysis_button_visible(), "Button should reappear after conflict"


@pytest.mark.smoke
def test_analysis_progress_polling(authenticated_page: Page, mock_api):
    """Test Flow 4.5: Analysis Progress Polling Flow."""
    hack_id = "test_hack_001"
    job_id = "job_polling_001"

    mock_api.mock_hackathons_list(
        [{"hack_id": hack_id, "name": "Test Hackathon", "status": "configured"}]
    )
    mock_api.mock_hackathon_stats(hack_id)

    # Mock job already running
    mock_api.mock_analysis_status(hack_id, job_id=job_id, status="running")
    mock_api.mock_job_status(hack_id, job_id, status="running", progress=65.0)

    dashboard = LiveDashboardPage(authenticated_page)
    dashboard.navigate()
    dashboard.select_hackathon("Test Hackathon")

    # Should detect active job
    assert dashboard.is_job_in_progress(), "Should detect active job"
    assert not dashboard.is_analysis_button_visible(), "Button should be hidden"

    # Verify progress metrics
    progress = dashboard.get_progress_percent()
    assert progress == 65.0, f"Expected 65.0% progress, got {progress}%"

    completed = dashboard.get_completed_count()
    assert completed == 6, f"Expected 6 completed, got {completed}"  # 10 * 0.65 = 6.5 → 6

    dashboard.assert_progress_valid()


@pytest.mark.smoke
def test_manual_refresh(authenticated_page: Page, mock_api):
    """Test Flow 4.7: Manual Refresh Flow."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list(
        [{"hack_id": hack_id, "name": "Test Hackathon", "status": "configured"}]
    )
    mock_api.mock_hackathon_stats(
        hack_id,
        stats={
            "submission_count": 5,
            "verified_count": 5,
            "pending_count": 0,
            "participant_count": 15,
        },
    )

    dashboard = LiveDashboardPage(authenticated_page)
    dashboard.navigate()
    dashboard.select_hackathon("Test Hackathon")

    initial_count = dashboard.get_total_submissions()
    assert initial_count == 5

    # Update mock to return different stats
    mock_api.mock_hackathon_stats(
        hack_id,
        stats={
            "submission_count": 10,
            "verified_count": 9,
            "pending_count": 1,
            "participant_count": 30,
        },
    )

    # Manual refresh
    dashboard.manual_refresh()

    # Should show updated stats
    new_count = dashboard.get_total_submissions()
    assert new_count == 10, "Stats should update after manual refresh"


@pytest.mark.smoke
def test_failed_submissions_error_details(authenticated_page: Page, mock_api):
    """Test Flow 4.8: Failed Submissions Error Details Flow."""
    hack_id = "test_hack_001"
    job_id = "job_with_failures"

    mock_api.mock_hackathons_list(
        [{"hack_id": hack_id, "name": "Test Hackathon", "status": "configured"}]
    )
    mock_api.mock_hackathon_stats(hack_id)

    # Mock job with failures
    mock_api.mock_analysis_status(hack_id, job_id=job_id, status="running")
    mock_api.mock_get(
        f"**/hackathons/{hack_id}/jobs/{job_id}",
        status=200,
        body={
            "job_id": job_id,
            "status": "running",
            "progress_percent": 80.0,
            "completed_submissions": 8,
            "failed_submissions": 2,
            "total_submissions": 10,
            "current_cost_usd": 10.0,
            "error_details": [
                "Submission sub_003: Repository not accessible",
                "Submission sub_007: Analysis timeout",
            ],
        },
    )

    dashboard = LiveDashboardPage(authenticated_page)
    dashboard.navigate()
    dashboard.select_hackathon("Test Hackathon")

    # Should show job in progress
    assert dashboard.is_job_in_progress()

    # Should show failure warning
    warning = dashboard.get_failure_count_warning()
    assert "2 submission(s) failed" in warning

    # Should have error details expander
    assert dashboard.has_error_details_expander(), "Error details expander should be present"


@pytest.mark.smoke
def test_analysis_completion_balloons(authenticated_page: Page, mock_api):
    """Test that completion shows success message and balloons."""
    hack_id = "test_hack_001"
    job_id = "job_complete"

    mock_api.mock_hackathons_list(
        [{"hack_id": hack_id, "name": "Test Hackathon", "status": "configured"}]
    )
    mock_api.mock_hackathon_stats(hack_id)

    # Mock completed job
    mock_api.mock_analysis_status(hack_id, job_id=job_id, status="running")
    mock_api.mock_job_status(hack_id, job_id, status="completed", progress=100.0)

    dashboard = LiveDashboardPage(authenticated_page)
    dashboard.navigate()
    dashboard.select_hackathon("Test Hackathon")

    # Should show completion
    assert dashboard.is_analysis_complete(), "Should show completion message"
    dashboard.assert_success("Analysis completed successfully")

    # Verify final summary displayed
    summary = dashboard.get_final_summary()
    assert summary["completed"] == 10
    assert summary["total"] == 10


@pytest.mark.smoke
def test_cancel_analysis_confirmation(authenticated_page: Page, mock_api):
    """Test Flow 4.10: Analysis Cancel Flow (STATE 3a)."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list(
        [{"hack_id": hack_id, "name": "Test Hackathon", "status": "configured"}]
    )
    mock_api.mock_hackathon_stats(hack_id)
    mock_api.mock_cost_estimate(hack_id, cost=20.50)

    dashboard = LiveDashboardPage(authenticated_page)
    dashboard.navigate()
    dashboard.select_hackathon("Test Hackathon")

    # Start analysis
    dashboard.start_analysis()

    # Should show confirmation
    assert dashboard.is_cost_estimate_visible()
    cost = dashboard.get_cost_estimate()
    assert cost == 20.50

    # Cancel
    dashboard.cancel_analysis()

    # Should return to initial state
    assert dashboard.is_analysis_button_visible(), "Button should reappear after cancel"
    assert not dashboard.is_cost_estimate_visible(), "Cost estimate should disappear"
    assert dashboard.get_current_state() == "no_job", "Should return to no_job state"
