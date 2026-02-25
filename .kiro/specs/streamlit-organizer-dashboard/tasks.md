# Implementation Plan: Streamlit Organizer Dashboard

## Overview

This implementation plan converts the Streamlit Organizer Dashboard design into discrete coding tasks. The dashboard is a Python-based web application built with Streamlit 1.30+ that provides hackathon organizers with a visual interface to manage events through the existing VibeJudge FastAPI backend.

The implementation follows a bottom-up approach: first building reusable components (API client, authentication, charts, formatters), then implementing the five pages (authentication, hackathon creation, live monitoring, results, intelligence), and finally adding comprehensive testing.

## Tasks

- [x] 1. Set up project structure and dependencies
  - Create streamlit_ui/ directory with subdirectories (components/, pages/, .streamlit/, tests/)
  - Create requirements.txt with Streamlit 1.30+, requests 2.31+, plotly 5.18+, streamlit-autorefresh 1.0+, python-dateutil 2.8+
  - Create requirements-dev.txt with pytest, pytest-cov, hypothesis, pytest-mock
  - Create .streamlit/config.toml with theme and server configuration
  - Create __init__.py files in components/ and tests/ directories
  - _Requirements: 11.1, 12.1_

- [x] 2. Implement API client component
  - [x] 2.1 Create APIClient class with HTTP methods
    - Write APIClient class in components/api_client.py with __init__, get(), post() methods
    - Implement requests.Session with X-API-Key header injection
    - Add timeout configuration (10 seconds default)
    - _Requirements: 1.5, 10.3_

  - [x] 2.2 Implement error handling and mapping
    - Write handle_error() method that maps HTTP status codes to user-friendly messages
    - Handle 400, 401, 402, 404, 409, 422, 429, 500, 503 status codes
    - Raise custom exceptions (AuthenticationError, ValidationError, etc.)
    - _Requirements: 10.1, 10.2, 10.4_

  - [x] 2.3 Add network error handling
    - Catch requests.Timeout and raise ConnectionTimeoutError
    - Catch requests.ConnectionError and raise ServiceUnavailableError
    - Add logging for all errors using Python logging module
    - _Requirements: 10.3, 10.5_

  - [x] 2.4 Write unit tests for API client
    - Test error handling for each HTTP status code
    - Test network timeout and connection errors
    - Test X-API-Key header inclusion
    - Mock requests.Session for isolated testing
    - _Requirements: 1.5, 10.1, 10.2, 10.3, 10.4_

- [x] 3. Implement authentication component
  - [x] 3.1 Create authentication helper functions
    - Write validate_api_key() function in components/auth.py
    - Write is_authenticated() function that checks st.session_state
    - Write logout() function that clears st.session_state
    - _Requirements: 1.2, 1.3, 1.6_

  - [x] 3.2 Write property test for session state persistence
    - **Property 2: Session State Persistence**
    - **Validates: Requirements 1.3**
    - Test that successful authentication stores API key in session state
    - _Requirements: 1.3_

  - [x] 3.3 Write property test for logout behavior
    - **Property 3: Logout Clears State**
    - **Validates: Requirements 1.6**
    - Test that logout clears API key from session state
    - _Requirements: 1.6_

- [x] 4. Implement formatters component
  - [x] 4.1 Create data formatting utilities
    - Write format_currency() function in components/formatters.py
    - Write format_timestamp() function for ISO datetime conversion
    - Write format_percentage() function
    - _Requirements: 7.6, 9.2_

  - [x] 4.2 Write unit tests for formatters
    - Test currency formatting with various amounts
    - Test timestamp formatting with ISO strings
    - Test percentage formatting with edge cases
    - _Requirements: 7.6, 9.2_

- [x] 5. Implement charts component
  - [x] 5.1 Create Plotly chart generators
    - Write create_technology_trends_chart() function in components/charts.py
    - Write create_progress_bar() function using st.progress
    - Configure Plotly layout with titles, axis labels, and colors
    - _Requirements: 5.2, 9.4_

  - [x] 5.2 Write property test for progress bar rendering
    - **Property 15: Progress Bar Rendering**
    - **Validates: Requirements 5.2**
    - Test that progress bar renders correctly for values 0-100
    - _Requirements: 5.2_

