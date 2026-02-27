# Streamlit Organizer Dashboard

A web-based interface for hackathon organizers to manage events, monitor submissions, trigger AI analysis, and view results through the VibeJudge AI platform.

## Overview

The Streamlit Organizer Dashboard provides a visual interface to the VibeJudge FastAPI backend, enabling organizers to:

- **Authenticate** with API keys for secure access
- **Create hackathons** with custom configurations and budgets
- **Monitor submissions** in real-time with auto-refresh
- **Trigger AI analysis** with cost estimates and progress tracking
- **View results** with leaderboards, search, and detailed scorecards
- **Access intelligence** including hiring insights and technology trends

## Quick Start

### Prerequisites

- Python 3.12+
- VibeJudge FastAPI backend running OR access to production deployment
- No API key needed - register directly through the dashboard!

### Installation

```bash
# Navigate to the dashboard directory
cd streamlit_ui

# Install dependencies
pip install -r requirements.txt

# (Optional) Set API URL if not using default
# For local development
export API_BASE_URL=http://localhost:8000

# For production backend
export API_BASE_URL=https://2nu0j4n648.execute-api.us-east-1.amazonaws.com/dev

# Run the dashboard
streamlit run app.py
```

The dashboard will open in your browser at http://localhost:8501

### First-Time Setup

1. **Register**: Click "Create an account" on the homepage or go to the Register page
2. **Save your API key**: Your API key will be displayed once after registration - save it!
3. **Login**: Use your API key or email/password to authenticate
4. **Create a hackathon**: Navigate to "Create Hackathon" and fill out the form
5. **Monitor submissions**: Use the "Live Dashboard" to track submissions in real-time
6. **Trigger analysis**: Click "Start Analysis" when ready to evaluate submissions
7. **View results**: Check the "Results" page for leaderboards and detailed scorecards

## Architecture

### High-Level Design

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
                   │  (VibeJudge API)  │
                   └───────────────────┘
```

### URL Construction Standard

The dashboard uses the following URL pattern:

**Base URL:**
- Local: `http://localhost:8000`
- Production: `https://2nu0j4n648.execute-api.us-east-1.amazonaws.com/dev`

**Endpoint Paths:**
- Registration: `/organizers`
- Login: `/organizers/login`
- Profile: `/organizers/me`
- API Keys: `/api-keys`
- Hackathons: `/hackathons`
- Submissions: `/submissions`
- Public endpoints: `/public/hackathons`

**Note:** Auth validation uses `/api/v1/hackathons` for backwards compatibility.

**Base URL does NOT include `/api/v1` prefix** - endpoints are added directly to the base URL.

### Directory Structure

```
streamlit_ui/
├── app.py                      # Entry point + authentication page
├── .streamlit/
│   └── config.toml             # Streamlit configuration
├── components/
│   ├── api_client.py           # HTTP client with error handling
│   ├── auth.py                 # Authentication helpers
│   ├── charts.py               # Plotly chart generators
│   ├── formatters.py           # Data formatting utilities
│   ├── validators.py           # Form validation logic
│   ├── retry_helpers.py        # Retry button helpers
│   └── safe_render.py          # Safe data rendering with fallbacks
├── pages/
│   ├── 1_🎯_Create_Hackathon.py
│   ├── 2_📊_Live_Dashboard.py
│   ├── 3_🏆_Results.py
│   └── 4_💡_Intelligence.py
├── tests/
│   ├── conftest.py             # Shared test fixtures
│   ├── test_*.py               # Unit tests
│   ├── test_*_properties.py    # Property-based tests
│   └── test_*_integration.py   # Integration tests
├── requirements.txt            # Production dependencies
├── requirements-dev.txt        # Development dependencies
├── .env.example                # Environment variable template
└── README.md                   # This file
```

### Pages

#### 1. Authentication (app.py)
- API key login form
- Session state management
- Logout functionality
- API URL configuration

#### 2. Create Hackathon (1_🎯_Create_Hackathon.py)
- Hackathon creation form
- Date range validation
- Budget limit configuration
- Success/error handling

