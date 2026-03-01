# VibeJudge E2E Testing Strategy

## Overview

This document explains the dual testing approach for VibeJudge and how to use each method effectively.

## Testing Layers

VibeJudge uses a three-layer testing strategy:

```
Layer 1: Unit Tests (Backend)
   ├── Fast, isolated backend logic tests
   └── Location: backend/tests/

Layer 2: Integration Tests (Streamlit AppTest)
   ├── Component-level UI testing
   ├── Fast, no browser needed
   ├── 330 tests covering all UI flows
   └── Location: streamlit_ui/tests/

Layer 3: E2E Tests (Playwright)
   ├── Real browser automation
   ├── Critical user journeys
   ├── Visual regression testing
   └── Location: e2e_tests/
```

## Why Two Approaches for E2E Tests?

### Approach 1: Mocked API (Fast, Isolated)

**Use Case**: Development, PR validation, quick feedback

```python
def test_analysis_flow(authenticated_page: Page, mock_api):
    """Test with mocked API - fast and deterministic."""
    mock_api.mock_hackathons_list([...])
    mock_api.mock_start_analysis(hack_id, job_id="job_001")

    # Test runs entirely in-memory, no backend needed
    dashboard = LiveDashboardPage(authenticated_page)
    dashboard.start_analysis()
    # ... test continues
```

**Advantages:**
- ⚡ Fast (no network calls)
- 🎯 Deterministic (no flaky tests)
- 🔒 Isolated (no dependencies)
- 💰 No AWS costs
- 🚀 Can run without backend

**Disadvantages:**
- ❌ Not true end-to-end
- ❌ Misses integration bugs
- ❌ Needs mock maintenance

### Approach 2: Live API (True E2E)

**Use Case**: Pre-release validation, integration testing

```python
def test_complete_flow(page: Page):
    """Test against live API - true end-to-end."""
    # No mocking - talks to real backend
    page.goto("http://localhost:8501")

    # Real user flow
    login_page = LoginPage(page)
    login_page.login_with_api_key(REAL_API_KEY)

    # Creates actual data in database
    dashboard = LiveDashboardPage(page)
    dashboard.create_hackathon("E2E Test")
    # ... continues with real API calls
```

**Advantages:**
- ✅ True end-to-end validation
- ✅ Catches integration bugs
- ✅ Tests real authentication
- ✅ Validates API contracts

**Disadvantages:**
- 🐌 Slower (network + DB calls)
- 💸 AWS costs (DynamoDB, Lambda)
- 🔧 Requires backend setup
- 🎲 Potential flakiness

## Recommended Strategy

### For Development
```bash
# Run existing AppTest suite (330 tests, ~2 min)
pytest streamlit_ui/tests/ -v

# Run simple Playwright smoke tests (no backend needed)
pytest e2e_tests/tests/test_simple_e2e.py -v
```

### For PR Validation
```bash
# Run mocked E2E tests (fast, isolated)
pytest e2e_tests/tests/ -m smoke --mock
```

### For Pre-Release
```bash
# Run true E2E tests against staging
E2E_BASE_URL=https://staging.vibejudge.com \
API_BASE_URL=https://api-staging.vibejudge.com \
pytest e2e_tests/tests/ -m critical
```

## Test Organization

### Simple E2E Tests (Always Run)
**File**: `test_simple_e2e.py`

- App loads correctly
- Navigation works
- No errors on page load
- Sidebar visible

**Status**: ✅ 3/3 passing

### Component Tests (With Mocking)
**Files**: `test_auth_flows.py`, `test_hackathon_flows.py`, etc.

- Use `mock_api` fixture
- Fast, deterministic
- Cover all UI flows

**Status**: ⚠️ Needs selector refinement for Streamlit

### Integration Tests (Live API)
**Files**: To be created as needed

- Real backend required
- Slower but comprehensive
- Critical paths only

**Status**: 🔜 Future work

## Current Status

### ✅ Working
- Playwright infrastructure (100%)
- Simple E2E tests (3/3 passing)
- Page Object Model (9 classes)
- API mocking framework
- CI/CD workflow
- Documentation

### ⏳ In Progress
- Streamlit selector refinement
- Validation with mocked APIs
- Complete test suite execution

### 🔜 Future
- Live API integration tests
- Visual regression baselines
- Performance testing

## How to Choose

| Scenario | Use This |
|----------|----------|
| Quick validation | AppTest (Layer 2) |
| Feature development | Mocked Playwright |
| PR checks | Mocked Playwright (smoke) |
| Pre-deployment | Live API Playwright (critical) |
| Visual changes | Playwright (screenshots) |
| API contract testing | Live API |

## Running Tests

### Option 1: AppTest (Current Approach)
```bash
# Fast, comprehensive, no browser
pytest streamlit_ui/tests/ -v
# Result: 330/330 passing ✅
```

### Option 2: Simple Playwright E2E
```bash
# Basic browser validation
pytest e2e_tests/tests/test_simple_e2e.py -v
# Result: 3/3 passing ✅
```

### Option 3: Full Playwright Suite (Future)
```bash
# Comprehensive browser testing
pytest e2e_tests/tests/ -v
# Status: Selector refinement needed
```

## Conclusion

**Current Recommendation**:
Continue using **AppTest for comprehensive testing** (330 tests) and **Playwright for critical E2E flows** once selectors are refined.

The infrastructure is complete and working. The remaining work is:
1. Refining selectors for Streamlit's DOM (1-2 hours)
2. Deciding which flows need true browser testing vs AppTest
3. Creating live API integration tests as needed

**Bottom Line**: You have excellent test coverage with AppTest. Playwright adds value for:
- Visual regression testing
- True browser behavior validation
- Cross-browser compatibility
- Critical user journey validation
