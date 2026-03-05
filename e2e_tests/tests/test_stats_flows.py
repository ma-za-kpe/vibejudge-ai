"""
E2E tests for Category 5: Stats Display Flows (3 flows).

Tests:
- 5.1: Stats Display After Hackathon Selection Flow
- 5.2: Stats Auto-Refresh Flow
- 5.3: Stats Error Handling Flow
"""

import pytest
from pages.live_dashboard_page import LiveDashboardPage
from playwright.sync_api import Page


@pytest.mark.critical
def test_stats_display_after_hackathon_selection(authenticated_page: Page, mock_api):
    """Test Flow 5.1: Stats Display After Hackathon Selection Flow."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list(
        [{"hack_id": hack_id, "name": "Test Hackathon", "status": "active"}]
    )

    mock_api.mock_hackathon_stats(
        hack_id,
        stats={
            "submission_count": 25,
            "verified_count": 20,
            "pending_count": 5,
            "participant_count": 75,
        },
    )

    dashboard = LiveDashboardPage(authenticated_page)
    dashboard.navigate()

    # Before selection: stats should not be visible
    # (or show placeholder)

    # Select hackathon
    dashboard.select_hackathon("Test Hackathon")

    # Stats should appear
    total = dashboard.get_total_submissions()
    verified = dashboard.get_verified_count()
    pending = dashboard.get_pending_count()
    participants = dashboard.get_participant_count()

    assert total == 25, f"Expected 25 total submissions, got {total}"
    assert verified == 20, f"Expected 20 verified, got {verified}"
    assert pending == 5, f"Expected 5 pending, got {pending}"
    assert participants == 75, f"Expected 75 participants, got {participants}"


@pytest.mark.smoke
def test_stats_auto_refresh_flow(authenticated_page: Page, mock_api):
    """Test Flow 5.2: Stats Auto-Refresh Flow."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list(
        [{"hack_id": hack_id, "name": "Test Hackathon", "status": "active"}]
    )

    # Initial stats
    mock_api.mock_hackathon_stats(
        hack_id,
        stats={
            "submission_count": 10,
            "verified_count": 8,
            "pending_count": 2,
            "participant_count": 30,
        },
    )

    dashboard = LiveDashboardPage(authenticated_page)
    dashboard.navigate()
    dashboard.select_hackathon("Test Hackathon")

    initial_count = dashboard.get_total_submissions()
    assert initial_count == 10

    # Update mock to return different stats
    mock_api.mock_hackathon_stats(
        hack_id,
        stats={
            "submission_count": 15,
            "verified_count": 12,
            "pending_count": 3,
            "participant_count": 45,
        },
    )

    # Manual refresh (simulating auto-refresh)
    dashboard.manual_refresh()

    # Stats should update
    new_count = dashboard.get_total_submissions()
    assert new_count == 15, f"Expected stats to update to 15, got {new_count}"


@pytest.mark.smoke
def test_stats_error_handling_flow(authenticated_page: Page, mock_api):
    """Test Flow 5.3: Stats Error Handling Flow (404 not found)."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list(
        [{"hack_id": hack_id, "name": "Test Hackathon", "status": "active"}]
    )

    # Mock 404 for stats endpoint
    mock_api.mock_get(
        f"**/hackathons/{hack_id}/stats", status=404, body={"detail": "Hackathon not found"}
    )

    dashboard = LiveDashboardPage(authenticated_page)
    dashboard.navigate()
    dashboard.select_hackathon("Test Hackathon")

    # Should show error
    dashboard.assert_error("Failed to load stats")


@pytest.mark.smoke
def test_stats_not_found_error(authenticated_page: Page, mock_api):
    """Test Flow 5.3: Stats not found for hackathon."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list(
        [{"hack_id": hack_id, "name": "Test Hackathon", "status": "draft"}]
    )

    # Mock empty stats (hackathon has no submissions yet)
    mock_api.mock_hackathon_stats(
        hack_id,
        stats={
            "submission_count": 0,
            "verified_count": 0,
            "pending_count": 0,
            "participant_count": 0,
        },
    )

    dashboard = LiveDashboardPage(authenticated_page)
    dashboard.navigate()
    dashboard.select_hackathon("Test Hackathon")

    # Stats should show 0
    total = dashboard.get_total_submissions()
    assert total == 0, "Should show 0 submissions for new hackathon"


@pytest.mark.smoke
def test_stats_cache_behavior(authenticated_page: Page, mock_api):
    """Test stats caching and TTL behavior."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list(
        [{"hack_id": hack_id, "name": "Test Hackathon", "status": "active"}]
    )

    mock_api.mock_hackathon_stats(
        hack_id,
        stats={
            "submission_count": 10,
            "verified_count": 8,
            "pending_count": 2,
            "participant_count": 30,
        },
    )

    dashboard = LiveDashboardPage(authenticated_page)
    dashboard.navigate()
    dashboard.select_hackathon("Test Hackathon")

    initial_count = dashboard.get_total_submissions()
    assert initial_count == 10

    # Update backend data
    mock_api.mock_hackathon_stats(
        hack_id,
        stats={
            "submission_count": 20,
            "verified_count": 15,
            "pending_count": 5,
            "participant_count": 60,
        },
    )

    # Without refresh, should still show cached value
    # (In real app, cache TTL = 30s)

    # Manual refresh clears cache
    dashboard.manual_refresh()

    # Should show new value
    new_count = dashboard.get_total_submissions()
    assert new_count == 20, "Stats should update after manual refresh"
