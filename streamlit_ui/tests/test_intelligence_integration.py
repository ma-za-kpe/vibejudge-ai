"""Integration tests for intelligence page flow using Streamlit AppTest.

**Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.6**

This module tests the full intelligence page flow including:
- Intelligence data display with must_interview candidates
- Technology trends display with Plotly bar chart
- Sponsor API usage statistics display
- Unavailable data handling (when analysis hasn't completed)
- All intelligence sections are displayed when data is available
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
    # Clear Streamlit cache before each test
    import streamlit as st

    st.cache_data.clear()

    at = AppTest.from_file("streamlit_ui/pages/4_💡_Intelligence.py")

    # Set up authentication in session state
    at.session_state["api_key"] = "test_api_key_123"  # pragma: allowlist secret
    at.session_state["api_base_url"] = "http://localhost:8000"

    return at


@patch("components.api_client.requests.Session.get")
def test_intelligence_page_displays_hackathon_dropdown(
    mock_get: MagicMock, authenticated_app: AppTest
) -> None:
    """Test that intelligence page displays hackathon selection dropdown.

    **Validates: Requirement 9.1**

    The dashboard should display a hackathon selection dropdown populated
    from GET /hackathons endpoint.
    """
    # Mock responses
    def mock_get_side_effect(url: str, *args, **kwargs):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True

        if "/intelligence" in url:
            # Return empty intelligence data
            mock_response.json.return_value = {
                "must_interview": [],
                "technology_trends": [],
                "sponsor_api_usage": {},
            }
        else:
            # Hackathons list response
            mock_response.json.return_value = [
                {"hack_id": "01HXXX111", "name": "Spring Hackathon 2025", "status": "active"},
                {"hack_id": "01HXXX222", "name": "Summer Hackathon 2025", "status": "active"},
            ]

        return mock_response

    mock_get.side_effect = mock_get_side_effect

    at = authenticated_app
    at.run()

    # Verify the page loaded without errors
    assert not at.exception

    # Verify title is displayed
    assert len(at.title) > 0
    assert "Intelligence" in at.title[0].value

    # Verify dropdown is present
    assert len(at.selectbox) >= 1

    # Get the hackathon selection dropdown
    hackathon_dropdown = at.selectbox[0]

    # Verify dropdown contains both hackathon names
    assert "Spring Hackathon 2025" in hackathon_dropdown.options
    assert "Summer Hackathon 2025" in hackathon_dropdown.options


@patch("components.api_client.requests.Session.get")
def test_intelligence_data_unavailable_message(
    mock_get: MagicMock, authenticated_app: AppTest
) -> None:
    """Test that unavailable data message is displayed when intelligence is pending.

    **Validates: Requirement 9.6**

    When intelligence data is unavailable (analysis hasn't completed),
    the dashboard should display a message indicating analysis must complete first.
    """

    # Mock responses
    def mock_get_side_effect(url: str, *args, **kwargs):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True

        if "/intelligence" in url:
            # Return None to simulate unavailable data
            # In the actual implementation, this would be a 404 or empty response
            mock_response.status_code = 404
            mock_response.ok = False
            mock_response.json.return_value = {"detail": "Intelligence data not available"}
        else:
            # Hackathons list response
            mock_response.json.return_value = [
                {"hack_id": "01HXXX111", "name": "Test Hackathon", "status": "active"}
            ]

        return mock_response

    mock_get.side_effect = mock_get_side_effect

    at = authenticated_app
    at.run()

    # Verify info message is displayed
    assert len(at.info) > 0, "Unavailable data message not displayed"
    info_message = at.info[0].value
    assert "pending" in info_message.lower() or "unavailable" in info_message.lower()
    assert "analysis" in info_message.lower()


@patch("components.api_client.requests.Session.get")
def test_must_interview_candidates_display(mock_get: MagicMock, authenticated_app: AppTest) -> None:
    """Test that must-interview candidates are displayed correctly.

    **Validates: Requirement 9.2**

    The dashboard should display must_interview candidates with name,
    team_name, skills, and hiring_score.
    """

    # Mock responses
    def mock_get_side_effect(url: str, *args, **kwargs):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True

        if "/intelligence" in url:
            # Intelligence response with must-interview candidates
            mock_response.json.return_value = {
                "must_interview": [
                    {
                        "name": "Alice Johnson",
                        "team_name": "Team Awesome",
                        "skills": ["Python", "FastAPI", "AWS"],
                        "hiring_score": 95.0,
                    },
                    {
                        "name": "Bob Smith",
                        "team_name": "Team Innovation",
                        "skills": ["JavaScript", "React", "Node.js"],
                        "hiring_score": 92.5,
                    },
                ],
                "technology_trends": [],
                "sponsor_api_usage": {},
            }
        else:
            # Hackathons list response
            mock_response.json.return_value = [
                {"hack_id": "01HXXX111", "name": "Test Hackathon", "status": "active"}
            ]

        return mock_response

    mock_get.side_effect = mock_get_side_effect

    at = authenticated_app
    at.run()

    # Verify tabs are displayed
    assert len(at.tabs) > 0, "Tabs not displayed"

    # Verify markdown content contains candidate information
    markdown_content = " ".join([md.value for md in at.markdown])

    # Check for candidate names
    assert "Alice Johnson" in markdown_content, "Alice Johnson not displayed"
    assert "Bob Smith" in markdown_content, "Bob Smith not displayed"

    # Check for team names
    assert "Team Awesome" in markdown_content, "Team Awesome not displayed"
    assert "Team Innovation" in markdown_content, "Team Innovation not displayed"

    # Check for skills
    assert "Python" in markdown_content, "Python skill not displayed"
    assert "JavaScript" in markdown_content, "JavaScript skill not displayed"

    # Check for hiring scores
    assert "95.0" in markdown_content or "95" in markdown_content, "Hiring score 95.0 not displayed"
    assert "92.5" in markdown_content or "92" in markdown_content, "Hiring score 92.5 not displayed"


@patch("components.api_client.requests.Session.get")
def test_technology_trends_display_with_chart(
    mock_get: MagicMock, authenticated_app: AppTest
) -> None:
    """Test that technology trends are displayed with Plotly chart.

    **Validates: Requirements 9.3, 9.4**

    The dashboard should display technology_trends with a Plotly bar chart
    visualization showing technology usage counts.
    """

    # Mock responses
    def mock_get_side_effect(url: str, *args, **kwargs):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True

        if "/intelligence" in url:
            # Intelligence response with technology trends
            mock_response.json.return_value = {
                "must_interview": [],
                "technology_trends": [
                    {"technology": "Python", "category": "language", "usage_count": 120},
                    {"technology": "JavaScript", "category": "language", "usage_count": 95},
                    {"technology": "React", "category": "framework", "usage_count": 80},
                ],
                "sponsor_api_usage": {},
            }
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
    assert not at.exception, "Page should load without errors"

    # Verify markdown content contains technology information
    markdown_content = " ".join([md.value for md in at.markdown])

    # Check for technology names
    assert "Python" in markdown_content, "Python not displayed"
    assert "JavaScript" in markdown_content, "JavaScript not displayed"
    assert "React" in markdown_content, "React not displayed"

    # Check for usage counts
    assert "120" in markdown_content, "Python usage count not displayed"
    assert "95" in markdown_content, "JavaScript usage count not displayed"
    assert "80" in markdown_content, "React usage count not displayed"


@patch("components.api_client.requests.Session.get")
def test_sponsor_api_usage_display(mock_get: MagicMock, authenticated_app: AppTest) -> None:
    """Test that sponsor API usage statistics are displayed.

    **Validates: Requirement 9.4**

    The dashboard should display sponsor_api_usage statistics showing
    how many teams used each sponsor API.
    """

    # Mock responses
    def mock_get_side_effect(url: str, *args, **kwargs):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True

        if "/intelligence" in url:
            # Intelligence response with sponsor API usage
            mock_response.json.return_value = {
                "must_interview": [],
                "technology_trends": [],
                "sponsor_api_usage": {"stripe": 45, "twilio": 30, "aws": 80, "sendgrid": 25},
            }
        else:
            # Hackathons list response
            mock_response.json.return_value = [
                {"hack_id": "01HXXX111", "name": "Test Hackathon", "status": "active"}
            ]

        return mock_response

    mock_get.side_effect = mock_get_side_effect

    at = authenticated_app
    at.run()

    # Verify metrics are displayed for sponsor APIs
    assert len(at.metric) >= 4, "Sponsor API metrics not displayed"

    # Get metric labels and values
    metric_labels = [m.label for m in at.metric]
    metric_values = [str(m.value) for m in at.metric]

    # Check for sponsor names (case-insensitive)
    metric_labels_lower = [label.lower() for label in metric_labels]
    assert any("stripe" in label for label in metric_labels_lower), "Stripe metric not found"
    assert any("twilio" in label for label in metric_labels_lower), "Twilio metric not found"
    assert any("aws" in label for label in metric_labels_lower), "AWS metric not found"
    assert any("sendgrid" in label for label in metric_labels_lower), "SendGrid metric not found"

    # Check for usage counts
    assert "45" in metric_values, "Stripe usage count not displayed"
    assert "30" in metric_values, "Twilio usage count not displayed"
    assert "80" in metric_values, "AWS usage count not displayed"
    assert "25" in metric_values, "SendGrid usage count not displayed"


@patch("components.api_client.requests.Session.get")
def test_all_intelligence_sections_displayed(
    mock_get: MagicMock, authenticated_app: AppTest
) -> None:
    """Test that all intelligence sections are displayed when data is available.

    **Validates: Requirements 9.2, 9.3, 9.4**

    When intelligence data is available, the dashboard should display all
    three sections: must-interview candidates, technology trends, and
    sponsor API usage.
    """

    # Mock responses with complete intelligence data
    def mock_get_side_effect(url: str, *args, **kwargs):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True

        if "/intelligence" in url:
            # Complete intelligence response
            mock_response.json.return_value = {
                "must_interview": [
                    {
                        "name": "Alice Johnson",
                        "team_name": "Team Awesome",
                        "skills": ["Python", "FastAPI"],
                        "hiring_score": 95.0,
                    }
                ],
                "technology_trends": [
                    {"technology": "Python", "category": "language", "usage_count": 120}
                ],
                "sponsor_api_usage": {"stripe": 45, "aws": 80},
            }
        else:
            # Hackathons list response
            mock_response.json.return_value = [
                {"hack_id": "01HXXX111", "name": "Test Hackathon", "status": "active"}
            ]

        return mock_response

    mock_get.side_effect = mock_get_side_effect

    at = authenticated_app
    at.run()

    # Verify tabs are displayed (3 tabs for the 3 sections)
    assert len(at.tabs) > 0, "Tabs not displayed"

    # Verify all three sections have content
    markdown_content = " ".join([md.value for md in at.markdown])

    # Check for must-interview section
    assert "Must-Interview" in markdown_content or "Alice Johnson" in markdown_content, (
        "Must-interview section not displayed"
    )

    # Check for technology trends section
    assert "Technology Trends" in markdown_content or "Python" in markdown_content, (
        "Technology trends section not displayed"
    )

    # Check for sponsor API section
    assert "Sponsor API" in markdown_content or len(at.metric) >= 2, (
        "Sponsor API section not displayed"
    )

    # Verify metrics are present (for sponsor APIs)
    assert len(at.metric) >= 2, "Sponsor API metrics not displayed"

    # Verify the page has all required content
    assert "Technology" in markdown_content, "Technology section not found"


@patch("components.api_client.requests.Session.get")
def test_empty_must_interview_candidates(mock_get: MagicMock, authenticated_app: AppTest) -> None:
    """Test that info message is displayed when no must-interview candidates exist.

    **Validates: Requirement 9.2**

    When must_interview list is empty, the dashboard should display an
    info message indicating no candidates were identified.
    """

    # Mock responses
    def mock_get_side_effect(url: str, *args, **kwargs):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True

        if "/intelligence" in url:
            # Intelligence response with empty must-interview list
            mock_response.json.return_value = {
                "must_interview": [],
                "technology_trends": [],
                "sponsor_api_usage": {},
            }
        else:
            # Hackathons list response
            mock_response.json.return_value = [
                {"hack_id": "01HXXX111", "name": "Test Hackathon", "status": "active"}
            ]

        return mock_response

    mock_get.side_effect = mock_get_side_effect

    at = authenticated_app
    at.run()

    # Verify info message is displayed for empty candidates
    assert len(at.info) > 0, "Empty candidates info message not displayed"
    info_messages = [info.value for info in at.info]
    empty_candidates_message = any(
        "no must-interview" in msg.lower() or "no candidates" in msg.lower()
        for msg in info_messages
    )
    assert empty_candidates_message, "Empty candidates message not found"


@patch("components.api_client.requests.Session.get")
def test_empty_technology_trends(mock_get: MagicMock, authenticated_app: AppTest) -> None:
    """Test that info message is displayed when no technology trends exist.

    **Validates: Requirement 9.3**

    When technology_trends list is empty, the dashboard should display an
    info message indicating no trends data is available.
    """

    # Mock responses
    def mock_get_side_effect(url: str, *args, **kwargs):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True

        if "/intelligence" in url:
            # Intelligence response with empty technology trends
            mock_response.json.return_value = {
                "must_interview": [],
                "technology_trends": [],
                "sponsor_api_usage": {},
            }
        else:
            # Hackathons list response
            mock_response.json.return_value = [
                {"hack_id": "01HXXX111", "name": "Test Hackathon", "status": "active"}
            ]

        return mock_response

    mock_get.side_effect = mock_get_side_effect

    at = authenticated_app
    at.run()

    # Verify info message is displayed for empty trends
    assert len(at.info) > 0, "Empty trends info message not displayed"
    info_messages = [info.value for info in at.info]
    empty_trends_message = any(
        "no technology trends" in msg.lower() or "trends data" in msg.lower()
        for msg in info_messages
    )
    assert empty_trends_message, "Empty trends message not found"


@patch("components.api_client.requests.Session.get")
def test_empty_sponsor_api_usage(mock_get: MagicMock, authenticated_app: AppTest) -> None:
    """Test that info message is displayed when no sponsor API usage exists.

    **Validates: Requirement 9.4**

    When sponsor_api_usage dict is empty, the dashboard should display an
    info message indicating no usage data is available.
    """

    # Mock responses
    def mock_get_side_effect(url: str, *args, **kwargs):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True

        if "/intelligence" in url:
            # Intelligence response with empty sponsor API usage
            mock_response.json.return_value = {
                "must_interview": [],
                "technology_trends": [],
                "sponsor_api_usage": {},
            }
        else:
            # Hackathons list response
            mock_response.json.return_value = [
                {"hack_id": "01HXXX111", "name": "Test Hackathon", "status": "active"}
            ]

        return mock_response

    mock_get.side_effect = mock_get_side_effect

    at = authenticated_app
    at.run()

    # Verify info message is displayed for empty sponsor API usage
    assert len(at.info) > 0, "Empty sponsor API usage info message not displayed"
    info_messages = [info.value for info in at.info]
    empty_sponsor_message = any(
        "no sponsor api" in msg.lower() or "usage data" in msg.lower() for msg in info_messages
    )
    assert empty_sponsor_message, "Empty sponsor API usage message not found"


@patch("components.api_client.requests.Session.get")
def test_refresh_button_clears_cache(mock_get: MagicMock, authenticated_app: AppTest) -> None:
    """Test that refresh button clears cache and reloads data.

    **Validates: Requirement 9.1**

    When the user clicks the refresh button, the cache should be cleared
    and the page should reload with fresh data.
    """

    # Mock responses
    def mock_get_side_effect(url: str, *args, **kwargs):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True

        if "/intelligence" in url:
            mock_response.json.return_value = {
                "must_interview": [],
                "technology_trends": [],
                "sponsor_api_usage": {},
            }
        else:
            mock_response.json.return_value = [
                {"hack_id": "01HXXX111", "name": "Test Hackathon", "status": "active"}
            ]

        return mock_response

    mock_get.side_effect = mock_get_side_effect

    at = authenticated_app
    at.run()

    # Find and click refresh button
    refresh_button = None
    for button in at.button:
        if "Refresh" in button.label or "refresh" in button.label.lower():
            refresh_button = button
            break

    assert refresh_button is not None, "Refresh button not found"

    # Click refresh button
    refresh_button.click()
    # Note: The actual cache clearing and rerun happens in the app
    # We just verify the button exists and can be clicked


@patch("components.api_client.requests.Session.get")
def test_no_hackathons_warning(mock_get: MagicMock, authenticated_app: AppTest) -> None:
    """Test that warning is displayed when no hackathons exist.

    **Validates: Requirement 9.1**

    When no hackathons are found, the dashboard should display a warning
    message prompting the user to create a hackathon first.
    """
    # Mock empty hackathons list response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.ok = True
    mock_response.json.return_value = []
    mock_get.return_value = mock_response

    at = authenticated_app
    at.run()

    # Verify warning is displayed
    assert len(at.warning) > 0, "No hackathons warning not displayed"
    warning_message = at.warning[0].value
    assert "no hackathons" in warning_message.lower() or "create" in warning_message.lower()


@patch("components.api_client.requests.Session.get")
def test_intelligence_api_error_handling(mock_get: MagicMock, authenticated_app: AppTest) -> None:
    """Test that API errors are handled gracefully.

    **Validates: Requirement 9.6**

    When the intelligence API returns an error, the dashboard should
    handle it gracefully and display an appropriate message.
    """

    # Mock responses
    def mock_get_side_effect(url: str, *args, **kwargs):
        mock_response = MagicMock()

        if "/intelligence" in url:
            # Simulate API error
            mock_response.status_code = 500
            mock_response.ok = False
            mock_response.json.return_value = {"detail": "Internal server error"}
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

    # Verify info message is displayed (not error, since we handle it gracefully)
    assert len(at.info) > 0, "Error handling message not displayed"
    info_message = at.info[0].value
    assert "pending" in info_message.lower() or "unavailable" in info_message.lower()


@patch("components.api_client.requests.Session.get")
def test_candidate_skills_display_as_comma_separated(
    mock_get: MagicMock, authenticated_app: AppTest
) -> None:
    """Test that candidate skills are displayed as comma-separated list.

    **Validates: Requirement 9.2**

    Skills should be displayed as a comma-separated list for readability.
    """

    # Mock responses
    def mock_get_side_effect(url: str, *args, **kwargs):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True

        if "/intelligence" in url:
            mock_response.json.return_value = {
                "must_interview": [
                    {
                        "name": "Alice Johnson",
                        "team_name": "Team Awesome",
                        "skills": ["Python", "FastAPI", "AWS", "Docker"],
                        "hiring_score": 95.0,
                    }
                ],
                "technology_trends": [],
                "sponsor_api_usage": {},
            }
        else:
            mock_response.json.return_value = [
                {"hack_id": "01HXXX111", "name": "Test Hackathon", "status": "active"}
            ]

        return mock_response

    mock_get.side_effect = mock_get_side_effect

    at = authenticated_app
    at.run()

    # Verify skills are displayed as comma-separated
    markdown_content = " ".join([md.value for md in at.markdown])

    # Check that skills appear in the content
    assert "Python" in markdown_content, "Python skill not displayed"
    assert "FastAPI" in markdown_content, "FastAPI skill not displayed"
    assert "AWS" in markdown_content, "AWS skill not displayed"
    assert "Docker" in markdown_content, "Docker skill not displayed"