- [x] 6. Implement authentication page (app.py)
  - [x] 6.1 Create main entry point with authentication form
    - Write app.py with st.set_page_config
    - Create API key text input and login button
    - Add API base URL configuration (env var or default)
    - _Requirements: 1.1_

  - [x] 6.2 Implement authentication flow
    - Call validate_api_key() on form submission
    - Store API key in st.session_state on success (HTTP 200)
    - Display error message on failure (HTTP 401)
    - Add logout button in sidebar when authenticated
    - _Requirements: 1.2, 1.3, 1.4, 1.6_

  - [x] 6.3 Write property test for API key header inclusion
    - **Property 1: API Key Header Inclusion**
    - **Validates: Requirements 1.5**
    - Test that all authenticated requests include X-API-Key header
    - _Requirements: 1.5_

- [x] 7. Checkpoint - Ensure authentication works
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Implement hackathon creation page
  - [x] 8.1 Create hackathon creation form
    - Write pages/1_🎯_Create_Hackathon.py with authentication check
    - Create form with name, description, start_date, end_date, budget_limit_usd inputs
    - Add form validation for date range and budget
    - _Requirements: 2.1, 2.5, 2.6_

  - [x] 8.2 Implement form submission and response handling
    - Send POST request to /hackathons on form submit
    - Display hack_id on success (HTTP 201)
    - Display validation errors inline on failure (HTTP 422)
    - Clear cache after successful creation
    - _Requirements: 2.2, 2.3, 2.4_

  - [x] 8.3 Write property test for form submission
    - **Property 4: Form Submission Triggers POST**
    - **Validates: Requirements 2.2**
    - Test that valid form data triggers POST to /hackathons
    - _Requirements: 2.2_

  - [x] 8.4 Write property test for date validation
    - **Property 5: Date Validation**
    - **Validates: Requirements 2.5**
    - Test that end_date must be after start_date
    - _Requirements: 2.5_

  - [x] 8.5 Write property test for budget validation
    - **Property 6: Budget Validation**
    - **Validates: Requirements 2.6**
    - Test that budget must be positive or empty
    - _Requirements: 2.6_

- [x] 9. Implement live dashboard page
  - [x] 9.1 Create hackathon selection and stats display
    - Write pages/2_📊_Live_Dashboard.py with authentication check
    - Create hackathon dropdown populated from GET /hackathons
    - Fetch and display stats (submission_count, verified_count, pending_count, participant_count)
    - Add @st.cache_data decorator with 30-second TTL
    - _Requirements: 3.1, 3.2, 3.3, 3.6, 11.2_

  - [x] 9.2 Implement auto-refresh for live monitoring
    - Add streamlit-autorefresh with 5-second interval
    - Display last refresh timestamp
    - Add manual refresh button
    - _Requirements: 3.4_

  - [x] 9.3 Implement analysis triggering
    - Add "Start Analysis" button
    - Fetch cost estimate from POST /hackathons/{hack_id}/estimate
    - Display cost estimate and confirmation dialog
    - Send POST to /hackathons/{hack_id}/analyze on confirmation
    - Display job_id and estimated_cost_usd on success (HTTP 202)
    - Handle budget exceeded (HTTP 402) and conflict (HTTP 409) errors
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [x] 9.4 Implement analysis progress monitoring
    - Poll GET /hackathons/{hack_id}/jobs/{job_id} every 5 seconds when analysis is running
    - Display progress bar with progress_percent
    - Display completed_submissions, failed_submissions, current_cost_usd
    - Display estimated_completion timestamp
    - Stop polling when status is "completed"
    - Display error details when failed_submissions > 0
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

  - [x] 9.5 Write property test for dropdown population
    - **Property 8: Dropdown Population**
    - **Validates: Requirements 3.1**
    - Test that dropdown contains all hackathon names from API
    - _Requirements: 3.1_

  - [x] 9.6 Write property test for cache TTL
    - **Property 11: Cache TTL Enforcement**
    - **Validates: Requirements 3.6, 11.2, 11.3**
    - Test that repeated calls within 30 seconds use cached response
    - _Requirements: 3.6, 11.2, 11.3_

