# VibeJudge E2E Test Suite

End-to-end browser testing for the VibeJudge Streamlit dashboard using Playwright.

## 📋 Overview

This test suite provides comprehensive E2E coverage of all frontend flows identified in the VibeJudge application. Tests run in real browsers (Chromium, Firefox, WebKit) and verify user-facing functionality, UI interactions, and integration with the backend API.

**Coverage**: 97 user flows across 15 categories
**Test Files**: 11 test suites
**Page Objects**: 9 reusable page classes
**Markers**: `smoke`, `critical`, `slow`, `visual`

## 🏗️ Architecture

### Page Object Model (POM)

Tests use the Page Object Model pattern for maintainability:

```
e2e_tests/
├── pages/                    # Page object classes
│   ├── base_page.py         # Base class with Streamlit utilities
│   ├── login_page.py        # Authentication page
│   ├── live_dashboard_page.py  # Analysis dashboard
│   ├── results_page.py      # Leaderboard & results
│   ├── create_hackathon_page.py
│   ├── intelligence_page.py
│   ├── settings_page.py
│   ├── manage_hackathons_page.py
│   ├── submit_page.py       # Public submission
│   └── submissions_page.py  # Organizer view
├── tests/                    # Test suites (11 files)
├── fixtures/                 # Test utilities
│   └── api_mocks.py         # API mocking helpers
├── visual_regression/        # Screenshots
├── reports/                  # Test reports
└── test_data/               # Test data fixtures
```

### API Mocking

Tests can run in two modes:

1. **Isolated (mocked)**: Fast, deterministic, mocked API responses
2. **Integration (real)**: Full E2E with real backend

Use the `mock_api` fixture for isolated tests:

```python
def test_example(authenticated_page: Page, mock_api):
    mock_api.mock_hackathons_list([...])
    mock_api.mock_hackathon_stats(hack_id)
    # Test runs with mocked data
```

## 🚀 Getting Started

### Prerequisites

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### Configuration

Environment variables (see `playwright_config.py`):

```bash
# Streamlit app URL
export E2E_BASE_URL=http://localhost:8501

# API URL
export API_BASE_URL=http://localhost:8000

# Test credentials
export TEST_API_KEY=vj_test_key_12345
export TEST_EMAIL=test@example.com
export TEST_PASSWORD=testpassword123

# Browser mode
export HEADLESS=true  # Set to false for headed mode
```

### Running Tests

```bash
# Run all tests
npm run test:e2e

# Run smoke tests only (fast, critical paths)
npm run test:smoke

# Run critical tests only
npm run test:critical

# Run in headed mode (see browser)
npm run test:headed

# Run with debugger
npm run test:debug

# Run specific test file
pytest e2e_tests/tests/test_auth_flows.py -v

# Run specific test
pytest e2e_tests/tests/test_analysis_flows.py::test_complete_analysis_lifecycle_with_mock -xvs

# Run tests in parallel
npm run test:parallel
```

## 📊 Test Categories

### Category 1: Authentication & Session (8 flows)
- API key login
- Email/password login
- Registration
- Logout
- Session persistence
- API base URL configuration

**File**: `test_auth_flows.py`

### Category 2: Hackathon Management (7 flows)
- Hackathon creation
- Listing, filtering, sorting
- Status lifecycle (DRAFT → ACTIVE → PAUSED → COMPLETED)
- Search and pagination

**File**: `test_hackathon_flows.py`

### Category 3: Submission Management (6 flows)
- Public submission form
- Verification/rejection (organizer)
- Filtering, bulk actions
- Export

**File**: `test_submission_flows.py`

### Category 4: Analysis Lifecycle (10 flows)
- **7-state lifecycle**: no_job → estimating → confirming → running → completed
- Cost estimation
- Progress polling
- Budget exceeded errors (HTTP 402)
- Concurrent analysis conflicts (HTTP 409)
- Analysis cancellation

**File**: `test_analysis_flows.py`

### Category 5: Stats Display (3 flows)
- Stats display after selection
- Auto-refresh behavior
- Error handling

**File**: `test_stats_flows.py`

### Category 6: Results & Leaderboard (12 flows)
- Leaderboard display
- Search, filtering, sorting
- Pagination (50 per page)
- Team detail navigation
- Scorecard tabs (4 tabs: Overview, Agent Analysis, Repository, Team Members)
- Back to leaderboard

**File**: `test_results_flows.py`

### Category 7: Intelligence Insights (5 flows)
- Tech stack analysis
- Team size distribution
- AI usage insights
- Filtering and export

**File**: `test_intelligence_flows.py`

### Category 8: Settings & Configuration (7 flows)
- Scoring weights configuration
- AI policy settings
- Budget limit management
- Agent enable/disable
- Settings validation

**File**: `test_settings_flows.py`

## 🎯 Test Markers

Tests are tagged with pytest markers for selective execution:

- **`@pytest.mark.smoke`**: Fast, critical path tests (~30 tests, ~5 min)
- **`@pytest.mark.critical`**: Must-pass tests for core functionality
- **`@pytest.mark.slow`**: Tests that take >30 seconds (e.g., full lifecycle)
- **`@pytest.mark.visual`**: Tests with screenshot capture for visual regression

### Running by marker

```bash
# Smoke tests only
pytest -m smoke

# Critical tests only
pytest -m critical

# Exclude slow tests
pytest -m "not slow"

# Smoke AND critical
pytest -m "smoke and critical"
```

## 📸 Visual Regression Testing

Screenshots are automatically captured on test failures:

