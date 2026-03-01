"""
E2E tests for Category 2: Hackathon Management Flows (7 flows).

Tests:
- 2.1: Hackathon Creation Flow
- 2.2: Hackathon Listing Flow
- 2.3: Hackathon Filtering Flow
- 2.4: Hackathon Sorting Flow
- 2.5: Hackathon Status Lifecycle Flow
- 2.6: Hackathon Search Flow
- 2.7: Hackathon Pagination Flow
"""

import pytest
from pages.create_hackathon_page import CreateHackathonPage
from pages.manage_hackathons_page import ManageHackathonsPage
from pages.settings_page import SettingsPage
from playwright.sync_api import Page


@pytest.mark.critical
def test_hackathon_creation_flow(authenticated_page: Page, mock_api):
    """Test Flow 2.1: Complete hackathon creation flow."""
    hack_id = "test_hack_001"

    mock_api.mock_create_hackathon(hack_id=hack_id)

    create_page = CreateHackathonPage(authenticated_page)
    create_page.navigate()

    # Fill form with valid data
    created_hack_id = create_page.create_hackathon(
        name="E2E Test Hackathon", description="Test hackathon for E2E testing", budget=100.0
    )

    # Verify creation
    create_page.assert_creation_success()
    assert created_hack_id == hack_id, f"Expected hack_id {hack_id}, got {created_hack_id}"


@pytest.mark.smoke
def test_hackathon_creation_validation(authenticated_page: Page):
    """Test Flow 2.1: Hackathon creation form validation."""
    create_page = CreateHackathonPage(authenticated_page)
    create_page.navigate()

    # Try to submit without name
    create_page.submit_form()

    # Should show validation error
    create_page.assert_validation_error("Name is required")


@pytest.mark.critical
def test_hackathon_listing_flow(authenticated_page: Page, mock_api):
    """Test Flow 2.2: Hackathon Listing Flow."""
    # Mock 5 hackathons
    hackathons = [
        {"hack_id": f"hack_{i}", "name": f"Test Hackathon {i}", "status": "active"}
        for i in range(1, 6)
    ]
    mock_api.mock_hackathons_list(hackathons)

    manage_page = ManageHackathonsPage(authenticated_page)
    manage_page.navigate()

    # Verify all hackathons displayed
    count = manage_page.get_hackathon_count()
    assert count == 5, f"Expected 5 hackathons, got {count}"

    names = manage_page.get_hackathon_names()
    assert "Test Hackathon 1" in str(names)


@pytest.mark.smoke
def test_hackathon_filtering_by_status(authenticated_page: Page, mock_api):
    """Test Flow 2.3: Hackathon Filtering Flow."""
    hackathons = [
        {"hack_id": "hack_1", "name": "Active Hack", "status": "active"},
        {"hack_id": "hack_2", "name": "Draft Hack", "status": "draft"},
        {"hack_id": "hack_3", "name": "Completed Hack", "status": "completed"},
    ]
    mock_api.mock_hackathons_list(hackathons)

    manage_page = ManageHackathonsPage(authenticated_page)
    manage_page.navigate()

    # Initial: all 3 visible
    initial_count = manage_page.get_hackathon_count()
    assert initial_count == 3

    # Filter by active
    manage_page.filter_by_status("Active")

    # Should show only 1
    filtered_count = manage_page.get_hackathon_count()
    assert filtered_count == 1, f"Expected 1 active hackathon, got {filtered_count}"


@pytest.mark.smoke
def test_hackathon_sorting_flow(authenticated_page: Page, mock_api):
    """Test Flow 2.4: Hackathon Sorting Flow."""
    hackathons = [
        {"hack_id": "hack_1", "name": "Zebra Hackathon", "status": "active"},
        {"hack_id": "hack_2", "name": "Alpha Hackathon", "status": "active"},
        {"hack_id": "hack_3", "name": "Beta Hackathon", "status": "active"},
    ]
    mock_api.mock_hackathons_list(hackathons)

    manage_page = ManageHackathonsPage(authenticated_page)
    manage_page.navigate()

    # Sort by name
    manage_page.sort_by("name")

    names = manage_page.get_hackathon_names()
    # First should be "Alpha Hackathon" after sorting
    assert "Alpha" in names[0], f"Expected Alpha first after sort, got {names[0]}"


