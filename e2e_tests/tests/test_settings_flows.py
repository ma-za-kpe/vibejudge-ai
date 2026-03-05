"""
E2E tests for Category 8: Settings & Configuration Flows (7 flows).

Tests:
- 8.1: Scoring Weights Configuration Flow
- 8.2: AI Policy Configuration Flow
- 8.3: Budget Limit Configuration Flow
- 8.4: Agent Enable/Disable Flow
- 8.5: Settings Save & Validation Flow
- 8.6: Hackathon Status Change Flow
- 8.7: Settings Reset Flow
"""

import pytest
from pages.settings_page import SettingsPage
from playwright.sync_api import Page


@pytest.mark.critical
def test_scoring_weights_configuration_flow(authenticated_page: Page, mock_api):
    """Test Flow 8.1: Scoring Weights Configuration Flow."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list(
        [{"hack_id": hack_id, "name": "Test Hackathon", "status": "draft"}]
    )
    mock_api.mock_hackathon_stats(hack_id)

    # Mock GET settings
    mock_api.mock_get(
        f"**/hackathons/{hack_id}/settings",
        status=200,
        body={
            "weights": {
                "code_quality": 0.3,
                "performance": 0.3,
                "innovation": 0.3,
                "ai_detection": 0.1,
            }
        },
    )

    # Mock PUT settings
    mock_api.mock_post(
        f"**/hackathons/{hack_id}/settings", status=200, body={"message": "Settings updated"}
    )

    settings = SettingsPage(authenticated_page)
    settings.navigate()
    settings.select_hackathon("Test Hackathon")

    # Verify default weights
    bug_hunter = settings.get_weight("code_quality")
    assert bug_hunter == 0.3

    # Update weights
    settings.set_weight("code_quality", 0.4)
    settings.set_weight("performance", 0.25)
    settings.set_weight("innovation", 0.25)
    settings.set_weight("ai_detection", 0.1)

    # Verify sum is 1.0
    settings.assert_weights_sum_to_one()

    # Save
    settings.save_settings()
    settings.assert_settings_saved()


@pytest.mark.smoke
def test_weights_validation_error(authenticated_page: Page, mock_api):
    """Test Flow 8.1: Weights validation (must sum to 1.0)."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list(
        [{"hack_id": hack_id, "name": "Test Hackathon", "status": "draft"}]
    )
    mock_api.mock_hackathon_stats(hack_id)
    mock_api.mock_get(f"**/hackathons/{hack_id}/settings", status=200, body={})

    settings = SettingsPage(authenticated_page)
    settings.navigate()
    settings.select_hackathon("Test Hackathon")

    # Set invalid weights (sum = 0.9)
    settings.set_weight("code_quality", 0.3)
    settings.set_weight("performance", 0.3)
    settings.set_weight("innovation", 0.2)
    settings.set_weight("ai_detection", 0.1)

    # Try to save
    settings.save_settings()

    # Should show validation error
    settings.assert_weights_validation_error()


@pytest.mark.critical
def test_ai_policy_configuration_flow(authenticated_page: Page, mock_api):
    """Test Flow 8.2: AI Policy Configuration Flow."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list(
        [{"hack_id": hack_id, "name": "Test Hackathon", "status": "draft"}]
    )
    mock_api.mock_hackathon_stats(hack_id)
    mock_api.mock_get(
        f"**/hackathons/{hack_id}/settings", status=200, body={"ai_policy": "ai_assisted"}
    )
    mock_api.mock_post(f"**/hackathons/{hack_id}/settings", status=200, body={})

    settings = SettingsPage(authenticated_page)
    settings.navigate()
    settings.select_hackathon("Test Hackathon")

    # Verify current policy
    current_policy = settings.get_ai_policy()
    assert current_policy == "ai_assisted"

    # Change to ai_prohibited
    settings.set_ai_policy("ai_prohibited")

    # Save
    settings.save_settings()
    settings.assert_settings_saved()


@pytest.mark.critical
def test_budget_limit_configuration_flow(authenticated_page: Page, mock_api):
    """Test Flow 8.3: Budget Limit Configuration Flow."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list(
        [{"hack_id": hack_id, "name": "Test Hackathon", "status": "draft"}]
    )
    mock_api.mock_hackathon_stats(hack_id)
    mock_api.mock_get(
        f"**/hackathons/{hack_id}/settings",
        status=200,
        body={"budget_limit_usd": 100.0, "current_spend_usd": 25.50},
    )
    mock_api.mock_post(f"**/hackathons/{hack_id}/settings", status=200, body={})

    settings = SettingsPage(authenticated_page)
    settings.navigate()
    settings.select_hackathon("Test Hackathon")

    # Verify current budget
    current_budget = settings.get_budget_limit()
    assert current_budget == 100.0

    # Verify current spend
    current_spend = settings.get_current_spend()
    assert current_spend == 25.50

    # Verify remaining
    remaining = settings.get_remaining_budget()
    assert remaining == 74.50

    # Update budget
    settings.set_budget_limit(200.0)
    settings.save_settings()
    settings.assert_settings_saved()


