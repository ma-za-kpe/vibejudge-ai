"""
E2E tests for Category 6: Results & Leaderboard Flows (12 flows).

Tests:
- 6.1: Leaderboard Viewing Flow
- 6.2: Search Filtering Flow
- 6.3: Sort Functionality Flow
- 6.4: Pagination Flow
- 6.5: Pagination Edge Cases
- 6.6: Leaderboard Table Display Flow
- 6.7: Team Detail Navigation Flow
- 6.8: Team Detail View Flow
- 6.9: Scorecard Display Flow (4 tabs)
- 6.10: Scorecard Not Found Flow
- 6.11: Individual Scorecards Flow
- 6.12: Back to Leaderboard Flow
"""
import pytest
from playwright.sync_api import Page
from pages.results_page import ResultsPage


@pytest.mark.smoke
@pytest.mark.critical
def test_leaderboard_display_with_submissions(authenticated_page: Page, mock_api):
    """Test Flow 6.1: Leaderboard Viewing Flow."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list([{"hack_id": hack_id, "name": "Test Hackathon", "status": "configured"}])
    mock_api.mock_leaderboard_with_submissions(hack_id, count=10)

    results = ResultsPage(authenticated_page)
    results.navigate()
    results.select_hackathon("Test Hackathon")

    # Verify leaderboard is displayed
    results.assert_leaderboard_displayed()

    # Verify stats
    total = results.get_total_submissions_stat()
    analyzed = results.get_analyzed_count_stat()

    assert total == 10, f"Expected 10 total submissions, got {total}"
    assert analyzed == 10, f"Expected 10 analyzed, got {analyzed}"

    # Verify submissions visible
    visible_count = results.get_visible_submission_count()
    assert visible_count == 10, f"Expected 10 visible submissions, got {visible_count}"


@pytest.mark.smoke
def test_search_filtering(authenticated_page: Page, mock_api):
    """Test Flow 6.2: Search Filtering Flow."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list([{"hack_id": hack_id, "name": "Test Hackathon", "status": "configured"}])
    mock_api.mock_leaderboard_with_submissions(hack_id, count=50)

    results = ResultsPage(authenticated_page)
    results.navigate()
    results.select_hackathon("Test Hackathon")

    # Initial: All submissions visible
    initial_count = results.get_visible_submission_count()
    assert initial_count == 50

    # Search for "Team 5" (matches Team 5, Team 50-59, etc.)
    results.search("Team 5")

    # Results should be filtered
    filtered_count = results.get_visible_submission_count()
    assert filtered_count < initial_count, "Search should filter results"
    assert filtered_count > 0, "Search should find some results"


@pytest.mark.smoke
def test_sort_functionality(authenticated_page: Page, mock_api):
    """Test Flow 6.3: Sort Functionality Flow."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list([{"hack_id": hack_id, "name": "Test Hackathon", "status": "configured"}])
    mock_api.mock_leaderboard_with_submissions(hack_id, count=10)

    results = ResultsPage(authenticated_page)
    results.navigate()
    results.select_hackathon("Test Hackathon")

    # Default sort: by score (highest first)
    first_team_score = results.get_team_name_at_rank(1)
    assert "Team 1" in first_team_score

    # Sort by team name
    results.sort_by("team_name")
    # After sorting by name, Team 1 should be first (alphabetically)

    # Sort by submission date
    results.sort_by("created_at")
    # Results should re-order


@pytest.mark.critical
def test_pagination_with_100_submissions(authenticated_page: Page, mock_api):
    """Test Flow 6.4-6.5: Pagination Flow and Edge Cases."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list([{"hack_id": hack_id, "name": "Test Hackathon", "status": "configured"}])
    mock_api.mock_leaderboard_with_submissions(hack_id, count=100)

    results = ResultsPage(authenticated_page)
    results.navigate()
    results.select_hackathon("Test Hackathon")

    # Page 1: Should show 50 submissions
    assert results.get_current_page() == 1
    assert results.get_total_pages() == 2
    assert results.get_visible_submission_count() == 50

    # Pagination controls
    assert results.is_button_disabled("⏮️ First"), "First should be disabled on page 1"
    assert results.is_button_disabled("◀️ Previous"), "Previous should be disabled on page 1"
    assert not results.is_button_disabled("Next ▶️"), "Next should be enabled"
    assert not results.is_button_disabled("Last ⏭️"), "Last should be enabled"

    results.take_screenshot("pagination_page_1")

    # Navigate to page 2
    results.click_pagination_button("Next ▶️")

    assert results.get_current_page() == 2
    assert results.get_visible_submission_count() == 50

    # Controls reversed
    assert not results.is_button_disabled("⏮️ First"), "First should be enabled on page 2"
    assert not results.is_button_disabled("◀️ Previous"), "Previous should be enabled"
    assert results.is_button_disabled("Next ▶️"), "Next should be disabled on last page"
    assert results.is_button_disabled("Last ⏭️"), "Last should be disabled on last page"

    results.take_screenshot("pagination_page_2")

    # Go back to page 1
    results.click_pagination_button("⏮️ First")
    assert results.get_current_page() == 1


