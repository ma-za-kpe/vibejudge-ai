"""Tests for Live Dashboard analyze button workflow."""

from unittest.mock import MagicMock, patch

import pytest
from streamlit.testing.v1 import AppTest


@pytest.fixture
def mock_api_responses():
    """Mock API responses for dashboard."""
    return {
        "hackathons": {
            "hackathons": [
                {
                    "hack_id": "01KJFQW23JKE473T0ZPSGSQ2J6",
                    "name": "Test Hackathon",
                    "status": "configured",
                }
            ],
            "total": 1,
        },
        "stats": {
            "submission_count": 3,
            "verified_count": 1,
            "pending_count": 2,
            "participant_count": 3,
        },
        "submissions": {
            "submissions": [
                {
                    "sub_id": "SUB001",
                    "team_name": "Team Alpha",
                    "repo_url": "https://github.com/test/alpha",
                    "status": "pending",
                    "overall_score": None,
                },
                {
                    "sub_id": "SUB002",
                    "team_name": "Team Beta",
                    "repo_url": "https://github.com/test/beta",
                    "status": "verified",
                    "overall_score": 85.5,
                },
                {
                    "sub_id": "SUB003",
                    "team_name": "Team Gamma",
                    "repo_url": "https://github.com/test/gamma",
                    "status": "pending",
                    "overall_score": None,
                },
            ],
            "total": 3,
        },
        "analyze_status": {"status": "not_started"},
        "analyze_response": {
            "job_id": "01KJKTEST123456789",
            "hack_id": "01KJFQW23JKE473T0ZPSGSQ2J6",
            "status": "queued",
            "total_submissions": 1,
            "estimated_cost_usd": 0.06,
        },
    }


def test_analyze_button_appears_for_pending_submissions(mock_api_responses):
    """Test that analyze button (▶️) appears only for pending submissions."""
    with patch("requests.get") as mock_get, patch("requests.post") as mock_post:
        # Mock API responses
        mock_get.side_effect = lambda url, **kwargs: MagicMock(
            status_code=200,
            ok=True,
            json=lambda: (
                mock_api_responses["hackathons"]
                if "/hackathons" in url and "/stats" not in url and "/submissions" not in url
                else mock_api_responses["stats"]
                if "/stats" in url
                else mock_api_responses["submissions"]
                if "/submissions" in url
                else mock_api_responses["analyze_status"]
            ),
        )

        at = AppTest.from_file("streamlit_ui/pages/2_📊_Live_Dashboard.py")
        at.session_state["authenticated"] = True
        at.session_state["api_key"] = "vj_live_test123"
        at.session_state["api_base_url"] = "https://api.test.com/api/v1"
        at.run()

        # Find all button elements in the page
        buttons = [btn for btn in at.button if btn.label == "▶️"]

        # Should have analyze buttons for 2 pending submissions (SUB001 and SUB003)
        assert len(buttons) == 2, "Should have 2 analyze buttons for pending submissions"

        # Verify buttons have correct keys
        button_keys = [btn.key for btn in buttons]
        assert "analyze_SUB001" in button_keys
        assert "analyze_SUB003" in button_keys


def test_analyze_button_click_shows_confirmation(mock_api_responses):
    """Test that clicking analyze button shows confirmation dialog."""
    with patch("requests.get") as mock_get, patch("requests.post") as mock_post:
        mock_get.side_effect = lambda url, **kwargs: MagicMock(
            status_code=200,
            ok=True,
            json=lambda: (
                mock_api_responses["hackathons"]
                if "/hackathons" in url and "/stats" not in url and "/submissions" not in url
                else mock_api_responses["stats"]
                if "/stats" in url
                else mock_api_responses["submissions"]
                if "/submissions" in url
                else mock_api_responses["analyze_status"]
            ),
        )

        at = AppTest.from_file("streamlit_ui/pages/2_📊_Live_Dashboard.py")
        at.session_state["authenticated"] = True
        at.session_state["api_key"] = "vj_live_test123"
        at.session_state["api_base_url"] = "https://api.test.com/api/v1"
        at.run()

        # Click the analyze button for SUB001
        analyze_button = next(btn for btn in at.button if btn.key == "analyze_SUB001")
        analyze_button.click().run()

        # Verify session state contains confirmation data
        assert "analysis_confirmation" in at.session_state
        assert at.session_state["analysis_confirmation"]["type"] == "single"
        assert at.session_state["analysis_confirmation"]["sub_id"] == "SUB001"
        assert at.session_state["analysis_confirmation"]["team_name"] == "Team Alpha"


