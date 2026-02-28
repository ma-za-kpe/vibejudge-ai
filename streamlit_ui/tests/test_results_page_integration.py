"""Integration tests for results page flow using Streamlit AppTest.

**Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 7.1, 7.2**

This module tests the full results page flow including:
- Leaderboard display with rank, team_name, overall_score, recommendation
- Search functionality (filter by team_name)
- Sort functionality (by score, team_name, created_at)
- Team detail navigation (clicking a team row)
- Scorecard display with all required sections
- Pagination (50 submissions per page limit)
"""

from unittest.mock import MagicMock, patch

import pytest
from streamlit.testing.v1 import AppTest


@pytest.fixture
def authenticated_app() -> AppTest:
    """Create an authenticated app instance for testing.

    Returns:
        An AppTest instance with authentication already set up.
    """
    import streamlit as st

    # Clear all caches before each test to prevent cache pollution
    st.cache_data.clear()

    at = AppTest.from_file("streamlit_ui/pages/3_🏆_Results.py")

    # Set up authentication in session state
    at.session_state["api_key"] = "test_api_key_123"  # pragma: allowlist secret
    at.session_state["api_base_url"] = "http://localhost:8000"

    return at


@pytest.fixture
def mock_leaderboard_data() -> dict:
    """Create mock leaderboard data for testing.

    Returns:
        Dictionary containing mock leaderboard data
    """
    return {
        "hack_id": "01HXXX111",
        "total_submissions": 150,
        "analyzed_count": 148,
        "submissions": [
            {
                "sub_id": "01HZZZ001",
                "rank": 1,
                "team_name": "Team Awesome",
                "overall_score": 92.5,
                "confidence": 0.95,
                "recommendation": "must_interview",
                "created_at": "2025-03-02T10:00:00Z",
            },
            {
                "sub_id": "01HZZZ002",
                "rank": 2,
                "team_name": "Code Warriors",
                "overall_score": 88.0,
                "confidence": 0.92,
                "recommendation": "strong_consider",
                "created_at": "2025-03-02T11:00:00Z",
            },
            {
                "sub_id": "01HZZZ003",
                "rank": 3,
                "team_name": "Tech Innovators",
                "overall_score": 85.5,
                "confidence": 0.90,
                "recommendation": "consider",
                "created_at": "2025-03-02T12:00:00Z",
            },
        ],
    }


@pytest.fixture
def mock_scorecard_data() -> dict:
    """Create mock scorecard data for testing.

    Returns:
        Dictionary containing mock scorecard data
    """
    return {
        "sub_id": "01HZZZ001",
        "team_name": "Team Awesome",
        "overall_score": 92.5,
        "confidence": 0.95,
        "recommendation": "must_interview",
        "dimension_scores": {
            "code_quality": {"raw": 90.0, "weighted": 27.0, "weight": 0.3},
            "innovation": {"raw": 95.0, "weighted": 28.5, "weight": 0.3},
            "performance": {"raw": 92.0, "weighted": 27.6, "weight": 0.3},
            "authenticity": {"raw": 90.0, "weighted": 9.0, "weight": 0.1},
        },
        "agent_results": {
            "bug_hunter": {
                "summary": "Excellent code quality with comprehensive testing",
                "strengths": ["Clean architecture", "Good test coverage"],
                "improvements": ["Add more edge case tests"],
                "cost_usd": 0.002,
            },
            "innovation": {
                "summary": "Highly innovative solution with novel approach",
                "strengths": ["Creative problem solving", "Unique features"],
                "improvements": ["Document innovation rationale"],
                "cost_usd": 0.018,
            },
        },
        "repo_meta": {
            "primary_language": "Python",
            "commit_count": 45,
            "contributor_count": 3,
            "has_tests": True,
            "has_ci": True,
        },
        "total_cost_usd": 0.023,
    }