#### 3. Live Dashboard (2_📊_Live_Dashboard.py)
- Hackathon selection dropdown
- Real-time submission statistics
- Auto-refresh every 5 seconds
- Analysis triggering with cost estimates
- Progress monitoring with live updates

#### 4. Results (3_🏆_Results.py)
- Leaderboard with rankings
- Search and sort functionality
- Pagination (50 submissions per page)
- Team detail scorecards
- Individual contributor analysis
- Dimension scores and agent results

#### 5. Intelligence (4_💡_Intelligence.py)
- Must-interview candidates
- Technology trends with charts
- Sponsor API usage statistics
- Hiring insights

### Components

#### API Client (`components/api_client.py`)
- Centralized HTTP client
- Automatic X-API-Key header injection
- Error handling with user-friendly messages
- Timeout configuration (10 seconds)
- Retry logic for transient failures

#### Authentication (`components/auth.py`)
- API key validation
- Session state management
- Authentication checks
- Logout functionality

#### Charts (`components/charts.py`)
- Plotly chart generators
- Progress bar rendering
- Technology trends visualization
- Responsive chart layouts

#### Formatters (`components/formatters.py`)
- Currency formatting ($X.XX)
- Timestamp formatting (ISO to human-readable)
- Percentage formatting (X.X%)
- Number abbreviations (1.5K, 2.3M)

#### Validators (`components/validators.py`)
- Date range validation
- Budget validation
- Form input validation
- Data completeness checks

### State Management

All application state is stored in `st.session_state`:

```python
st.session_state = {
    "api_key": str,              # Authenticated API key
    "api_base_url": str,         # Backend URL
    "selected_hackathon": str,   # Currently selected hack_id
    "analysis_job_id": str,      # Active analysis job ID
    "last_refresh": datetime,    # Last auto-refresh timestamp
}
```

## Live Deployment

### Production Endpoints

**Backend API:**
https://2nu0j4n648.execute-api.us-east-1.amazonaws.com/dev

**Frontend Dashboard:**
http://vibejudge-alb-prod-1135403146.us-east-1.elb.amazonaws.com

### Environment Configuration

Set the `API_BASE_URL` environment variable to point to the backend:

```bash
# Docker deployment
docker run -e API_BASE_URL=https://2nu0j4n648.execute-api.us-east-1.amazonaws.com/dev vibejudge-dashboard

# ECS task definition
{
  "name": "API_BASE_URL",
  "value": "https://2nu0j4n648.execute-api.us-east-1.amazonaws.com/dev"
}
```

### Caching Strategy

The dashboard uses Streamlit's `@st.cache_data` decorator with 30-second TTL to minimize backend load:

```python
@st.cache_data(ttl=30)
def fetch_hackathons(api_key: str) -> list[dict]:
    return api_client.get("/hackathons")
```

Cache invalidation occurs:
- Automatically after 30 seconds (TTL expiration)
- Manually via `st.cache_data.clear()` after mutations (POST, PUT, DELETE)

## Configuration

### Environment Variables

Create a `.env` file in the `streamlit_ui/` directory:

```bash
# API Base URL (required)
API_BASE_URL=http://localhost:8000

# For production deployment:
# API_BASE_URL=https://api.vibejudge.com
```

Alternatively, configure the API URL via the Streamlit UI (Advanced Settings in login form).

### Streamlit Configuration

The `.streamlit/config.toml` file contains Streamlit-specific settings:

```toml
[theme]
primaryColor = "#FF6B6B"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
font = "sans serif"

[server]
headless = true
port = 8501
enableCORS = false
enableXsrfProtection = true
```

## Usage Guide

### Authentication

1. Open the dashboard at http://localhost:8501
2. Enter your API key in the login form
3. (Optional) Configure a custom API URL in Advanced Settings
4. Click "Login"
5. Upon success, you'll be redirected to the Create Hackathon page

### Creating a Hackathon

1. Navigate to "Create Hackathon" (🎯)
2. Fill out the form:
   - **Name**: Hackathon name (1-200 characters)
   - **Description**: Event description (1-2000 characters)
   - **Start Date**: Event start date and time
   - **End Date**: Event end date and time (must be after start date)
   - **Budget Limit**: Optional cost limit in USD (must be positive)
