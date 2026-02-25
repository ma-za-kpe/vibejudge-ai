# Requirements Document: Streamlit Organizer Dashboard

## Introduction

The Streamlit Organizer Dashboard is a web-based user interface that enables hackathon organizers to manage their events through a visual interface. The dashboard consumes the existing VibeJudge FastAPI backend and provides five core pages: authentication, hackathon creation, live monitoring, results viewing, and intelligence insights. This MVP focuses exclusively on organizer workflows and excludes team submission portals.

## Glossary

- **Dashboard**: The Streamlit web application that organizers interact with
- **Backend_API**: The existing FastAPI service providing REST endpoints
- **Session_State**: Streamlit's mechanism for storing user data across page interactions
- **API_Key**: Authentication credential stored in session state after login
- **Hackathon**: An event entity with submissions, analysis jobs, and results
- **Submission**: A team's project entry with repository URL and metadata
- **Scorecard**: Detailed analysis results for a single submission
- **Intelligence**: Hiring insights and technology trends derived from submissions
- **Auto_Refresh**: Automatic page reload mechanism for live data updates
- **Cache**: Temporary storage of API responses with time-to-live expiration

## Requirements

### Requirement 1: API Key Authentication

**User Story:** As an organizer, I want to authenticate with my API key, so that I can access my hackathon data securely.

#### Acceptance Criteria

1. THE Dashboard SHALL display an authentication form on initial load
2. WHEN an organizer enters an API key, THE Dashboard SHALL validate it against the Backend_API
3. WHEN the Backend_API returns HTTP 200, THE Dashboard SHALL store the API_Key in Session_State
4. WHEN the Backend_API returns HTTP 401, THE Dashboard SHALL display an error message
5. WHILE the API_Key is stored in Session_State, THE Dashboard SHALL include it in all Backend_API requests via X-API-Key header
6. WHEN an organizer clicks logout, THE Dashboard SHALL clear the API_Key from Session_State

### Requirement 2: Hackathon Creation

**User Story:** As an organizer, I want to create a new hackathon through a form, so that I can start accepting submissions.

#### Acceptance Criteria

1. THE Dashboard SHALL provide a hackathon creation form with name, description, start date, end date, and budget fields
2. WHEN an organizer submits the form, THE Dashboard SHALL send a POST request to /hackathons endpoint
3. WHEN the Backend_API returns HTTP 201, THE Dashboard SHALL display the created hackathon details including hack_id
4. WHEN the Backend_API returns HTTP 422, THE Dashboard SHALL display validation errors inline with the form fields
5. THE Dashboard SHALL validate that end_date is after start_date before submission
6. THE Dashboard SHALL validate that budget_limit_usd is a positive number or empty

### Requirement 3: Live Dashboard Monitoring

**User Story:** As an organizer, I want to monitor submission statistics in real-time, so that I can track hackathon progress.

#### Acceptance Criteria

1. THE Dashboard SHALL display a hackathon selection dropdown populated from GET /hackathons
2. WHEN an organizer selects a hackathon, THE Dashboard SHALL fetch statistics from GET /hackathons/{hack_id}/stats
3. THE Dashboard SHALL display submission_count, verified_count, pending_count, and participant_count
4. WHILE viewing the live dashboard, THE Dashboard SHALL refresh statistics every 5 seconds using streamlit-autorefresh
5. WHEN the Backend_API returns HTTP 404, THE Dashboard SHALL display a not found message
6. THE Dashboard SHALL cache API responses for 30 seconds to reduce Backend_API load

### Requirement 4: Analysis Triggering

**User Story:** As an organizer, I want to trigger analysis for my hackathon submissions, so that I can generate scorecards.

#### Acceptance Criteria

1. THE Dashboard SHALL display a "Start Analysis" button on the live dashboard page
2. WHEN an organizer clicks "Start Analysis", THE Dashboard SHALL send a POST request to /hackathons/{hack_id}/analyze
3. WHEN the Backend_API returns HTTP 202, THE Dashboard SHALL display the job_id and estimated_cost_usd
4. WHEN the Backend_API returns HTTP 402, THE Dashboard SHALL display a budget exceeded error
5. WHEN the Backend_API returns HTTP 409, THE Dashboard SHALL display an analysis already running message
6. THE Dashboard SHALL display a cost estimate before triggering analysis using POST /hackathons/{hack_id}/estimate

### Requirement 5: Analysis Progress Monitoring

**User Story:** As an organizer, I want to see analysis progress in real-time, so that I know when results will be ready.

#### Acceptance Criteria

1. WHEN analysis is running, THE Dashboard SHALL poll GET /hackathons/{hack_id}/jobs/{job_id} every 5 seconds
2. THE Dashboard SHALL display progress_percent as a progress bar
3. THE Dashboard SHALL display completed_submissions, failed_submissions, and current_cost_usd
4. THE Dashboard SHALL display estimated_completion timestamp
5. WHEN status changes to "completed", THE Dashboard SHALL stop polling and display a success message
6. WHEN failed_submissions is greater than 0, THE Dashboard SHALL display error details

