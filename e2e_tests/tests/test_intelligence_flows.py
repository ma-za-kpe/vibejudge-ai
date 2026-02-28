"""
E2E tests for Category 7: Intelligence Insights Flows (5 flows).

Tests:
- 7.1: Intelligence Page Display Flow
- 7.2: Tech Stack Analysis Flow
- 7.3: Team Size Distribution Flow
- 7.4: AI Usage Insights Flow
- 7.5: Insights Filtering Flow
"""
import pytest
from playwright.sync_api import Page
from pages.intelligence_page import IntelligencePage


@pytest.mark.critical
def test_intelligence_page_display_flow(authenticated_page: Page, mock_api):
    """Test Flow 7.1: Intelligence Page Display Flow with all sections."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list([{
        "hack_id": hack_id,
        "name": "Test Hackathon",
        "status": "active"
    }])

    # Mock intelligence insights endpoint
    mock_api.mock_get(f"**/hackathons/{hack_id}/intelligence", status=200, body={
        "top_teams": [
            {"rank": 1, "team_name": "Team Alpha", "score": 95.0},
            {"rank": 2, "team_name": "Team Beta", "score": 92.5},
            {"rank": 3, "team_name": "Team Gamma", "score": 90.0},
        ],
        "tech_stack": {
            "Python": 45.0,
            "JavaScript": 30.0,
            "Go": 15.0,
            "Rust": 10.0
        },
        "team_sizes": {
            "average": 3.5,
            "largest": 5,
            "smallest": 2
        },
        "ai_usage": {
            "percentage": 35.0,
            "policy": "ai_assisted"
        }
    })

    intelligence = IntelligencePage(authenticated_page)
    intelligence.navigate()
    intelligence.select_hackathon("Test Hackathon")

    # Verify all sections exist
    assert intelligence.has_top_teams_section(), "Top teams section should exist"
    assert intelligence.has_tech_stack_analysis(), "Tech stack section should exist"
    assert intelligence.has_team_size_analysis(), "Team size section should exist"
    assert intelligence.has_ai_usage_insights(), "AI usage section should exist"


@pytest.mark.critical
def test_tech_stack_analysis_flow(authenticated_page: Page, mock_api):
    """Test Flow 7.2: Tech Stack Analysis Flow."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list([{
        "hack_id": hack_id,
        "name": "Test Hackathon",
        "status": "active"
    }])

    mock_api.mock_get(f"**/hackathons/{hack_id}/intelligence", status=200, body={
        "tech_stack": {
            "Python": 50.0,
            "JavaScript": 30.0,
            "TypeScript": 15.0,
            "Go": 5.0
        }
    })

    intelligence = IntelligencePage(authenticated_page)
    intelligence.navigate()
    intelligence.select_hackathon("Test Hackathon")

    # Verify most popular language
    most_popular = intelligence.get_most_popular_language()
    assert most_popular == "Python", f"Expected Python, got {most_popular}"

    # Verify percentage
    python_pct = intelligence.get_language_percentage("Python")
    assert python_pct == 50.0, f"Expected 50%, got {python_pct}%"


@pytest.mark.smoke
def test_team_size_distribution_flow(authenticated_page: Page, mock_api):
    """Test Flow 7.3: Team Size Distribution Flow."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list([{
        "hack_id": hack_id,
        "name": "Test Hackathon",
        "status": "active"
    }])

    mock_api.mock_get(f"**/hackathons/{hack_id}/intelligence", status=200, body={
        "team_sizes": {
            "average": 3.8,
            "largest": 5,
            "smallest": 2,
            "distribution": {
                "2": 10,
                "3": 20,
                "4": 15,
                "5": 5
            }
        }
    })

    intelligence = IntelligencePage(authenticated_page)
    intelligence.navigate()
    intelligence.select_hackathon("Test Hackathon")

    # Verify team size metrics
    avg_size = intelligence.get_average_team_size()
    assert avg_size == 3.8, f"Expected avg 3.8, got {avg_size}"

    largest = intelligence.get_largest_team_size()
    assert largest == 5, f"Expected largest 5, got {largest}"

    smallest = intelligence.get_smallest_team_size()
    assert smallest == 2, f"Expected smallest 2, got {smallest}"


@pytest.mark.smoke
def test_ai_usage_insights_flow(authenticated_page: Page, mock_api):
    """Test Flow 7.4: AI Usage Insights Flow."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list([{
        "hack_id": hack_id,
        "name": "Test Hackathon",
        "status": "active"
    }])

    mock_api.mock_get(f"**/hackathons/{hack_id}/intelligence", status=200, body={
        "ai_usage": {
            "percentage": 42.5,
            "policy": "ai_assisted",
            "flagged_count": 17,
            "total_analyzed": 40
        }
    })

    intelligence = IntelligencePage(authenticated_page)
    intelligence.navigate()
    intelligence.select_hackathon("Test Hackathon")

    # Verify AI usage percentage
    ai_pct = intelligence.get_ai_usage_percentage()
    assert ai_pct == 42.5, f"Expected 42.5%, got {ai_pct}%"

    # Verify policy
    policy = intelligence.get_ai_policy_mode()
    assert "ai_assisted" in policy.lower(), f"Expected ai_assisted policy, got {policy}"