```
e2e_tests/visual_regression/
├── failures/           # Failure screenshots
│   └── test_name.png
└── baseline/          # Baseline screenshots (optional)
```

Manual screenshot capture in tests:

```python
dashboard.take_screenshot("state_1_no_job")
```

## 🐛 Debugging

### Headed Mode

Watch tests run in a real browser:

```bash
npm run test:headed
```

### Debug Mode

Interactive debugger:

```bash
npm run test:debug
pytest e2e_tests/tests/test_analysis_flows.py --headed --pdb
```

### Playwright Inspector

```bash
PWDEBUG=1 pytest e2e_tests/tests/test_auth_flows.py
```

### Verbose Output

```bash
pytest -xvs  # -x: stop on first failure, -v: verbose, -s: show print statements
```

## 🔧 Fixtures

### `page` (Playwright page)

Fresh browser page for each test.

### `authenticated_page`

Pre-authenticated page with API key login completed.

```python
def test_example(authenticated_page: Page):
    # Already logged in
    dashboard = LiveDashboardPage(authenticated_page)
    dashboard.navigate()
```

### `mock_api` (APIMock)

API mocking helper for isolated tests.

```python
def test_example(authenticated_page: Page, mock_api):
    mock_api.mock_hackathons_list([...])
    mock_api.mock_cost_estimate(hack_id, cost=15.75)
    mock_api.mock_analysis_lifecycle(hack_id, job_id="job_001")
```

### `context` (BrowserContext)

Shared browser context for session isolation.

### `browser` (Browser)

Browser instance (Chromium by default).

## 📦 Continuous Integration

GitHub Actions workflow runs E2E tests on every PR and push to main.

```yaml
# .github/workflows/e2e-tests.yml
- Smoke tests on PR (fast)
- Full suite on main branch
- Screenshot upload on failure
- HTML test report artifact
```

## 🎨 Streamlit-Specific Utilities

The `BasePage` class provides Streamlit-specific helpers:

```python
# Wait for app ready
self.wait_for_streamlit_ready()

# Button interactions (handles Streamlit's button rendering)
self.click_button("Start Analysis")
self.is_button_visible("🚀 Submit")
self.is_button_disabled("Next ▶️")

# Metric extraction
value = self.get_metric("Total Submissions")

# Form inputs
self.fill_input("Team Name", "My Team")
self.select_option("Select Hackathon", "Test Hack")
self.check_checkbox("I agree", True)

# Wait for spinners to disappear
self.wait_for_spinner_gone()

# Assertions
self.assert_success("Analysis completed")
self.assert_error("Budget exceeded")
self.assert_text_visible("Welcome")
```

## 📝 Writing New Tests

### 1. Create Page Object (if needed)

```python
# e2e_tests/pages/my_page.py
from pages.base_page import BasePage

class MyPage(BasePage):
    def navigate(self):
        super().navigate("My_Page_Name")

    def do_action(self):
        self.click_button("Action Button")
```

### 2. Write Test

```python
# e2e_tests/tests/test_my_flows.py
import pytest
from pages.my_page import MyPage

@pytest.mark.smoke
def test_my_flow(authenticated_page: Page, mock_api):
    \"\"\"Test Flow X.Y: Description.\"\"\"
    # Arrange
    mock_api.mock_something()

    # Act
    page = MyPage(authenticated_page)
    page.navigate()
    page.do_action()

    # Assert
    page.assert_success("Action completed")
```

### 3. Run Test

```bash
pytest e2e_tests/tests/test_my_flows.py::test_my_flow -xvs
```

## 🚨 Common Issues

### Timeout waiting for element

**Problem**: `TimeoutError: Timeout waiting for selector`

**Solution**: Increase timeout or wait for Streamlit to be ready:

```python
self.wait_for_streamlit_ready(timeout=60000)
```

### Element not interactable

**Problem**: `Error: Element is not visible`

**Solution**: Wait for element to be visible:

```python
button = self.page.get_by_role("button", name="Submit")
button.wait_for(state="visible", timeout=10000)
button.click()
```

### Stale session state

**Problem**: Test passes locally but fails in CI

**Solution**: Always call `wait_for_streamlit_ready()` after navigation or interactions that trigger `st.rerun()`.

## 📚 Resources

- [Playwright Docs](https://playwright.dev/python/)
- [Pytest Docs](https://docs.pytest.org/)
- [Streamlit Testing Guide](https://docs.streamlit.io/develop/concepts/app-testing)
- [VibeJudge API Docs](../backend/README.md)

## 🤝 Contributing

1. Write tests for new features before implementation (TDD)
2. Use Page Object Model pattern
3. Add pytest markers (`@pytest.mark.smoke`, `@pytest.mark.critical`)
4. Include docstrings with flow references
5. Capture screenshots for visual flows
6. Run smoke tests before committing: `npm run test:smoke`

## 📊 Test Coverage Report

Current coverage (as of 2025-02-28):

| Category | Flows | Status |
|----------|-------|--------|
| 1. Authentication | 8 | ✅ Complete |
| 2. Hackathon Management | 7 | ✅ Complete |
| 3. Submission Management | 6 | ✅ Complete |
| 4. Analysis Lifecycle | 10 | ✅ Complete |
| 5. Stats Display | 3 | ✅ Complete |
| 6. Results & Leaderboard | 12 | ✅ Complete |
| 7. Intelligence Insights | 5 | ✅ Complete |
| 8. Settings | 7 | ✅ Complete |
| **Total** | **58/97** | **60% Coverage** |

**Next Priority**: Error handling, navigation, form validation flows.
