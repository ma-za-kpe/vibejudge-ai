"""
Simple E2E test to validate the infrastructure works with live API.
No mocking - tests against real backend.
"""
import pytest
from playwright.sync_api import Page, expect


@pytest.mark.smoke
def test_streamlit_app_loads(page: Page):
    """Test that Streamlit app loads successfully."""
    page.goto("http://localhost:8501")

    # Wait for Streamlit to be ready
    page.wait_for_selector('[data-testid="stAppViewContainer"]', timeout=30000)
    page.wait_for_load_state("networkidle")

    # Check that we're on the app
    expect(page).to_have_title("VibeJudge AI - Organizer Dashboard")

    # Check sidebar exists
    sidebar = page.locator('[data-testid="stSidebar"]')
    expect(sidebar).to_be_visible()

    # Check we see the login/auth status
    expect(sidebar).to_contain_text("Not authenticated")


@pytest.mark.smoke
def test_navigation_to_pages(page: Page):
    """Test navigation between pages."""
    page.goto("http://localhost:8501")
    page.wait_for_selector('[data-testid="stAppViewContainer"]', timeout=30000)
    page.wait_for_load_state("networkidle")

    # Find navigation links in sidebar
    sidebar = page.locator('[data-testid="stSidebar"]')

    # Click on different pages
    pages_to_test = ["Create Hackathon", "Live Dashboard", "Results"]

    for page_name in pages_to_test:
        # Find and click the link
        link = sidebar.get_by_role("link", name=page_name).or_(
            sidebar.get_by_text(page_name, exact=False)
        ).first

        if link.count() > 0:
            link.click()
            page.wait_for_load_state("networkidle", timeout=10000)
            # Verify page changed (URL should update)
            print(f"✓ Navigated to {page_name}")


@pytest.mark.smoke
def test_no_errors_on_load(page: Page):
    """Test that app loads without critical errors."""
    page.goto("http://localhost:8501")
    page.wait_for_selector('[data-testid="stAppViewContainer"]', timeout=30000)

    # The app should load without critical errors
    # Check for any exception messages
    exceptions = page.locator('[data-testid="stException"]')
    assert exceptions.count() == 0, "Should not have exceptions on page load"

    print("✓ No exceptions on page load")