@pytest.mark.smoke
def test_insights_filtering_flow(authenticated_page: Page, mock_api):
    """Test Flow 7.5: Insights Filtering Flow."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list([{
        "hack_id": hack_id,
        "name": "Test Hackathon",
        "status": "active"
    }])

    mock_api.mock_get(f"**/hackathons/{hack_id}/intelligence", status=200, body={
        "top_teams": [
            {"rank": 1, "team_name": "Team A", "score": 95.0, "recommendation": "must_interview"},
            {"rank": 2, "team_name": "Team B", "score": 85.0, "recommendation": "strong_consider"},
            {"rank": 3, "team_name": "Team C", "score": 75.0, "recommendation": "consider"},
        ]
    })

    intelligence = IntelligencePage(authenticated_page)
    intelligence.navigate()
    intelligence.select_hackathon("Test Hackathon")

    # Apply score filter
    intelligence.filter_by_score_range(min_score=80.0, max_score=100.0)

    # Should filter to top 2 teams
    visible_count = intelligence.get_top_teams_count()
    assert visible_count == 2, f"Expected 2 teams in range, got {visible_count}"


@pytest.mark.smoke
def test_insights_export_flow(authenticated_page: Page, mock_api):
    """Test insights export functionality."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list([{
        "hack_id": hack_id,
        "name": "Test Hackathon",
        "status": "active"
    }])

    mock_api.mock_get(f"**/hackathons/{hack_id}/intelligence", status=200, body={
        "top_teams": [{"rank": 1, "team_name": "Team A", "score": 95.0}]
    })

    intelligence = IntelligencePage(authenticated_page)
    intelligence.navigate()
    intelligence.select_hackathon("Test Hackathon")

    # Export insights
    if intelligence.has_export_button():
        intelligence.click_export()
        # Should trigger download


@pytest.mark.smoke
def test_intelligence_empty_state(authenticated_page: Page, mock_api):
    """Test empty state: No data for insights."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list([{
        "hack_id": hack_id,
        "name": "Test Hackathon",
        "status": "draft"
    }])

    # Mock 404 or empty response
    mock_api.mock_get(f"**/hackathons/{hack_id}/intelligence", status=200, body={
        "top_teams": [],
        "tech_stack": {},
        "team_sizes": None,
        "ai_usage": None
    })

    intelligence = IntelligencePage(authenticated_page)
    intelligence.navigate()
    intelligence.select_hackathon("Test Hackathon")

    # Should show no data message
    intelligence.assert_no_data_message()


@pytest.mark.smoke
def test_intelligence_insufficient_data(authenticated_page: Page, mock_api):
    """Test insufficient data warning (< 5 submissions)."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list([{
        "hack_id": hack_id,
        "name": "Test Hackathon",
        "status": "active"
    }])

    # Mock response with warning
    mock_api.mock_get(f"**/hackathons/{hack_id}/intelligence", status=200, body={
        "warning": "Insufficient data for meaningful insights (minimum 5 submissions required)",
        "top_teams": [{"rank": 1, "team_name": "Team A", "score": 90.0}]
    })

    intelligence = IntelligencePage(authenticated_page)
    intelligence.navigate()
    intelligence.select_hackathon("Test Hackathon")

    # Should show warning
    intelligence.assert_insufficient_data_message()
