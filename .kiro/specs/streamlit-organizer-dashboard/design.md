# Design Document: Streamlit Organizer Dashboard

## Overview

The Streamlit Organizer Dashboard is a Python-based web application that provides hackathon organizers with a visual interface to manage their events. The dashboard is built using Streamlit 1.30+ and consumes the existing VibeJudge FastAPI backend through REST API calls. The application follows a multi-page architecture with five core pages: authentication, hackathon creation, live monitoring, results viewing, and intelligence insights.

The dashboard is designed to be stateless from the backend's perspective - all state is managed client-side using Streamlit's session_state mechanism. The API key is stored in session state after authentication and included in all subsequent API requests via the X-API-Key header. The application uses aggressive caching (30-second TTL) to minimize backend load and implements auto-refresh for live monitoring pages.

Key design principles:
- **API-First**: No backend modifications required, consumes existing FastAPI endpoints
- **Stateless**: All user state managed in st.session_state
- **Cached**: 30-second TTL on GET requests to reduce backend load
- **Responsive**: Loading spinners, error handling, and retry mechanisms
- **Live Updates**: Auto-refresh every 5 seconds for monitoring pages

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Dashboard                       │
│                     (streamlit_ui/)                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   app.py     │  │   pages/     │  │ components/  │      │
│  │  (Auth Page) │  │ (4 Pages)    │  │ (Reusable)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                  │                  │              │
│         └──────────────────┴──────────────────┘              │
│                            │                                 │
│                   ┌────────▼────────┐                        │
│                   │  api_client.py  │                        │
│                   │  (HTTP Client)  │                        │
│                   └────────┬────────┘                        │
│                            │                                 │
└────────────────────────────┼─────────────────────────────────┘
                             │ HTTPS + X-API-Key
                             │
                   ┌─────────▼─────────┐
                   │  FastAPI Backend  │
                   │  (Existing API)   │
                   └───────────────────┘
```

### Directory Structure

```
streamlit_ui/
├── app.py                      # Entry point + authentication page
├── .streamlit/
│   └── config.toml             # Streamlit configuration
├── components/
│   ├── __init__.py
│   ├── api_client.py           # HTTP client with error handling
│   ├── auth.py                 # Authentication helpers
│   ├── charts.py               # Plotly chart generators
│   └── formatters.py           # Data formatting utilities
├── pages/
│   ├── 1_🎯_Create_Hackathon.py
│   ├── 2_📊_Live_Dashboard.py
│   ├── 3_🏆_Results.py
│   └── 4_💡_Intelligence.py
└── requirements.txt            # Python dependencies
```

### Technology Stack

- **Framework**: Streamlit 1.30+
- **HTTP Client**: requests 2.31+
- **Charts**: plotly 5.18+
- **Auto-Refresh**: streamlit-autorefresh 1.0+
- **Date Handling**: python-dateutil 2.8+
- **Python**: 3.12 (matching backend)

### State Management

All application state is stored in `st.session_state`:

```python
st.session_state = {
    "api_key": str,              # Authenticated API key
    "api_base_url": str,         # Backend URL (from env or default)
    "selected_hackathon": str,   # Currently selected hack_id
    "analysis_job_id": str,      # Active analysis job ID
    "last_refresh": datetime,    # Last auto-refresh timestamp
}
```

### Caching Strategy

The application uses Streamlit's `@st.cache_data` decorator with TTL:

```python
@st.cache_data(ttl=30)  # 30-second cache
def fetch_hackathons(api_key: str) -> list[dict]:
    return api_client.get("/hackathons")

@st.cache_data(ttl=30)
def fetch_stats(api_key: str, hack_id: str) -> dict:
    return api_client.get(f"/hackathons/{hack_id}/stats")