def test_confirmation_dialog_displays_submission_details(mock_api_responses):
    """Test that confirmation dialog shows correct submission details."""
    with patch("requests.get") as mock_get, patch("requests.post") as mock_post:
        mock_get.side_effect = lambda url, **kwargs: MagicMock(
            status_code=200,
            ok=True,
            json=lambda: (
                mock_api_responses["hackathons"]
                if "/hackathons" in url and "/stats" not in url and "/submissions" not in url
                else mock_api_responses["stats"]
                if "/stats" in url
                else mock_api_responses["submissions"]
                if "/submissions" in url
                else mock_api_responses["analyze_status"]
            ),
        )

        at = AppTest.from_file("streamlit_ui/pages/2_📊_Live_Dashboard.py")
        at.session_state["authenticated"] = True
        at.session_state["api_key"] = "vj_live_test123"
        at.session_state["api_base_url"] = "https://api.test.com/api/v1"

        # Simulate analyze button click by setting session state
        at.session_state["analysis_confirmation"] = {
            "type": "single",
            "sub_id": "SUB001",
            "team_name": "Team Alpha",
        }
        at.run()

        # Check that confirmation info is displayed
        info_messages = [info.value for info in at.info]
        caption_messages = [cap.value for cap in at.caption]
        assert any("Team Alpha" in msg for msg in info_messages), "Should show team name"
        assert any("SUB001" in msg for msg in caption_messages), (
            "Should show submission ID in caption"
        )


def test_confirm_analyze_triggers_api_call(mock_api_responses):
    """Test that clicking 'Confirm & Analyze' triggers the analyze API call."""
    with patch("requests.get") as mock_get, patch("requests.post") as mock_post:
        mock_get.side_effect = lambda url, **kwargs: MagicMock(
            status_code=200,
            ok=True,
            json=lambda: (
                mock_api_responses["hackathons"]
                if "/hackathons" in url and "/stats" not in url and "/submissions" not in url
                else mock_api_responses["stats"]
                if "/stats" in url
                else mock_api_responses["submissions"]
                if "/submissions" in url
                else mock_api_responses["analyze_status"]
            ),
        )

        mock_post.return_value = MagicMock(
            status_code=202,
            ok=True,
            json=lambda: mock_api_responses["analyze_response"],
        )

        at = AppTest.from_file("streamlit_ui/pages/2_📊_Live_Dashboard.py")
        at.session_state["authenticated"] = True
        at.session_state["api_key"] = "vj_live_test123"
        at.session_state["api_base_url"] = "https://api.test.com/api/v1"

        # Set confirmation state
        at.session_state["analysis_confirmation"] = {
            "type": "single",
            "sub_id": "SUB001",
            "team_name": "Team Alpha",
        }
        at.run()

        # Click confirm button
        confirm_button = next(btn for btn in at.button if "Confirm & Analyze" in btn.label)
        confirm_button.click().run()

        # Verify POST request was made with correct submission_ids
        assert mock_post.called, "Should make POST request to analyze endpoint"
        call_args = mock_post.call_args

        # Check the request included submission_ids
        assert "json" in call_args.kwargs, "Should include JSON data"
        assert call_args.kwargs["json"]["submission_ids"] == ["SUB001"], (
            "Should include the specific submission ID"
        )