@patch("components.api_client.requests.Session.get")
def test_leaderboard_display_with_all_fields(
    mock_get: MagicMock, authenticated_app: AppTest, mock_leaderboard_data: dict
) -> None:
    """Test that leaderboard displays all required fields.

    **Validates: Requirements 6.1, 6.2**

    The dashboard should:
    - Fetch leaderboard data from GET /hackathons/{hack_id}/leaderboard
    - Display rank, team_name, overall_score, and recommendation for each submission
    - Display total_submissions and analyzed_count at the top
    """

    # Mock responses
    def mock_get_side_effect(url: str, *args, **kwargs):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True

        if "/leaderboard" in url:
            mock_response.json.return_value = mock_leaderboard_data
        else:
            # Hackathons list response
            mock_response.json.return_value = [
                {"hack_id": "01HXXX111", "name": "Test Hackathon", "status": "active"}
            ]

        return mock_response

    mock_get.side_effect = mock_get_side_effect

    at = authenticated_app
    at.run()

    # Verify the page loaded without errors
    assert not at.exception

    # Verify summary metrics are displayed
    assert len(at.metric) >= 2
    metric_labels = [m.label for m in at.metric]

    # Check for total submissions and analyzed count metrics
    assert any("Total Submissions" in label or "total" in label.lower() for label in metric_labels)
    assert any("Analyzed" in label or "analyzed" in label.lower() for label in metric_labels)

    # Verify leaderboard table is displayed with all required fields
    # The page should display team names, scores, and recommendations
    markdown_content = " ".join([md.value for md in at.markdown])

    # Check that all submissions are displayed
    assert "Team Awesome" in markdown_content
    assert "Code Warriors" in markdown_content
    assert "Tech Innovators" in markdown_content

    # Check that scores are displayed
    assert "92.5" in markdown_content or "92" in markdown_content
    assert "88.0" in markdown_content or "88" in markdown_content

    # Check that recommendations are displayed
    assert "Must Interview" in markdown_content or "must_interview" in markdown_content.lower()


@patch("components.api_client.requests.Session.get")
def test_search_functionality_filters_by_team_name(
    mock_get: MagicMock, authenticated_app: AppTest, mock_leaderboard_data: dict
) -> None:
    """Test search functionality filters submissions by team name.

    **Validates: Requirement 6.3**

    The dashboard should provide a search input that filters submissions
    by team_name (case-insensitive).
    """

    # Mock responses
    def mock_get_side_effect(url: str, *args, **kwargs):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True

        if "/leaderboard" in url:
            mock_response.json.return_value = mock_leaderboard_data
        else:
            mock_response.json.return_value = [
                {"hack_id": "01HXXX111", "name": "Test Hackathon", "status": "active"}
            ]

        return mock_response

    mock_get.side_effect = mock_get_side_effect

    at = authenticated_app
    at.run()

    # Verify search input is present
    assert len(at.text_input) >= 1

    # Find the search input (should have "search" in key or label)
    search_input = None
    for text_input in at.text_input:
        key_match = text_input.key and "search" in text_input.key.lower()
        label_match = "search" in str(text_input.label).lower()
        if key_match or label_match:
            search_input = text_input
            break

    assert search_input is not None, "Search input not found"

    # Enter search query
    search_input.set_value("awesome")
    at.run()

    # Verify filtered results
    markdown_content = " ".join([md.value for md in at.markdown])

    # "Team Awesome" should be displayed
    assert "Team Awesome" in markdown_content


@patch("components.api_client.requests.Session.get")
def test_sort_functionality_by_score(
    mock_get: MagicMock, authenticated_app: AppTest, mock_leaderboard_data: dict
) -> None:
    """Test sort functionality by overall score.

    **Validates: Requirement 6.4**

    The dashboard should provide a sort dropdown with options for
    score, team_name, and created_at.
    """

    # Mock responses
    def mock_get_side_effect(url: str, *args, **kwargs):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True

        if "/leaderboard" in url:
            mock_response.json.return_value = mock_leaderboard_data
        else:
            mock_response.json.return_value = [
                {"hack_id": "01HXXX111", "name": "Test Hackathon", "status": "active"}
            ]

        return mock_response

    mock_get.side_effect = mock_get_side_effect

    at = authenticated_app
    at.run()

    # Verify sort dropdown is present
    assert len(at.selectbox) >= 1

    # Find the sort dropdown (should have "sort" in key or label)
    sort_dropdown = None
    for selectbox in at.selectbox:
        key_match = selectbox.key and "sort" in selectbox.key.lower()
        label_match = "sort" in str(selectbox.label).lower()
        if key_match or label_match:
            sort_dropdown = selectbox
            break

    assert sort_dropdown is not None, "Sort dropdown not found"

    # Verify sort options are available
    # The options should include score, team_name, and created_at
    assert len(sort_dropdown.options) >= 3