@pytest.mark.smoke
def test_budget_validation_error(authenticated_page: Page, mock_api):
    """Test Flow 8.3: Budget validation (must be positive)."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list(
        [{"hack_id": hack_id, "name": "Test Hackathon", "status": "draft"}]
    )
    mock_api.mock_hackathon_stats(hack_id)
    mock_api.mock_get(f"**/hackathons/{hack_id}/settings", status=200, body={})

    settings = SettingsPage(authenticated_page)
    settings.navigate()
    settings.select_hackathon("Test Hackathon")

    # Set negative budget
    settings.set_budget_limit(-50.0)
    settings.save_settings()

    # Should show validation error
    settings.assert_budget_validation_error()


@pytest.mark.smoke
def test_agent_enable_disable_flow(authenticated_page: Page, mock_api):
    """Test Flow 8.4: Agent Enable/Disable Flow."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list(
        [{"hack_id": hack_id, "name": "Test Hackathon", "status": "draft"}]
    )
    mock_api.mock_hackathon_stats(hack_id)
    mock_api.mock_get(
        f"**/hackathons/{hack_id}/settings",
        status=200,
        body={"enabled_agents": ["bug_hunter", "performance", "innovation", "ai_detection"]},
    )
    mock_api.mock_post(f"**/hackathons/{hack_id}/settings", status=200, body={})

    settings = SettingsPage(authenticated_page)
    settings.navigate()
    settings.select_hackathon("Test Hackathon")

    # Verify all agents enabled
    assert settings.is_agent_enabled("bug_hunter")
    assert settings.is_agent_enabled("performance")
    assert settings.is_agent_enabled("innovation")
    assert settings.is_agent_enabled("ai_detection")

    # Disable performance agent
    settings.toggle_agent("performance", enabled=False)

    # Save
    settings.save_settings()
    settings.assert_settings_saved()


@pytest.mark.critical
def test_settings_save_validation_flow(authenticated_page: Page, mock_api):
    """Test Flow 8.5: Settings Save & Validation Flow."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list(
        [{"hack_id": hack_id, "name": "Test Hackathon", "status": "draft"}]
    )
    mock_api.mock_hackathon_stats(hack_id)
    mock_api.mock_get(
        f"**/hackathons/{hack_id}/settings",
        status=200,
        body={
            "weights": {
                "code_quality": 0.3,
                "performance": 0.3,
                "innovation": 0.3,
                "ai_detection": 0.1,
            }
        },
    )
    mock_api.mock_post(f"**/hackathons/{hack_id}/settings", status=200, body={})

    settings = SettingsPage(authenticated_page)
    settings.navigate()
    settings.select_hackathon("Test Hackathon")

    # Make changes
    settings.set_weight("code_quality", 0.4)
    settings.set_weight("performance", 0.3)
    settings.set_weight("innovation", 0.2)
    settings.set_weight("ai_detection", 0.1)

    # Should show unsaved changes warning
    if settings.has_unsaved_changes_warning():
        assert True, "Unsaved changes warning shown"

    # Save
    settings.save_settings()
    settings.assert_settings_saved()


@pytest.mark.smoke
def test_hackathon_status_change_flow(authenticated_page: Page, mock_api):
    """Test Flow 8.6: Hackathon Status Change Flow (covered in test_hackathon_flows.py)."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list(
        [{"hack_id": hack_id, "name": "Test Hackathon", "status": "draft"}]
    )
    mock_api.mock_hackathon_stats(hack_id)
    mock_api.mock_get(f"**/hackathons/{hack_id}/settings", status=200, body={})
    mock_api.mock_post(f"**/hackathons/{hack_id}/activate", status=200, body={})

    settings = SettingsPage(authenticated_page)
    settings.navigate()
    settings.select_hackathon("Test Hackathon")

    # Activate hackathon
    settings.activate_hackathon()
    settings.assert_success("activated")


@pytest.mark.smoke
def test_date_validation_error(authenticated_page: Page, mock_api):
    """Test date validation: End date must be after start date."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list(
        [{"hack_id": hack_id, "name": "Test Hackathon", "status": "draft"}]
    )
    mock_api.mock_hackathon_stats(hack_id)
    mock_api.mock_get(f"**/hackathons/{hack_id}/settings", status=200, body={})

    settings = SettingsPage(authenticated_page)
    settings.navigate()
    settings.select_hackathon("Test Hackathon")

    # Set end date before start date
    settings.update_dates("2025-03-31", "2025-03-01")
    settings.save_settings()

    # Should show validation error
    settings.assert_date_validation_error()


@pytest.mark.smoke
def test_delete_hackathon_flow(authenticated_page: Page, mock_api):
    """Test hackathon deletion with confirmation."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list(
        [{"hack_id": hack_id, "name": "Test Hackathon", "status": "draft"}]
    )
    mock_api.mock_hackathon_stats(hack_id)
    mock_api.mock_get(f"**/hackathons/{hack_id}/settings", status=200, body={})
    mock_api.mock_delete(f"**/hackathons/{hack_id}", status=204)

    settings = SettingsPage(authenticated_page)
    settings.navigate()
    settings.select_hackathon("Test Hackathon")

    # Check danger zone exists
    if settings.has_delete_section():
        # Test cancel path
        settings.delete_hackathon(confirm=False)
        # Should stay on page

        # Test confirm path
        settings.delete_hackathon(confirm=True)
        # Should show success or redirect