def test_cancel_button_clears_confirmation_state(mock_api_responses):
    """Test that clicking cancel clears the confirmation state."""
    with patch("requests.get") as mock_get:
        mock_get.side_effect = lambda url, **kwargs: MagicMock(
            status_code=200,
            ok=True,
            json=lambda: (
                mock_api_responses["hackathons"]
                if "/hackathons" in url and "/stats" not in url and "/submissions" not in url
                else mock_api_responses["stats"]
                if "/stats" in url
                else mock_api_responses["submissions"]
                if "/submissions" in url
                else mock_api_responses["analyze_status"]
            ),
        )

        at = AppTest.from_file("streamlit_ui/pages/2_📊_Live_Dashboard.py")
        at.session_state["authenticated"] = True
        at.session_state["api_key"] = "vj_live_test123"
        at.session_state["api_base_url"] = "https://api.test.com/api/v1"

        # Set confirmation state
        at.session_state["analysis_confirmation"] = {
            "type": "single",
            "sub_id": "SUB001",
            "team_name": "Team Alpha",
        }
        at.run()

        # Click cancel button
        cancel_button = next(btn for btn in at.button if btn.label == "❌ Cancel")
        cancel_button.click().run()

        # Verify confirmation state is cleared
        assert (
            "analysis_confirmation" not in at.session_state
            or at.session_state["analysis_confirmation"] is None
        )


def test_analyze_button_shows_loading_state(mock_api_responses):
    """Test that analyze button shows ⏳ when in confirmation state."""
    with patch("requests.get") as mock_get:
        mock_get.side_effect = lambda url, **kwargs: MagicMock(
            status_code=200,
            ok=True,
            json=lambda: (
                mock_api_responses["hackathons"]
                if "/hackathons" in url and "/stats" not in url and "/submissions" not in url
                else mock_api_responses["stats"]
                if "/stats" in url
                else mock_api_responses["submissions"]
                if "/submissions" in url
                else mock_api_responses["analyze_status"]
            ),
        )

        at = AppTest.from_file("streamlit_ui/pages/2_📊_Live_Dashboard.py")
        at.session_state["authenticated"] = True
        at.session_state["api_key"] = "vj_live_test123"
        at.session_state["api_base_url"] = "https://api.test.com/api/v1"

        # Set confirmation state for SUB001
        at.session_state["analysis_confirmation"] = {
            "type": "single",
            "sub_id": "SUB001",
            "team_name": "Team Alpha",
        }
        at.run()

        # Check that SUB001 shows ⏳ instead of ▶️
        analyze_buttons = [btn for btn in at.button if btn.label == "▶️"]
        button_keys = [btn.key for btn in analyze_buttons]

        # SUB001 should NOT have analyze button (replaced with ⏳)
        assert "analyze_SUB001" not in button_keys, "SUB001 should show ⏳, not ▶️"

        # SUB003 should still have analyze button
        assert "analyze_SUB003" in button_keys, "SUB003 should still show ▶️ button"


def test_successful_analysis_clears_confirmation_state(mock_api_responses):
    """Test that successful analysis clears confirmation state and triggers API call."""
    with patch("requests.get") as mock_get, patch("requests.post") as mock_post:
        mock_get.side_effect = lambda url, **kwargs: MagicMock(
            status_code=200,
            ok=True,
            json=lambda: (
                mock_api_responses["hackathons"]
                if "/hackathons" in url and "/stats" not in url and "/submissions" not in url
                else mock_api_responses["stats"]
                if "/stats" in url
                else mock_api_responses["submissions"]
                if "/submissions" in url
                else mock_api_responses["analyze_status"]
            ),
        )

        mock_post.return_value = MagicMock(
            status_code=202,
            ok=True,
            json=lambda: mock_api_responses["analyze_response"],
        )

        at = AppTest.from_file("streamlit_ui/pages/2_📊_Live_Dashboard.py")
        at.session_state["authenticated"] = True
        at.session_state["api_key"] = "vj_live_test123"
        at.session_state["api_base_url"] = "https://api.test.com/api/v1"

        # Set confirmation state
        at.session_state["analysis_confirmation"] = {
            "type": "single",
            "sub_id": "SUB001",
            "team_name": "Team Alpha",
        }
        at.run()

        # Click confirm button
        confirm_button = next(btn for btn in at.button if "Confirm & Analyze" in btn.label)
        confirm_button.click().run()

        # Verify POST was called with correct payload
        assert mock_post.called, "Should trigger analysis API call"
        call_args = mock_post.call_args
        assert call_args.kwargs["json"]["submission_ids"] == ["SUB001"]