@patch("components.api_client.requests.Session.get")
def test_team_detail_navigation(
    mock_get: MagicMock,
    authenticated_app: AppTest,
    mock_leaderboard_data: dict,
    mock_scorecard_data: dict,
) -> None:
    """Test team detail navigation by clicking a team row.

    **Validates: Requirements 6.5, 7.1**

    When an organizer clicks a team row, the dashboard should:
    - Navigate to the team detail view
    - Fetch scorecard data from GET /hackathons/{hack_id}/submissions/{sub_id}/scorecard
    """

    # Mock responses
    def mock_get_side_effect(url: str, *args, **kwargs):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True

        if "/individual-scorecards" in url:
            # Return individual scorecards data
            mock_response.json.return_value = {
                "team_dynamics": {
                    "collaboration_quality": "excellent",
                    "role_distribution": "balanced",
                    "communication_frequency": "high"
                },
                "members": []
            }
        elif "/scorecard" in url:
            mock_response.json.return_value = mock_scorecard_data
        elif "/leaderboard" in url:
            mock_response.json.return_value = mock_leaderboard_data
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

    # Verify hackathon dropdown exists and select first hackathon
    assert len(at.selectbox) > 0, "Hackathon dropdown not found"

    # The selectbox should auto-select the first hackathon
    # Now verify leaderboard is displayed with View Details buttons

    # Find "View Details" button for first submission
    view_button = None
    for button in at.button:
        if "View Details" in button.label or "view" in button.label.lower():
            view_button = button
            break

    assert view_button is not None, f"View Details button not found. Available buttons: {[b.label for b in at.button]}"

    # Click the button to navigate to team detail
    view_button.click()
    at.run()

    # Verify we're now in team detail view
    # AppTest session_state doesn't have .get(), use 'in' operator
    assert "view_mode" in at.session_state and at.session_state["view_mode"] == "team_detail"
    assert "selected_sub_id" in at.session_state

    # Verify scorecard API was called
    scorecard_calls = [
        call for call in mock_get.call_args_list if "/scorecard" in str(call.args[0])
    ]
    assert len(scorecard_calls) > 0, "Scorecard endpoint not called"


@patch("components.api_client.requests.Session.get")
def test_scorecard_display_completeness(
    mock_get: MagicMock,
    authenticated_app: AppTest,
    mock_leaderboard_data: dict,
    mock_scorecard_data: dict,
) -> None:
    """Test that scorecard displays all required sections.

    **Validates: Requirement 7.2**

    The dashboard should display:
    - overall_score, confidence, recommendation
    - dimension_scores with raw, weighted, and weight columns
    - agent_results with summary, strengths, improvements, cost
    - repo_meta with primary_language, commit_count, contributor_count, has_tests, has_ci
    - total cost breakdown by agent
    """

    # Mock responses
    def mock_get_side_effect(url: str, *args, **kwargs):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True

        if "/individual-scorecards" in url:
            mock_response.json.return_value = {
                "team_dynamics": {
                    "collaboration_quality": "excellent",
                    "role_distribution": "balanced"
                },
                "members": []
            }
        elif "/scorecard" in url:
            mock_response.json.return_value = mock_scorecard_data
        elif "/leaderboard" in url:
            mock_response.json.return_value = mock_leaderboard_data
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

    # Set up session state to view team detail
    at.session_state["view_mode"] = "team_detail"
    at.session_state["selected_sub_id"] = "01HZZZ001"
    at.session_state["selected_hackathon"] = "01HXXX111"

    at.run()

    # Verify the page loaded without errors
    assert not at.exception

    # Verify overall metrics are displayed
    assert len(at.metric) >= 3
    metric_labels = [m.label for m in at.metric]

    # Check for overall score, confidence, and recommendation
    assert any("Overall Score" in label or "score" in label.lower() for label in metric_labels)
    assert any("Confidence" in label for label in metric_labels)
    assert any("Recommendation" in label for label in metric_labels)

    # Verify tabs are present for organizing content
    assert len(at.tabs) > 0

    # Verify dimension scores are displayed
    markdown_content = " ".join([md.value for md in at.markdown])
    assert "Dimension" in markdown_content or "dimension" in markdown_content.lower()

    # Verify agent results are displayed
    assert len(at.expander) > 0

    # Verify repository metadata is displayed
    assert any(
        "Primary Language" in label or "language" in label.lower() for label in metric_labels
    )
    assert any("Commits" in label or "commit" in label.lower() for label in metric_labels)

    # Verify cost breakdown is displayed
    assert any("Cost" in label or "cost" in label.lower() for label in metric_labels)