@pytest.mark.critical
def test_hackathon_status_lifecycle_flow(authenticated_page: Page, mock_api):
    """Test Flow 2.5: Hackathon Status Lifecycle Flow (DRAFT → ACTIVE → PAUSED → ACTIVE → COMPLETED)."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list(
        [{"hack_id": hack_id, "name": "Test Hackathon", "status": "draft"}]
    )
    mock_api.mock_hackathon_stats(hack_id)

    settings = SettingsPage(authenticated_page)
    settings.navigate()
    settings.select_hackathon("Test Hackathon")

    # Should start in DRAFT
    status = settings.get_hackathon_status()
    assert status == "draft", f"Expected draft status, got {status}"

    # Activate
    settings.activate_hackathon()
    settings.assert_success("Hackathon activated")

    # Pause
    settings.pause_hackathon()
    settings.assert_success("Hackathon paused")

    # Resume
    settings.resume_hackathon()
    settings.assert_success("Hackathon resumed")

    # Complete
    settings.complete_hackathon()
    settings.assert_success("Hackathon completed")


@pytest.mark.smoke
def test_hackathon_search_flow(authenticated_page: Page, mock_api):
    """Test Flow 2.6: Hackathon Search Flow."""
    hackathons = [
        {"hack_id": "hack_1", "name": "AI Hackathon 2025", "status": "active"},
        {"hack_id": "hack_2", "name": "Blockchain Challenge", "status": "active"},
        {"hack_id": "hack_3", "name": "AI Innovation Summit", "status": "active"},
    ]
    mock_api.mock_hackathons_list(hackathons)

    manage_page = ManageHackathonsPage(authenticated_page)
    manage_page.navigate()

    # Initial: 3 hackathons
    assert manage_page.get_hackathon_count() == 3

    # Search for "AI"
    manage_page.search("AI")

    # Should show 2 hackathons with "AI" in name
    filtered_count = manage_page.get_hackathon_count()
    assert filtered_count == 2, f"Expected 2 hackathons with 'AI', got {filtered_count}"

    # Clear search
    manage_page.clear_search()

    # Should show all 3 again
    assert manage_page.get_hackathon_count() == 3


@pytest.mark.smoke
def test_hackathon_pagination_flow(authenticated_page: Page, mock_api):
    """Test Flow 2.7: Hackathon Pagination Flow."""
    # Mock 25 hackathons (assuming page size = 10)
    hackathons = [
        {"hack_id": f"hack_{i:03d}", "name": f"Hackathon {i}", "status": "active"}
        for i in range(1, 26)
    ]
    mock_api.mock_hackathons_list(hackathons)

    manage_page = ManageHackathonsPage(authenticated_page)
    manage_page.navigate()

    # Should have pagination
    assert manage_page.has_pagination(), "Pagination should be visible"

    # Page 1
    assert manage_page.get_current_page() == 1
    assert manage_page.get_total_pages() >= 2

    # Go to page 2
    manage_page.next_page()
    assert manage_page.get_current_page() == 2

    # Go back
    manage_page.previous_page()
    assert manage_page.get_current_page() == 1


@pytest.mark.smoke
def test_hackathon_empty_state(authenticated_page: Page, mock_api):
    """Test empty state: No hackathons."""
    mock_api.mock_hackathons_list([])

    manage_page = ManageHackathonsPage(authenticated_page)
    manage_page.navigate()

    # Should show no hackathons message
    manage_page.assert_no_hackathons_message()
    manage_page.assert_create_hackathon_prompt()

    # Count should be 0
    count = manage_page.get_hackathon_count()
    assert count == 0