- [x] 10. Checkpoint - Ensure live dashboard works
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Implement results page
  - [x] 11.1 Create leaderboard display
    - Write pages/3_🏆_Results.py with authentication check
    - Fetch leaderboard from GET /hackathons/{hack_id}/leaderboard
    - Display total_submissions and analyzed_count
    - Display table with rank, team_name, overall_score, recommendation
    - Add @st.cache_data decorator with 30-second TTL
    - _Requirements: 6.1, 6.2, 11.3_

  - [x] 11.2 Implement search and sort functionality
    - Add search input for filtering by team_name (case-insensitive)
    - Add sort dropdown with options: score, team_name, created_at
    - Implement client-side filtering and sorting
    - _Requirements: 6.3, 6.4_

  - [x] 11.3 Implement pagination
    - Limit display to 50 submissions per page
    - Add page navigation controls (previous, next, page number)
    - _Requirements: 11.6_

  - [x] 11.4 Implement team detail navigation
    - Make team rows clickable
    - Store selected sub_id in st.session_state
    - Navigate to team detail view on click
    - _Requirements: 6.5_

  - [x] 11.5 Create team detail scorecard view
    - Fetch scorecard from GET /hackathons/{hack_id}/submissions/{sub_id}/scorecard
    - Display overall_score, confidence, recommendation
    - Display dimension_scores table with raw, weighted, and weight columns
    - Display agent_results in expandable sections (summary, strengths, improvements, cost)
    - Display repo_meta (primary_language, commit_count, contributor_count, has_tests, has_ci)
    - Display total cost breakdown by agent
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [x] 11.6 Create individual team member scorecard view
    - Fetch individual scorecards from GET /hackathons/{hack_id}/submissions/{sub_id}/individual-scorecards
    - Display team_dynamics (collaboration_quality, role_distribution, communication_patterns)
    - Display strategy_analysis (development_approach, time_management, risk_management)
    - Display contributors table with member_name, commit_count, skill_assessment
    - Display actionable_feedback for each contributor
    - Handle unavailable data with pending message
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

  - [x] 11.7 Write property test for search filtering
    - **Property 20: Search Filtering**
    - **Validates: Requirements 6.3**
    - Test that filtered results only include matching team names
    - _Requirements: 6.3_

  - [x] 11.8 Write property test for leaderboard sorting
    - **Property 21: Leaderboard Sorting**
    - **Validates: Requirements 6.4**
    - Test that sorting works correctly for all sort options
    - _Requirements: 6.4_`z

  - [x] 11.9 Write property test for pagination limit
    - **Property 22: Pagination Limit**
    - **Validates: Requirements 11.6**
    - Test that at most 50 submissions are displayed per page
    - _Requirements: 11.6_

  - [x] 11.10 Write property test for scorecard completeness
    - **Property 23: Scorecard Data Completeness**
    - **Validates: Requirements 7.2, 7.3, 7.4, 7.5, 7.6**
    - Test that all required scorecard sections are displayed
    - _Requirements: 7.2, 7.3, 7.4, 7.5, 7.6_

- [x] 12. Implement intelligence page
  - [x] 12.1 Create intelligence insights display
    - Write pages/4_💡_Intelligence.py with authentication check
    - Fetch intelligence from GET /hackathons/{hack_id}/intelligence
    - Display must_interview candidates table (name, team_name, skills, hiring_score)
    - Display technology_trends with Plotly bar chart
    - Display sponsor_api_usage statistics
    - Handle unavailable data with pending message
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

  - [x] 12.2 Write property test for intelligence completeness
    - **Property 25: Intelligence Data Completeness**
    - **Validates: Requirements 9.2, 9.3, 9.4, 9.5**
    - Test that all intelligence sections are displayed
    - _Requirements: 9.2, 9.3, 9.4, 9.5_

- [x] 13. Checkpoint - Ensure all pages work
  - Ensure all tests pass, ask the user if questions arise.

- [x] 14. Implement error handling and UI polish
  - [x] 14.1 Add loading spinners
    - Add st.spinner for API requests longer than 500ms
    - Display loading messages during data fetching
    - _Requirements: 11.5_

  - [x] 14.2 Add retry buttons for failed requests
    - Create retry_button() helper function
    - Add retry buttons after error messages
    - _Requirements: 10.6_

  - [x] 14.3 Implement responsive UI components
    - Use st.columns for multi-column layouts
    - Use st.expander for collapsible sections
    - Use st.tabs for organizing related content
    - Use st.success, st.error, st.warning for messages
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6_

  - [x] 14.4 Add data validation and safe rendering
    - Write validate_scorecard() function
    - Write safe_render_scorecard() with fallbacks for missing data
    - Use .get() with defaults for all dictionary access
    - Display "No data available" for empty responses
    - _Requirements: 7.1, 8.6, 9.6_

  - [x] 14.5 Write property test for error logging
    - **Property 26: Error Logging**
    - **Validates: Requirements 10.5**
    - Test that all API errors are logged to console
    - _Requirements: 10.5_

  - [x] 14.6 Write property test for retry button
    - **Property 27: Retry Button Availability**
    - **Validates: Requirements 10.6**
    - Test that retry button appears after failed requests
    - _Requirements: 10.6_

- [ ] 15. Implement remaining property-based tests
  - [x] 15.1 Write property test for selection triggers stats fetch
    - **Property 9: Selection Triggers Stats Fetch**
    - **Validates: Requirements 3.2**
    - Test that selecting a hackathon fetches stats
    - _Requirements: 3.2_

  - [x] 15.2 Write property test for stats display completeness
    - **Property 10: Stats Display Completeness**
    - **Validates: Requirements 3.3**
    - Test that all four stats fields are displayed
    - _Requirements: 3.3_

  - [x] 15.3 Write property test for analysis trigger
    - **Property 12: Analysis Trigger**
    - **Validates: Requirements 4.2**
    - Test that clicking Start Analysis sends POST request
    - _Requirements: 4.2_

  - [x] 15.4 Write property test for analysis response display
    - **Property 13: Analysis Response Display**
    - **Validates: Requirements 4.3**
    - Test that job_id and estimated_cost_usd are displayed
    - _Requirements: 4.3_

  - [x] 15.5 Write property test for cost estimate display
    - **Property 14: Cost Estimate Display**
    - **Validates: Requirements 4.6**
    - Test that cost estimate is fetched and displayed
    - _Requirements: 4.6_

  - [x] 15.6 Write property test for progress fields display
    - **Property 16: Progress Fields Display**
    - **Validates: Requirements 5.3**
    - Test that all progress fields are displayed
    - _Requirements: 5.3_

  - [x] 15.7 Write property test for failure details display
    - **Property 17: Failure Details Display**
    - **Validates: Requirements 5.6**
    - Test that error details are shown when failures occur
    - _Requirements: 5.6_

  - [x] 15.8 Write property test for leaderboard data fetch
    - **Property 18: Leaderboard Data Fetch**
    - **Validates: Requirements 6.1**
    - Test that leaderboard data is fetched correctly
    - _Requirements: 6.1_

  - [x] 15.9 Write property test for leaderboard row completeness
    - **Property 19: Leaderboard Row Completeness**
    - **Validates: Requirements 6.2**
    - Test that all leaderboard row fields are displayed
    - _Requirements: 6.2_

  - [x] 15.10 Write property test for individual scorecard completeness
    - **Property 24: Individual Scorecard Completeness**
    - **Validates: Requirements 8.2, 8.3, 8.4, 8.5**
    - Test that all individual scorecard sections are displayed
    - _Requirements: 8.2, 8.3, 8.4, 8.5_

- [ ] 16. Create integration tests
  - [x] 16.1 Write integration test for authentication flow
    - Test full authentication page flow with AppTest
    - Test login success and failure scenarios
    - Test logout functionality
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.6_

  - [x] 16.2 Write integration test for hackathon creation flow
    - Test full form submission flow with AppTest
    - Test validation errors and success messages
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [x] 16.3 Write integration test for live dashboard flow
    - Test hackathon selection and stats display
    - Test analysis triggering and progress monitoring
    - _Requirements: 3.1, 3.2, 3.3, 4.1, 4.2, 4.3, 5.1, 5.2, 5.3_

  - [x] 16.4 Write integration test for results page flow
    - Test leaderboard display with search and sort
    - Test team detail navigation and scorecard display
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 7.1, 7.2_

  - [x] 16.5 Write integration test for intelligence page flow
    - Test intelligence data display with charts
    - Test unavailable data handling
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.6_

- [x] 17. Final checkpoint - Ensure all tests pass
  - Run pytest with coverage report
  - Verify 90%+ test coverage for components/
  - Verify all 27 property tests pass
  - Ensure all integration tests pass
  - Ask the user if questions arise.

- [x] 18. Create documentation and deployment files
  - Create README.md with setup instructions, usage guide, and architecture overview
  - Create .env.example with API_BASE_URL and API_KEY placeholders
  - Create .gitignore for Python and Streamlit artifacts
  - Add deployment instructions for Streamlit Cloud
  - _Requirements: 11.1_

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end page flows
- The implementation uses Python 3.12 to match the backend
- All API calls use the existing FastAPI backend endpoints
- No backend modifications are required