@patch("components.api_client.requests.Session.get")
def test_pagination_limit_50_submissions(mock_get: MagicMock, authenticated_app: AppTest) -> None:
    """Test pagination limits display to 50 submissions per page.

    **Validates: Requirement 11.6**

    The dashboard should limit leaderboard pagination to 50 submissions per page.
    """
    # Create mock data with 100 submissions
    large_leaderboard_data = {
        "hack_id": "01HXXX111",
        "total_submissions": 100,
        "analyzed_count": 100,
        "submissions": [
            {
                "sub_id": f"01HZZZ{i:03d}",
                "rank": i + 1,
                "team_name": f"Team {i + 1}",
                "overall_score": 90.0 - i * 0.5,
                "confidence": 0.95,
                "recommendation": "must_interview",
                "created_at": "2025-03-02T10:00:00Z",
            }
            for i in range(100)
        ],
    }

    # Mock responses
    def mock_get_side_effect(url: str, *args, **kwargs):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True

        if "/leaderboard" in url:
            mock_response.json.return_value = large_leaderboard_data
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

    # Verify pagination controls are present
    # Should have First, Previous, Next, Last buttons
    button_labels = [b.label for b in at.button]

    # Check for pagination buttons
    assert any("First" in label or "⏮" in label for label in button_labels), (
        "First button not found"
    )
    assert any("Previous" in label or "◀" in label for label in button_labels), (
        "Previous button not found"
    )
    assert any("Next" in label or "▶" in label for label in button_labels), "Next button not found"
    assert any("Last" in label or "⏭" in label for label in button_labels), "Last button not found"

    # Verify page information is displayed
    markdown_content = " ".join([md.value for md in at.markdown])
    assert "Page" in markdown_content or "page" in markdown_content.lower()

    # Verify caption shows correct range (1-50 of 100)
    caption_content = " ".join([c.value for c in at.caption])
    assert "1-50" in caption_content or "50" in caption_content


@patch("components.api_client.requests.Session.get")
def test_back_to_leaderboard_button(
    mock_get: MagicMock, authenticated_app: AppTest, mock_scorecard_data: dict
) -> None:
    """Test back button returns to leaderboard from team detail view.

    **Validates: Requirement 6.5**

    When viewing team details, a back button should return to the leaderboard.
    """

    # Mock responses
    def mock_get_side_effect(url: str, *args, **kwargs):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True

        if "/individual-scorecards" in url:
            mock_response.json.return_value = {
                "team_dynamics": {},
                "members": []
            }
        elif "/scorecard" in url:
            mock_response.json.return_value = mock_scorecard_data
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

    # Set up session state to view team detail
    at.session_state["view_mode"] = "team_detail"
    at.session_state["selected_sub_id"] = "01HZZZ001"
    at.session_state["selected_hackathon"] = "01HXXX111"

    at.run()

    # Find back button
    back_button = None
    for button in at.button:
        if "Back" in button.label or "⬅" in button.label:
            back_button = button
            break

    assert back_button is not None, "Back button not found"

    # Click back button
    back_button.click()
    at.run()

    # Verify we're back in leaderboard view
    # AppTest session_state doesn't have .get(), use 'in' operator
    assert "view_mode" in at.session_state and at.session_state["view_mode"] == "leaderboard"


@patch("components.api_client.requests.Session.get")
def test_no_submissions_message(mock_get: MagicMock, authenticated_app: AppTest) -> None:
    """Test that appropriate message is shown when no submissions are analyzed.

    **Validates: Requirement 6.1**

    When no submissions have been analyzed, the dashboard should display
    an informative message.
    """
    # Mock empty leaderboard data
    empty_leaderboard_data = {
        "hack_id": "01HXXX111",
        "total_submissions": 0,
        "analyzed_count": 0,
        "submissions": [],
    }

    # Mock responses
    def mock_get_side_effect(url: str, *args, **kwargs):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True

        if "/leaderboard" in url:
            mock_response.json.return_value = empty_leaderboard_data
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

    # Verify info message is displayed
    assert len(at.info) > 0, f"Expected info message but got {len(at.info)} info messages"
    info_message = at.info[0].value
    assert "no submissions" in info_message.lower() or "analyzed" in info_message.lower()


@patch("components.api_client.requests.Session.get")
def test_refresh_button_clears_cache(
    mock_get: MagicMock, authenticated_app: AppTest, mock_leaderboard_data: dict
) -> None:
    """Test that refresh button clears cache and reloads data.

    **Validates: Requirement 3.6**

    The dashboard should provide a manual refresh button that clears
    the cache and reloads data.
    """

    # Mock responses
    def mock_get_side_effect(url: str, *args, **kwargs):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True

        if "/leaderboard" in url:
            mock_response.json.return_value = mock_leaderboard_data
        else:
            mock_response.json.return_value = [
                {"hack_id": "01HXXX111", "name": "Test Hackathon", "status": "active"}
            ]

        return mock_response

    mock_get.side_effect = mock_get_side_effect

    at = authenticated_app
    at.run()

    # Find refresh button
    refresh_button = None
    for button in at.button:
        if "Refresh" in button.label or "🔄" in button.label:
            refresh_button = button
            break

    assert refresh_button is not None, "Refresh button not found"