3. Click "Create Hackathon"
4. On success, the hackathon ID will be displayed

### Monitoring Submissions

1. Navigate to "Live Dashboard" (📊)
2. Select a hackathon from the dropdown
3. View real-time statistics:
   - Total submissions
   - Verified submissions
   - Pending submissions
   - Participant count
4. The dashboard auto-refreshes every 5 seconds

### Triggering Analysis

1. On the Live Dashboard, click "Estimate Cost"
2. Review the estimated cost
3. Click "Start Analysis" to confirm
4. Monitor progress in real-time:
   - Progress bar
   - Completed/failed submissions
   - Current cost
   - Estimated completion time
5. Wait for analysis to complete (status: "completed")

### Viewing Results

1. Navigate to "Results" (🏆)
2. Select a hackathon from the dropdown
3. Use the search bar to filter by team name
4. Use the sort dropdown to order by score, name, or date
5. Click a team row to view detailed scorecard:
   - Overall score and confidence
   - Dimension scores (code quality, innovation, performance, authenticity)
   - Agent results (summary, strengths, improvements)
   - Repository metadata
   - Cost breakdown
6. View individual contributor analysis:
   - Team dynamics
   - Strategy analysis
   - Member-specific feedback

### Accessing Intelligence

1. Navigate to "Intelligence" (💡)
2. Select a hackathon from the dropdown
3. View insights:
   - Must-interview candidates with hiring scores
   - Technology trends with interactive charts
   - Sponsor API usage statistics

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=streamlit_ui --cov-report=html

# Run only unit tests
pytest tests/test_api_client.py tests/test_formatters.py tests/test_auth.py

# Run only property-based tests
pytest tests/test_*_properties.py

# Run only integration tests
pytest tests/test_*_integration.py

# Run specific test file
pytest tests/test_formatters.py -v

# Run specific test function
pytest tests/test_auth_properties.py::TestSessionStatePersistenceProperty -v
```

### Test Coverage

The dashboard has comprehensive test coverage:

- **27 property-based tests** validating universal correctness properties
- **Unit tests** for all components (API client, formatters, validators, charts)
- **Integration tests** for all 5 pages
- **90%+ code coverage** for components/

### Property-Based Testing

The dashboard uses Hypothesis for property-based testing, which validates universal properties across randomized inputs:

```python
@given(st.floats(min_value=0, max_value=100))
def test_progress_bar_rendering_property(progress: float):
    """Property 15: Progress Bar Rendering"""
    with patch("streamlit.progress") as mock_progress:
        render_progress_bar(progress)
        mock_progress.assert_called_once_with(progress / 100.0)
```

Each property test runs 100 iterations with randomized inputs to ensure correctness.

### Test Files

- `test_api_client.py` - API client error handling
- `test_formatters.py` - Data formatting functions
- `test_auth.py` - Authentication helpers
- `test_*_properties.py` - Property-based tests (27 properties)
- `test_*_integration.py` - End-to-end page tests

## Deployment

### Local Deployment

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export API_BASE_URL=http://localhost:8000

# Run dashboard
streamlit run app.py
```

### Streamlit Cloud Deployment

1. **Push to GitHub**: Ensure your code is in a GitHub repository

2. **Create Streamlit Cloud Account**: Sign up at https://streamlit.io/cloud

3. **Deploy App**:
   - Click "New app"
   - Select your repository
   - Set main file path: `streamlit_ui/app.py`
   - Configure secrets (see below)
   - Click "Deploy"

4. **Configure Secrets**: In Streamlit Cloud settings, add:
   ```toml
   # .streamlit/secrets.toml
   API_BASE_URL = "https://api.vibejudge.com"
   ```

5. **Access Dashboard**: Your app will be available at `https://your-app.streamlit.app`

### Docker Deployment

Create a `Dockerfile` in the `streamlit_ui/` directory:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

Build and run:

```bash
# Build image
docker build -t vibejudge-dashboard .

# Run container
docker run -p 8501:8501 -e API_BASE_URL=http://localhost:8000 vibejudge-dashboard
```