@pytest.mark.smoke
def test_search_resets_pagination(authenticated_page: Page, mock_api):
    """Test Flow 6.5: Pagination Edge Case - Search resets to page 1."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list([{"hack_id": hack_id, "name": "Test Hackathon", "status": "configured"}])
    mock_api.mock_leaderboard_with_submissions(hack_id, count=100)

    results = ResultsPage(authenticated_page)
    results.navigate()
    results.select_hackathon("Test Hackathon")

    # Go to page 2
    results.click_pagination_button("Next ▶️")
    assert results.get_current_page() == 2

    # Search
    results.search("Team 5")

    # Should reset to page 1
    assert results.get_current_page() == 1


@pytest.mark.critical
def test_team_detail_navigation_and_back(authenticated_page: Page, mock_api):
    """Test Flow 6.7, 6.8, 6.12: Team Detail Navigation and Back."""
    hack_id = "test_hack_001"
    sub_id = "sub_001"

    mock_api.mock_hackathons_list([{"hack_id": hack_id, "name": "Test Hackathon", "status": "configured"}])
    mock_api.mock_leaderboard_with_submissions(hack_id, count=10)
    mock_api.mock_scorecard(hack_id, sub_id)
    mock_api.mock_individual_scorecards(hack_id, sub_id)

    results = ResultsPage(authenticated_page)
    results.navigate()
    results.select_hackathon("Test Hackathon")

    # Leaderboard view
    assert results.is_leaderboard_view()
    results.take_screenshot("leaderboard_view")

    # Click View Details for rank 1
    results.click_view_details_for_rank(1)

    # Should navigate to team detail
    assert results.is_team_detail_view()
    team_name = results.get_team_detail_name()
    assert team_name == "Team Awesome"

    results.take_screenshot("team_detail_view")

    # Verify tabs exist
    results.assert_team_detail_tabs_exist()

    # Click back button
    results.click_back_to_leaderboard()

    # Should return to leaderboard
    assert results.is_leaderboard_view()
    assert not results.is_team_detail_view()


@pytest.mark.smoke
def test_scorecard_tabs_display(authenticated_page: Page, mock_api):
    """Test Flow 6.9: Scorecard Display Flow - 4 Tabs."""
    hack_id = "test_hack_001"
    sub_id = "sub_001"

    mock_api.mock_hackathons_list([{"hack_id": hack_id, "name": "Test Hackathon", "status": "configured"}])
    mock_api.mock_leaderboard_with_submissions(hack_id, count=5)
    mock_api.mock_scorecard(hack_id, sub_id)
    mock_api.mock_individual_scorecards(hack_id, sub_id)

    results = ResultsPage(authenticated_page)
    results.navigate()
    results.select_hackathon("Test Hackathon")

    results.click_view_details_for_rank(1)

    # Tab 1: Overview
    results.click_scorecard_tab("📊 Overview")
    score = results.get_overall_score()
    assert score == 92.5

    confidence = results.get_confidence()
    assert confidence == 95.0  # 0.95 * 100

    recommendation = results.get_recommendation()
    assert "Must Interview" in recommendation

    results.take_screenshot("scorecard_tab_overview")

    # Tab 2: Agent Analysis
    results.click_scorecard_tab("🤖 Agent Analysis")
    results.take_screenshot("scorecard_tab_agents")

    # Tab 3: Repository
    results.click_scorecard_tab("📦 Repository")
    language = results.get_primary_language()
    assert language == "Python"

    commits = results.get_commit_count()
    assert commits == 45

    results.take_screenshot("scorecard_tab_repository")

    # Tab 4: Team Members
    results.click_scorecard_tab("👥 Team Members")
    has_members = results.has_team_members()
    assert has_members, "Should have team members data"

    results.take_screenshot("scorecard_tab_members")


@pytest.mark.smoke
def test_no_submissions_message(authenticated_page: Page, mock_api):
    """Test empty state: No submissions analyzed."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list([{"hack_id": hack_id, "name": "Test Hackathon", "status": "configured"}])
    mock_api.mock_get(f"**/hackathons/{hack_id}/leaderboard", status=200, body={
        "hack_id": hack_id,
        "total_submissions": 0,
        "analyzed_count": 0,
        "submissions": []
    })

    results = ResultsPage(authenticated_page)
    results.navigate()
    results.select_hackathon("Test Hackathon")

    # Should show no submissions message
    results.assert_no_submissions_message()

    # Should not show pagination or table
    visible_count = results.get_visible_submission_count()
    assert visible_count == 0


@pytest.mark.smoke
def test_scorecard_not_found_error(authenticated_page: Page, mock_api):
    """Test Flow 6.10: Scorecard Not Found Flow."""
    hack_id = "test_hack_001"
    sub_id = "sub_not_found"

    mock_api.mock_hackathons_list([{"hack_id": hack_id, "name": "Test Hackathon", "status": "configured"}])
    mock_api.mock_leaderboard_with_submissions(hack_id, count=5)

    # Mock 404 for scorecard
    mock_api.mock_get(f"**/hackathons/{hack_id}/submissions/{sub_id}/scorecard", status=404, body={
        "detail": "Scorecard not found"
    })

    results = ResultsPage(authenticated_page)
    results.navigate()
    results.select_hackathon("Test Hackathon")

    # Click View Details (will try to load non-existent scorecard)
    results.click_view_details_for_rank(1)

    # Should show error
    results.assert_error("Failed to load scorecard")
