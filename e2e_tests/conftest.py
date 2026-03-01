"""Pytest configuration and fixtures for E2E tests."""

import os
import sys
from collections.abc import Generator

import pytest
from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

# Add e2e_tests to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from playwright_config import BROWSER_CONFIG, DEFAULT_TIMEOUT, DESKTOP_VIEWPORT, TEST_API_KEY

# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "smoke: Quick smoke tests for CI/CD")
    config.addinivalue_line("markers", "critical: Critical user flows that must work")
    config.addinivalue_line("markers", "slow: Long-running tests (analysis completion, etc.)")
    config.addinivalue_line("markers", "visual: Visual regression tests")
    config.addinivalue_line("markers", "integration: Tests requiring real backend")
    config.addinivalue_line("markers", "unit: Unit-level E2E tests with mocked API")


# ============================================================================
# BROWSER FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def playwright_instance() -> Generator[Playwright, None, None]:
    """Shared Playwright instance for session."""
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser(playwright_instance: Playwright) -> Generator[Browser, None, None]:
    """Shared browser instance for all tests in session."""
    browser = playwright_instance.chromium.launch(**BROWSER_CONFIG)
    yield browser
    browser.close()


@pytest.fixture(scope="function")
def context(browser: Browser) -> Generator[BrowserContext, None, None]:
    """New browser context for each test (isolated cookies/session)."""
    context = browser.new_context(
        viewport=DESKTOP_VIEWPORT,
        locale="en-US",
        timezone_id="America/Los_Angeles",
    )

    # Set default timeout
    context.set_default_timeout(DEFAULT_TIMEOUT)

    yield context
    context.close()


@pytest.fixture(scope="function")
def page(context: BrowserContext) -> Generator[Page, None, None]:
    """New page for each test."""
    page = context.new_page()
    yield page
    page.close()


# ============================================================================
# AUTHENTICATION FIXTURES
# ============================================================================


@pytest.fixture(scope="function")
def authenticated_page(page: Page) -> Page:
    """Page with API key authentication already completed."""
    from pages.login_page import LoginPage

    login_page = LoginPage(page)
    login_page.navigate()
    login_page.login_with_api_key(TEST_API_KEY)

    return page


@pytest.fixture(scope="function")
def authenticated_context(browser: Browser) -> Generator[BrowserContext, None, None]:
    """Authenticated browser context that can be reused for multiple pages."""
    context = browser.new_context(viewport=DESKTOP_VIEWPORT)
    page = context.new_page()

    from pages.login_page import LoginPage

    login_page = LoginPage(page)
    login_page.navigate()
    login_page.login_with_api_key(TEST_API_KEY)

    page.close()
    yield context
    context.close()


# ============================================================================
# API MOCK FIXTURES
# ============================================================================


@pytest.fixture(scope="function")
def mock_api(context: BrowserContext):
    """API mocking helper for isolated tests."""
    from fixtures.api_mocks import APIMock

    return APIMock(context)


@pytest.fixture(scope="function")
def mock_backend_healthy(mock_api):
    """Mock healthy backend with all endpoints."""
    mock_api.mock_health_check()
    mock_api.mock_hackathons_list()
    return mock_api


# ============================================================================
# HACKATHON SETUP FIXTURES
# ============================================================================


@pytest.fixture(scope="function")
def hackathon_setup(authenticated_page: Page):
    """Create a test hackathon for testing."""
    from pages.create_hackathon_page import CreateHackathonPage

    create_page = CreateHackathonPage(authenticated_page)
    create_page.navigate()

    hack_id = create_page.create_hackathon(
        name="E2E Test Hackathon",
        description="Automated test hackathon for E2E testing",
        start_date="2025-03-01",
        end_date="2025-03-31",
    )

    return {"hack_id": hack_id, "name": "E2E Test Hackathon", "page": authenticated_page}


@pytest.fixture(scope="function")
def hackathon_with_submissions(hackathon_setup, mock_api):
    """Hackathon with mock submissions."""
    hack_id = hackathon_setup["hack_id"]

    # Mock leaderboard with submissions
    mock_api.mock_leaderboard_with_submissions(hack_id, count=10)

    return hackathon_setup


# ============================================================================
# SCREENSHOT & REPORTING FIXTURES
# ============================================================================


@pytest.fixture(scope="function", autouse=True)
def screenshot_on_failure(request, page: Page):
    """Automatically take screenshot on test failure."""
    yield

    # Check if test failed (handle missing attribute gracefully)
    if hasattr(request.node, "rep_call") and request.node.rep_call.failed:
        screenshot_dir = "e2e_tests/visual_regression/failures"
        os.makedirs(screenshot_dir, exist_ok=True)

        test_name = request.node.name
        screenshot_path = f"{screenshot_dir}/{test_name}.png"
        page.screenshot(path=screenshot_path)
        print(f"\n📸 Screenshot saved: {screenshot_path}")


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Store test result for screenshot fixture."""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


# ============================================================================
# TEST DATA FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def test_data_loader():
    """Load test data from JSON files."""
    import json

    from playwright_config import TEST_DATA_DIR

    def load(filename: str):
        path = os.path.join(TEST_DATA_DIR, filename)
        with open(path) as f:
            return json.load(f)

    return load