### Production Considerations

1. **HTTPS**: Always use HTTPS for production deployments
2. **API Keys**: Store API keys securely (environment variables, secrets management)
3. **CORS**: Configure backend CORS settings to allow dashboard origin
4. **Rate Limiting**: Implement rate limiting on the backend to prevent abuse
5. **Monitoring**: Set up logging and monitoring for production issues
6. **Caching**: Adjust cache TTL based on your use case (default: 30 seconds)

## Development

### Technology Stack

- **Framework**: Streamlit 1.30+
- **HTTP Client**: requests 2.31+
- **Charts**: plotly 5.18+
- **Auto-Refresh**: streamlit-autorefresh 1.0+
- **Date Handling**: python-dateutil 2.8+
- **Python**: 3.12

### Coding Standards

The dashboard follows VibeJudge coding standards:

- **Type hints required** for all functions
- **Comprehensive docstrings** for all modules, classes, and functions
- **Error handling** at 3 layers (API client, component, UI)
- **Structured logging** with context
- **30-second caching** for GET requests
- **No circular imports** (enforced with mypy)
- **Absolute imports only** (no relative imports)

### Adding a New Page

1. Create a new file in `pages/` with format: `N_Emoji_PageName.py`
2. Add authentication check at the top:
   ```python
   import streamlit as st
   from components.auth import is_authenticated

   st.set_page_config(page_title="Page Name", page_icon="🎯")

   if not is_authenticated():
       st.error("Please authenticate first")
       st.stop()
   ```
3. Implement page logic using components
4. Add tests in `tests/test_pagename_integration.py`

### Adding a New Component

1. Create a new file in `components/` with descriptive name
2. Add type hints and docstrings
3. Implement error handling
4. Add unit tests in `tests/test_componentname.py`
5. Add property tests in `tests/test_componentname_properties.py`

## Troubleshooting

### Common Issues

#### "Cannot connect to server"
- Ensure the FastAPI backend is running
- Check the API_BASE_URL is correct
- Verify network connectivity

#### "Invalid API key"
- Verify your API key is correct
- Check if the API key has expired
- Ensure the backend is configured to accept your API key

#### "Rate limit exceeded"
- Wait a few seconds and try again
- Reduce auto-refresh frequency
- Contact your administrator to increase rate limits

#### "Budget limit exceeded"
- Increase your hackathon budget limit
- Reduce the number of submissions
- Contact your administrator for budget increase

#### "Analysis already running"
- Wait for the current analysis to complete
- Check the Live Dashboard for progress
- If stuck, contact your administrator

### Debug Mode

Enable debug logging:

```bash
# Set log level to DEBUG
export STREAMLIT_LOG_LEVEL=debug

# Run dashboard
streamlit run app.py
```

### Getting Help

- **Documentation**: See `.kiro/specs/streamlit-organizer-dashboard/` for detailed specs
- **Issues**: Report bugs on GitHub
- **Support**: Contact your VibeJudge administrator

## Contributing

### Development Setup

```bash
# Clone repository
git clone https://github.com/your-org/vibejudge.git
cd vibejudge/streamlit_ui

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
pytest

# Run dashboard
streamlit run app.py
```

### Running Tests Before Commit

```bash
# Run all tests with coverage
pytest --cov=streamlit_ui --cov-report=html

# Check coverage report
open htmlcov/index.html  # On macOS
# Or: xdg-open htmlcov/index.html  # On Linux
# Or: start htmlcov/index.html  # On Windows
```

### Code Quality

```bash
# Format code
black streamlit_ui/

# Lint code
ruff check streamlit_ui/

# Type check
mypy streamlit_ui/
```

## License

Copyright © 2025 VibeJudge AI. All rights reserved.

## Documentation

For detailed specifications, see:
- `.kiro/specs/streamlit-organizer-dashboard/requirements.md` - 12 requirements with 72 acceptance criteria
- `.kiro/specs/streamlit-organizer-dashboard/design.md` - Architecture and design decisions
- `.kiro/specs/streamlit-organizer-dashboard/tasks.md` - Implementation plan