```

Cache invalidation occurs:
- Automatically after 30 seconds (TTL expiration)
- Manually via `st.cache_data.clear()` after mutations (POST, PUT, DELETE)

## Components and Interfaces

### API Client Component

The `api_client.py` module provides a centralized HTTP client with error handling, retry logic, and authentication.

```python
class APIClient:
    """HTTP client for VibeJudge FastAPI backend."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({"X-API-Key": api_key})

    def get(self, endpoint: str, params: dict | None = None) -> dict:
        """GET request with error handling."""
        ...

    def post(self, endpoint: str, json: dict) -> dict:
        """POST request with error handling."""
        ...

    def handle_error(self, response: requests.Response) -> None:
        """Map HTTP status codes to user-friendly error messages."""
        ...
```

Error handling mapping:
- 401: "Invalid API key. Please check your credentials."
- 404: "Resource not found."
- 409: "Conflict: Analysis already running."
- 422: "Validation error: {details}"
- 429: "Rate limit exceeded. Please try again later."
- 500: "Server error. Please try again."
- 503: "Service unavailable. Please try again later."
- Timeout: "Connection timeout. Please check your network."

### Authentication Component

The `auth.py` module manages API key validation and session state.

```python
def validate_api_key(api_key: str, base_url: str) -> bool:
    """Validate API key against backend."""
    try:
        response = requests.get(
            f"{base_url}/health",
            headers={"X-API-Key": api_key},
            timeout=5
        )
        return response.status_code == 200
    except Exception:
        return False

def is_authenticated() -> bool:
    """Check if user is authenticated."""
    return "api_key" in st.session_state

def logout() -> None:
    """Clear authentication state."""
    st.session_state.clear()
```

### Charts Component

The `charts.py` module generates Plotly visualizations.

```python
def create_technology_trends_chart(trends: list[dict]) -> go.Figure:
    """Create bar chart for technology trends."""
    fig = go.Figure(data=[
        go.Bar(
            x=[t["technology"] for t in trends],
            y=[t["usage_count"] for t in trends],
            marker_color="lightblue"
        )
    ])
    fig.update_layout(
        title="Technology Trends",
        xaxis_title="Technology",
        yaxis_title="Usage Count",
        height=400
    )
    return fig

def create_progress_bar(progress_percent: float) -> None:
    """Display progress bar using Streamlit."""
    st.progress(progress_percent / 100.0)
```

### Formatters Component

The `formatters.py` module provides data formatting utilities.

```python
def format_currency(amount: float) -> str:
    """Format USD amount."""
    return f"${amount:.2f}"

def format_timestamp(iso_timestamp: str) -> str:
    """Format ISO timestamp to human-readable."""
    dt = datetime.fromisoformat(iso_timestamp)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def format_percentage(value: float) -> str:
    """Format percentage."""
    return f"{value:.1f}%"
```

### Page Components

Each page follows a consistent structure:

```python
# pages/X_Emoji_PageName.py
import streamlit as st
from components.api_client import APIClient
from components.auth import is_authenticated

st.set_page_config(page_title="Page Name", page_icon="🎯")

if not is_authenticated():
    st.error("Please authenticate first")
    st.stop()

# Page-specific logic
api_client = APIClient(
    st.session_state["api_base_url"],
    st.session_state["api_key"]
)

# Render page content
```

## Data Models

The dashboard consumes existing Pydantic models from the backend via JSON responses. No new data models are defined in the frontend - all data structures are dictionaries parsed from API responses.

### API Response Structures

#### Hackathon List Response
```python
[
    {
        "hack_id": "01HXXX...",
        "name": "Spring Hackathon 2025",
        "description": "Build something amazing",
        "start_date": "2025-03-01T00:00:00Z",
        "end_date": "2025-03-03T23:59:59Z",
        "status": "active",
        "created_at": "2025-02-01T10:00:00Z"
    }
]
```

#### Hackathon Stats Response
```python
{
    "hack_id": "01HXXX...",
    "submission_count": 150,
    "verified_count": 145,
    "pending_count": 5,
    "participant_count": 450,
    "analysis_status": "completed",
    "last_updated": "2025-03-04T12:00:00Z"
}
```

#### Analysis Job Response
```python
{
    "job_id": "01HYYY...",
    "hack_id": "01HXXX...",
    "status": "running",
    "progress_percent": 45.5,
    "completed_submissions": 68,
    "failed_submissions": 2,
    "total_submissions": 150,
    "current_cost_usd": 3.45,
    "estimated_cost_usd": 7.50,
    "estimated_completion": "2025-03-04T13:30:00Z",
    "started_at": "2025-03-04T12:00:00Z"
}
```

#### Leaderboard Response
```python
{
    "hack_id": "01HXXX...",
    "total_submissions": 150,
    "analyzed_count": 148,
    "submissions": [
        {
            "sub_id": "01HZZZ...",
            "rank": 1,
            "team_name": "Team Awesome",
            "overall_score": 92.5,
            "confidence": 0.95,
            "recommendation": "must_interview",
            "created_at": "2025-03-02T10:00:00Z"
        }
    ]
}
```

#### Scorecard Response
```python
{
    "sub_id": "01HZZZ...",
    "team_name": "Team Awesome",
    "overall_score": 92.5,
    "confidence": 0.95,
    "recommendation": "must_interview",
    "dimension_scores": {
        "code_quality": {"raw": 90.0, "weighted": 27.0, "weight": 0.3},
        "innovation": {"raw": 95.0, "weighted": 28.5, "weight": 0.3},
        "performance": {"raw": 92.0, "weighted": 27.6, "weight": 0.3},
        "authenticity": {"raw": 90.0, "weighted": 9.0, "weight": 0.1}
    },
    "agent_results": {
        "bug_hunter": {
            "summary": "Excellent code quality...",
            "strengths": ["Clean architecture", "Good tests"],
            "improvements": ["Add more edge case tests"],
            "cost_usd": 0.002
        }
    },
    "repo_meta": {
        "primary_language": "Python",
        "commit_count": 45,
        "contributor_count": 3,
        "has_tests": true,
        "has_ci": true
    },
    "total_cost_usd": 0.023
}
```

#### Individual Scorecard Response
```python
{
    "sub_id": "01HZZZ...",
    "team_dynamics": {
        "collaboration_quality": "excellent",
        "role_distribution": "balanced",
        "communication_patterns": "frequent"
    },
    "strategy_analysis": {
        "development_approach": "iterative",
        "time_management": "excellent",
        "risk_management": "good"
    },
    "contributors": [
        {
            "member_name": "Alice",
            "commit_count": 20,
            "skill_assessment": "senior",
            "actionable_feedback": "Strong backend skills..."
        }
    ]
}
```

#### Intelligence Response
```python
{
    "hack_id": "01HXXX...",
    "must_interview": [
        {
            "name": "Alice",
            "team_name": "Team Awesome",
            "skills": ["Python", "FastAPI", "AWS"],
            "hiring_score": 95.0
        }
    ],
    "technology_trends": [
        {
            "technology": "Python",
            "category": "language",
            "usage_count": 120
        }
    ],
    "sponsor_api_usage": {
        "stripe": 45,
        "twilio": 30,
        "aws": 80
    }
}
```

### Form Input Structures

#### Hackathon Creation Form
```python
{
    "name": str,                    # Required, 1-200 chars
    "description": str,             # Required, 1-2000 chars
    "start_date": datetime,         # Required, ISO format
    "end_date": datetime,           # Required, > start_date
    "budget_limit_usd": float | None  # Optional, > 0 if provided
}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

After analyzing all 72 acceptance criteria, I identified the following areas of redundancy:

1. **Display Properties**: Many criteria specify that certain fields "SHALL display" specific data. These can be consolidated into properties that verify all required fields are present in rendered output.

2. **API Call Properties**: Multiple criteria specify that the dashboard "SHALL fetch" data from specific endpoints. These can be consolidated into properties that verify correct endpoint usage and parameter passing.

3. **Error Handling Properties**: Multiple edge cases specify error handling for different HTTP status codes. These can be consolidated into a single property that verifies error handling across all status codes.

4. **Caching Properties**: Requirements 11.2 and 11.3 both specify 30-second caching for different endpoints. These can be consolidated into a single property about cache TTL.

5. **Validation Properties**: Requirements 2.5 and 2.6 both specify form validation. These can be consolidated into a single property about form validation logic.

After reflection, I've consolidated 72 acceptance criteria into 27 unique properties that provide comprehensive coverage without redundancy.

### Property 1: API Key Header Inclusion

*For any* authenticated API request, the X-API-Key header should be present and contain the stored API key from session state.

**Validates: Requirements 1.5**

### Property 2: Session State Persistence

*For any* successful authentication (HTTP 200), the API key should be stored in st.session_state and persist across page navigations.

**Validates: Requirements 1.3**

### Property 3: Logout Clears State

*For any* session state with an API key, calling logout should clear the API key from session state.

**Validates: Requirements 1.6**

### Property 4: Form Submission Triggers POST

*For any* valid hackathon creation form data, submitting the form should trigger a POST request to /hackathons with the form data as JSON.

**Validates: Requirements 2.2**

### Property 5: Date Validation

*For any* pair of start_date and end_date, the form validation should reject submissions where end_date is not after start_date.

**Validates: Requirements 2.5**

### Property 6: Budget Validation

*For any* budget_limit_usd value, the form validation should reject negative numbers and accept positive numbers or empty values.

**Validates: Requirements 2.6**

### Property 7: Success Response Display

*For any* successful hackathon creation (HTTP 201), the dashboard should display the hack_id from the response.

**Validates: Requirements 2.3**

### Property 8: Dropdown Population

*For any* list of hackathons returned from GET /hackathons, the dropdown should contain all hackathon names as options.

**Validates: Requirements 3.1**

### Property 9: Selection Triggers Stats Fetch

*For any* hackathon selection from the dropdown, the dashboard should fetch statistics from GET /hackathons/{hack_id}/stats.

**Validates: Requirements 3.2**

### Property 10: Stats Display Completeness

*For any* stats response, the dashboard should display all four required fields: submission_count, verified_count, pending_count, and participant_count.

**Validates: Requirements 3.3**

### Property 11: Cache TTL Enforcement

*For any* cached GET request, repeated calls within 30 seconds should return the cached response without making a new API call.

**Validates: Requirements 3.6, 11.2, 11.3**

### Property 12: Analysis Trigger

*For any* hackathon with pending submissions, clicking "Start Analysis" should send a POST request to /hackathons/{hack_id}/analyze.

**Validates: Requirements 4.2**

### Property 13: Analysis Response Display

*For any* successful analysis start (HTTP 202), the dashboard should display both job_id and estimated_cost_usd from the response.

**Validates: Requirements 4.3**

### Property 14: Cost Estimate Display

*For any* hackathon, the dashboard should fetch and display a cost estimate from POST /hackathons/{hack_id}/estimate before allowing analysis to start.

**Validates: Requirements 4.6**

### Property 15: Progress Bar Rendering

*For any* progress_percent value between 0 and 100, the dashboard should render a progress bar with the correct percentage.

**Validates: Requirements 5.2**

### Property 16: Progress Fields Display

*For any* analysis job response, the dashboard should display completed_submissions, failed_submissions, and current_cost_usd.

**Validates: Requirements 5.3**

### Property 17: Failure Details Display

*For any* analysis job where failed_submissions > 0, the dashboard should display error details.

**Validates: Requirements 5.6**

### Property 18: Leaderboard Data Fetch

*For any* hackathon with analyzed submissions, the dashboard should fetch leaderboard data from GET /hackathons/{hack_id}/leaderboard.

**Validates: Requirements 6.1**

### Property 19: Leaderboard Row Completeness

*For any* submission in the leaderboard, the dashboard should display rank, team_name, overall_score, and recommendation.

**Validates: Requirements 6.2**

### Property 20: Search Filtering

*For any* search query and leaderboard data, the filtered results should only include submissions where team_name contains the search query (case-insensitive).

**Validates: Requirements 6.3**

### Property 21: Leaderboard Sorting

*For any* sort option (score, team_name, created_at) and leaderboard data, the sorted results should be correctly ordered by the selected field.

**Validates: Requirements 6.4**

### Property 22: Pagination Limit

*For any* leaderboard with more than 50 submissions, the dashboard should display at most 50 submissions per page.

**Validates: Requirements 11.6**

### Property 23: Scorecard Data Completeness

*For any* scorecard response, the dashboard should display all required sections: overall_score, confidence, recommendation, dimension_scores, agent_results, repo_meta, and cost breakdown.

**Validates: Requirements 7.2, 7.3, 7.4, 7.5, 7.6**

### Property 24: Individual Scorecard Completeness

*For any* individual scorecard response, the dashboard should display team_dynamics, strategy_analysis, and all contributor details (member_name, commit_count, skill_assessment, actionable_feedback).

**Validates: Requirements 8.2, 8.3, 8.4, 8.5**

### Property 25: Intelligence Data Completeness

*For any* intelligence response, the dashboard should display must_interview candidates, technology_trends with Plotly chart, and sponsor_api_usage statistics.

**Validates: Requirements 9.2, 9.3, 9.4, 9.5**

### Property 26: Error Logging

*For any* API error (4xx or 5xx status code), the dashboard should log the error details to the console.

**Validates: Requirements 10.5**

### Property 27: Retry Button Availability

*For any* failed API request, the dashboard should display a retry button that re-attempts the request.

**Validates: Requirements 10.6**

## Error Handling

### Error Handling Strategy

The dashboard implements a three-layer error handling strategy:

1. **API Client Layer**: Catches HTTP errors and network exceptions, maps to user-friendly messages
2. **Component Layer**: Validates data before rendering, handles missing or malformed data
3. **UI Layer**: Displays errors using Streamlit's st.error, st.warning, and st.info

### HTTP Error Mapping

```python
ERROR_MESSAGES = {
    400: "Bad request. Please check your input.",
    401: "Invalid API key. Please log in again.",
    402: "Budget limit exceeded. Increase your budget or reduce scope.",
    404: "Resource not found.",
    409: "Conflict: {detail}",  # e.g., "Analysis already running"
    422: "Validation error: {detail}",
    429: "Rate limit exceeded. Please wait and try again.",
    500: "Server error. Please try again later.",
    503: "Service unavailable. Please try again later.",
}
```

### Network Error Handling

```python
try:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()
except requests.Timeout:
    st.error("Connection timeout. Please check your network.")
    return None
except requests.ConnectionError:
    st.error("Cannot connect to server. Please check the API URL.")
    return None
except requests.HTTPError as e:
    handle_http_error(e.response)
    return None
```

### Data Validation

```python
def validate_scorecard(data: dict) -> bool:
    """Validate scorecard response has required fields."""
    required_fields = [
        "overall_score", "confidence", "recommendation",
        "dimension_scores", "agent_results", "repo_meta"
    ]
    return all(field in data for field in required_fields)

def safe_render_scorecard(data: dict) -> None:
    """Render scorecard with fallbacks for missing data."""
    if not validate_scorecard(data):
        st.warning("Scorecard data is incomplete. Some sections may be missing.")

    st.metric("Overall Score", data.get("overall_score", "N/A"))
    st.metric("Confidence", data.get("confidence", "N/A"))
    # ... render other fields with .get() fallbacks
```

### Retry Mechanism

```python
def retry_button(func: callable, *args, **kwargs) -> None:
    """Display retry button for failed operations."""
    if st.button("🔄 Retry"):
        with st.spinner("Retrying..."):
            result = func(*args, **kwargs)
            if result:
                st.success("Success!")
                st.rerun()
```

### Edge Case Handling

1. **Empty Data**: Display "No data available" messages instead of empty tables
2. **Missing Fields**: Use `.get()` with defaults instead of direct key access
3. **Invalid Dates**: Catch parsing errors and display raw strings
4. **Large Numbers**: Format with abbreviations (1.5K, 2.3M)
5. **Long Strings**: Truncate with ellipsis and show full text in expander

## Testing Strategy

### Testing Approach

The Streamlit dashboard requires a dual testing approach:

1. **Unit Tests**: Test individual components (API client, formatters, validators) in isolation
2. **Property Tests**: Verify universal properties across randomized inputs

### Unit Testing

Unit tests focus on:
- API client error handling for specific HTTP status codes
- Data formatting functions (currency, timestamps, percentages)
- Form validation logic (date ranges, budget values)
- Cache behavior with mocked time
- Authentication state management

Example unit tests:

```python
def test_api_client_handles_401():
    """Test that 401 returns appropriate error message."""
    client = APIClient("http://test", "invalid_key")
    with pytest.raises(AuthenticationError, match="Invalid API key"):
        client.get("/hackathons")

def test_format_currency():
    """Test currency formatting."""
    assert format_currency(1.5) == "$1.50"
    assert format_currency(1000.0) == "$1,000.00"

def test_date_validation_rejects_invalid_range():
    """Test that end_date before start_date is rejected."""
    start = datetime(2025, 3, 3)
    end = datetime(2025, 3, 1)
    assert not validate_date_range(start, end)
```

### Property-Based Testing

Property tests verify universal behaviors across randomized inputs using Hypothesis (Python property-based testing library).

Configuration:
- **Library**: Hypothesis 6.92+
- **Iterations**: 100 per property test
- **Tag Format**: `# Feature: streamlit-organizer-dashboard, Property {N}: {description}`

Example property tests:

```python
from hypothesis import given, strategies as st

@given(st.text(min_size=1), st.lists(st.dictionaries(...)))
def test_search_filtering_property(query: str, leaderboard: list[dict]):
    """
    Feature: streamlit-organizer-dashboard, Property 20: Search Filtering

    For any search query and leaderboard data, filtered results should only
    include submissions where team_name contains the query (case-insensitive).
    """
    filtered = filter_leaderboard(leaderboard, query)
    for submission in filtered:
        assert query.lower() in submission["team_name"].lower()

@given(st.floats(min_value=0, max_value=100))
def test_progress_bar_rendering_property(progress: float):
    """
    Feature: streamlit-organizer-dashboard, Property 15: Progress Bar Rendering

    For any progress_percent value between 0 and 100, the dashboard should
    render a progress bar with the correct percentage.
    """
    # Mock Streamlit progress bar
    with patch("streamlit.progress") as mock_progress:
        render_progress_bar(progress)
        mock_progress.assert_called_once_with(progress / 100.0)

@given(st.datetimes(), st.datetimes())
def test_date_validation_property(start: datetime, end: datetime):
    """
    Feature: streamlit-organizer-dashboard, Property 5: Date Validation

    For any pair of start_date and end_date, validation should reject
    submissions where end_date is not after start_date.
    """
    is_valid = validate_date_range(start, end)
    if end > start:
        assert is_valid
    else:
        assert not is_valid
```

### Integration Testing

Integration tests verify page-level behavior using Streamlit's testing framework:

```python
from streamlit.testing.v1 import AppTest

def test_authentication_page():
    """Test authentication page flow."""
    at = AppTest.from_file("app.py")
    at.run()

    # Check form is displayed
    assert len(at.text_input) == 1  # API key input
    assert len(at.button) == 1      # Login button

    # Enter API key and submit
    at.text_input[0].set_value("test_key_123")
    at.button[0].click()
    at.run()

    # Check authentication succeeded
    assert at.session_state["api_key"] == "test_key_123"  # pragma: allowlist secret

def test_leaderboard_pagination():
    """Test leaderboard pagination with >50 submissions."""
    # Mock API response with 100 submissions
    with patch("components.api_client.APIClient.get") as mock_get:
        mock_get.return_value = {
            "submissions": [{"rank": i} for i in range(100)]
        }

        at = AppTest.from_file("pages/3_🏆_Results.py")
        at.run()

        # Check only 50 displayed
        assert len(at.dataframe[0].value) == 50
```

### Test Coverage Goals

- **Unit Tests**: 90%+ coverage of components/ modules
- **Property Tests**: All 27 properties implemented
- **Integration Tests**: All 5 pages tested for happy path
- **Edge Cases**: All error handling paths tested

### Testing Tools

```
# requirements-dev.txt
pytest>=7.4.0
pytest-cov>=4.1.0
hypothesis>=6.92.0
pytest-mock>=3.12.0
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=streamlit_ui --cov-report=html

# Run only property tests
pytest -m property

# Run only unit tests
pytest -m unit
```