### Requirement 6: Results Leaderboard

**User Story:** As an organizer, I want to view ranked submissions, so that I can identify top teams.

#### Acceptance Criteria

1. THE Dashboard SHALL fetch leaderboard data from GET /hackathons/{hack_id}/leaderboard
2. THE Dashboard SHALL display rank, team_name, overall_score, and recommendation for each submission
3. THE Dashboard SHALL provide a search input that filters submissions by team_name
4. THE Dashboard SHALL provide a sort dropdown with options for score, team_name, and created_at
5. WHEN an organizer clicks a team row, THE Dashboard SHALL navigate to the team detail view
6. THE Dashboard SHALL display total_submissions and analyzed counts at the top of the leaderboard

### Requirement 7: Team Detail Scorecard

**User Story:** As an organizer, I want to view detailed scorecards for a team, so that I can understand their evaluation.

#### Acceptance Criteria

1. THE Dashboard SHALL fetch scorecard data from GET /hackathons/{hack_id}/submissions/{sub_id}/scorecard
2. THE Dashboard SHALL display overall_score, confidence, and recommendation
3. THE Dashboard SHALL display dimension_scores with raw and weighted values
4. THE Dashboard SHALL display agent results including summary, strengths, and improvements
5. THE Dashboard SHALL display repo_meta including primary_language, commit_count, and has_tests
6. THE Dashboard SHALL display cost breakdown by agent

### Requirement 8: Individual Team Member Scorecards

**User Story:** As an organizer, I want to view individual contributor analysis, so that I can identify standout developers.

#### Acceptance Criteria

1. THE Dashboard SHALL fetch individual scorecards from GET /hackathons/{hack_id}/submissions/{sub_id}/individual-scorecards
2. THE Dashboard SHALL display team_dynamics including collaboration_quality and role_distribution
3. THE Dashboard SHALL display strategy_analysis including development_approach and time_management
4. THE Dashboard SHALL display actionable_feedback for each team member
5. THE Dashboard SHALL display member_name, commit_count, and skill_assessment for each contributor
6. WHEN individual scorecard data is unavailable, THE Dashboard SHALL display a message indicating analysis is pending

### Requirement 9: Hiring Intelligence

**User Story:** As an organizer, I want to view hiring insights, so that I can identify candidates for recruitment.

#### Acceptance Criteria

1. THE Dashboard SHALL fetch intelligence data from GET /hackathons/{hack_id}/intelligence
2. THE Dashboard SHALL display must_interview candidates with name, skills, and hiring_score
3. THE Dashboard SHALL display technology_trends with language, framework, and usage counts
4. THE Dashboard SHALL provide a chart visualization for technology_trends using Plotly
5. THE Dashboard SHALL display sponsor_api_usage statistics
6. WHEN intelligence data is unavailable, THE Dashboard SHALL display a message indicating analysis must complete first

### Requirement 10: Error Handling

**User Story:** As an organizer, I want clear error messages when API calls fail, so that I can troubleshoot issues.

#### Acceptance Criteria

1. WHEN the Backend_API returns HTTP 500, THE Dashboard SHALL display a generic server error message
2. WHEN the Backend_API returns HTTP 503, THE Dashboard SHALL display a service unavailable message
3. WHEN a network timeout occurs, THE Dashboard SHALL display a connection timeout message
4. WHEN the Backend_API returns HTTP 429, THE Dashboard SHALL display a rate limit exceeded message
5. THE Dashboard SHALL log all API errors to the console for debugging
6. THE Dashboard SHALL provide a retry button for failed API requests

### Requirement 11: Performance Requirements

**User Story:** As an organizer, I want the dashboard to load quickly, so that I can work efficiently.

#### Acceptance Criteria

1. THE Dashboard SHALL load the initial authentication page within 2 seconds
2. THE Dashboard SHALL cache GET /hackathons responses for 30 seconds
3. THE Dashboard SHALL cache GET /hackathons/{hack_id}/stats responses for 30 seconds
4. THE Dashboard SHALL use Streamlit st.cache_data decorator for API response caching
5. THE Dashboard SHALL display loading spinners during API requests longer than 500 milliseconds
6. THE Dashboard SHALL limit leaderboard pagination to 50 submissions per page

### Requirement 12: Responsive UI Design

**User Story:** As an organizer, I want a clean and intuitive interface, so that I can navigate easily.

#### Acceptance Criteria

1. THE Dashboard SHALL use Streamlit columns for multi-column layouts
2. THE Dashboard SHALL use Streamlit expanders for collapsible sections
3. THE Dashboard SHALL use Streamlit tabs for organizing related content
4. THE Dashboard SHALL display success messages using st.success
5. THE Dashboard SHALL display error messages using st.error
6. THE Dashboard SHALL display warning messages using st.warning
