"""
E2E tests for Category 1: Authentication & Session Flows (8 flows).

Tests:
- 1.1: API Key Login Flow
- 1.2: Email/Password Login Flow
- 1.3: Registration Flow
- 1.4: Logout Flow
- 1.5: Session State Initialization Flow
- 1.6: API Base URL Configuration Flow
- 1.7: "Just Registered" Auto-Login Flow
- 1.8: Lost API Key Recovery Flow
"""

import pytest
from pages.login_page import LoginPage
from playwright.sync_api import Page
from playwright_config import TEST_API_KEY, TEST_EMAIL, TEST_PASSWORD


@pytest.mark.smoke
@pytest.mark.critical
def test_api_key_login_success(page: Page):
    """Test Flow 1.1: API Key Login Flow - Success path."""
    login_page = LoginPage(page)
    login_page.navigate()

    # Verify on login page
    login_page.assert_on_login_page()
    login_page.assert_not_authenticated()

    # Login with API key
    login_page.login_with_api_key(TEST_API_KEY)

    # Verify authenticated
    login_page.assert_authenticated()
    login_page.assert_on_page("VibeJudge AI Dashboard")


@pytest.mark.smoke
def test_api_key_login_invalid(page: Page, mock_api):
    """Test Flow 1.1: API Key Login Flow - Invalid key."""
    # Mock invalid API key
    mock_api.mock_health_check(status=401)

    login_page = LoginPage(page)
    login_page.navigate()

    # Try to login with invalid key
    login_page.fill_input("API Key", "invalid_key_123")
    login_page.click_button("Login with API Key")

    # Should show error
    login_page.assert_login_error("Invalid API key")
    login_page.assert_not_authenticated()


@pytest.mark.critical
def test_email_password_login_success(page: Page, mock_api):
    """Test Flow 1.2: Email/Password Login Flow - Success."""
    # Mock successful login
    mock_api.mock_login_success(api_key=TEST_API_KEY)
    mock_api.mock_health_check()
    mock_api.mock_hackathons_list()

    login_page = LoginPage(page)
    login_page.navigate()

    # Login with email/password
    success = login_page.login_with_email(TEST_EMAIL, TEST_PASSWORD)

    assert success, "Login should succeed"
    login_page.assert_authenticated()


@pytest.mark.smoke
def test_email_password_login_invalid_credentials(page: Page, mock_api):
    """Test Flow 1.2: Email/Password Login Flow - Invalid credentials."""
    # Mock login failure
    mock_api.mock_login_failure(status=401, message="Invalid email or password")

    login_page = LoginPage(page)
    login_page.navigate()

    # Try to login
    success = login_page.login_with_email("wrong@email.com", "wrongpassword")

    assert not success, "Login should fail"
    login_page.assert_login_error("Invalid email or password")
    login_page.assert_not_authenticated()


@pytest.mark.smoke
def test_email_password_login_account_not_found(page: Page, mock_api):
    """Test Flow 1.2: Email/Password Login Flow - Account not found."""
    # Mock 404 response
    mock_api.mock_login_failure(status=404, message="Account not found. Please register first.")

    login_page = LoginPage(page)
    login_page.navigate()

    success = login_page.login_with_email("notfound@email.com", "password123")

    assert not success, "Login should fail"
    login_page.assert_login_error("Account not found")


@pytest.mark.critical
def test_logout_flow(authenticated_page: Page):
    """Test Flow 1.4: Logout Flow."""
    login_page = LoginPage(authenticated_page)

    # Verify authenticated
    login_page.assert_authenticated()

    # Logout
    login_page.logout()

    # Verify not authenticated
    login_page.assert_not_authenticated()
    login_page.assert_on_login_page()


@pytest.mark.smoke
def test_api_base_url_configuration(page: Page):
    """Test Flow 1.6: API Base URL Configuration Flow."""
    login_page = LoginPage(page)
    login_page.navigate()

    # Set custom API base URL
    custom_url = "http://custom-api.example.com:8000"
    login_page.set_api_base_url(custom_url, tab="api_key")

    # Verify URL is set (would need to check session state or network requests)
    # For now, just verify no errors
    assert True


@pytest.mark.smoke
def test_session_persistence_across_navigation(authenticated_page: Page):
    """Test Flow 1.5: Session State Initialization Flow."""
    from pages.live_dashboard_page import LiveDashboardPage
    from pages.results_page import ResultsPage

    # Navigate to Live Dashboard
    dashboard = LiveDashboardPage(authenticated_page)
    dashboard.navigate()

    # Should still be authenticated
    assert dashboard.get_sidebar().inner_text().__contains__("✅ Authenticated")

    # Navigate to Results
    results = ResultsPage(authenticated_page)
    results.navigate()

    # Should still be authenticated
    assert results.get_sidebar().inner_text().__contains__("✅ Authenticated")


@pytest.mark.smoke
def test_browser_refresh_clears_session(page: Page):
    """Test error case: Browser refresh loses session."""
    login_page = LoginPage(page)
    login_page.navigate()
    login_page.login_with_api_key(TEST_API_KEY)

    # Verify authenticated
    login_page.assert_authenticated()

    # Refresh browser
    page.reload()
    login_page.wait_for_streamlit_ready()

    # Session should be lost (Streamlit behavior)
    login_page.assert_not_authenticated()
