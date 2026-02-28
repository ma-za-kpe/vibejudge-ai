# VibeJudge AI Frontend - Complete Flow Analysis

**Date:** February 28, 2026
**Purpose:** Holistic mapping of all user flows for comprehensive test coverage

---

## Flow Overview

### 1. Authentication Flow (app.py)
**Trigger:** User arrives at homepage without authentication
**Steps:**
1. Display login form (API key + base URL inputs)
2. User enters credentials
3. Validate API key → `GET /hackathons` (HTTP 200 = valid)
4. Store in `session_state["api_key"]` and `session_state["api_base_url"]`
5. Show success message + navigation links

**Edge Cases:**
- Invalid API key (HTTP 401)
- Network timeout
- Empty fields validation

---

### 2. Hackathon Creation Flow (1_🎯_Create_Hackathon.py)
**Trigger:** User navigates to Create Hackathon page
**Steps:**
1. Display form (name, description, start_date, end_date, budget_limit)
2. Client-side validation:
   - End date must be after start date
   - Budget must be positive or empty
   - Name and description required
3. Submit → `POST /hackathons`
4. Success → Display hack_id + next steps
5. Error → Display validation errors

**Edge Cases:**
- HTTP 422 validation errors
- Date range validation failures
- Budget validation (zero, negative)

---

### 3. Live Dashboard - Monitoring Flow (2_📊_Live_Dashboard.py)
**Trigger:** User navigates to Live Dashboard
**Steps:**
1. Fetch hackathons → `GET /hackathons` → Returns `{hackathons: [...], next_cursor, has_more}`
2. Filter out DRAFT/ARCHIVED hackathons
3. Display dropdown (hackathon names)
4. User selects hackathon → Store in `session_state["selected_hackathon"]`
5. Fetch stats → `GET /hackathons/{id}/stats`
6. Display metrics (submission_count, verified_count, pending_count, participant_count)
7. Auto-refresh every 5 minutes

**Edge Cases:**
- No hackathons available → Warning message
- Stats not found (HTTP 404) → Error message
- Empty stats response

---

### 4. Live Dashboard - Analysis Job Lifecycle Flow (2_📊_Live_Dashboard.py)
**Trigger:** User wants to trigger analysis
**The flow you showed - this is the critical one with 7 failing tests**

#### State Machine:

```
State 1: NO_ACTIVE_JOB
├─ Condition: fetch_active_job() returns None
├─ UI: Show "🚀 Start Analysis" button
└─ cost_estimate in session_state is None

State 2: COST_ESTIMATE_FETCHED
├─ Trigger: User clicks "Start Analysis"
├─ Action: POST /hackathons/{id}/analyze/estimate
├─ UI: Show cost + confirmation dialog ("Confirm & Start", "Cancel")
└─ cost_estimate in session_state = 1.25

State 3: JOB_QUEUED
├─ Trigger: User clicks "Confirm & Start"
├─ Action: POST /hackathons/{id}/analyze → Returns {job_id, estimated_cost_usd, status: "queued"}
├─ UI: Display job_id + cost → st.rerun()
└─ cost_estimate cleared from session_state

State 4: JOB_RUNNING (after rerun)
├─ Condition: fetch_active_job() returns job_id (status="running")
├─ UI:
│   - Button HIDDEN
│   - Show "📊 Analysis job in progress: {job_id}"
│   - Progress monitoring section displayed
├─ Action: GET /hackathons/{id}/jobs/{job_id} → Returns progress details
└─ Display: Progress bar, metrics (completed/failed/total), current cost, ETA

State 5: JOB_COMPLETED
├─ Condition: GET /hackathons/{id}/jobs/{job_id} returns {status: "completed"}
├─ UI:
│   - Success message + balloons
│   - Final summary (total analyzed, failed, cost)
│   - After 10s cache refresh, fetch_active_job() returns None
│   - Button REAPPEARS → Back to State 1
└─ Cache cleared → st.rerun()

State 6: JOB_FAILED
├─ Condition: GET /hackathons/{id}/jobs/{job_id} returns {status: "failed"}
├─ UI: Error message + failure details
└─ Cache cleared → Button reappears

State 7: JOB_CONFLICT
├─ Trigger: User tries to start analysis while job running
├─ Action: POST /hackathons/{id}/analyze → HTTP 409
├─ UI: Conflict error message
└─ Stay in current state

State 8: BUDGET_EXCEEDED
├─ Trigger: Cost estimate OR analyze request exceeds budget
├─ Action: POST returns HTTP 402
├─ UI: Budget exceeded warning
└─ cost_estimate cleared → Back to State 1
```

**API Endpoints:**
- `GET /hackathons/{id}/analyze/status` → `{status, job_id}` (cached 10s)
- `POST /hackathons/{id}/analyze/estimate` → `{estimate: {total_cost_usd: {expected, min, max}}}`
- `POST /hackathons/{id}/analyze` → `{job_id, estimated_cost_usd, status, message}` (HTTP 202)
- `GET /hackathons/{id}/jobs/{job_id}` → `{status, progress_percent, completed_submissions, ...}`

**Edge Cases (7 FAILING TESTS):**
1. ✅ Cost estimate display → test_analysis_cost_estimate_display
2. ✅ Confirmation dialog → test_analysis_confirmation_dialog
3. ❌ Job ID display after confirm → test_analysis_start_displays_job_id_and_cost
4. ❌ Progress monitoring → test_analysis_progress_monitoring
5. ❌ Failure details display → test_analysis_failure_details_display
6. ❌ Completion success message → test_analysis_completion_success_message
7. ❌ Stats not found error → test_stats_not_found_error
8. ❌ Cancel button → test_cancel_analysis_confirmation

---

### 5. Results Page - Leaderboard Flow (3_🏆_Results.py)
**Trigger:** User navigates to Results page
**Steps:**
1. Initialize `session_state["view_mode"] = "leaderboard"`
2. Fetch hackathons → `GET /hackathons`
3. Display dropdown
4. User selects hackathon → `GET /hackathons/{id}/leaderboard`
5. Display leaderboard table:
   - Rank, Team Name, Overall Score, Confidence, Created At
   - Search by team name (client-side filter)
   - Sort by score/name/date (client-side)
   - Pagination (50 per page)

**Edge Cases:**
- No submissions → Info message
- Empty leaderboard
- Leaderboard not found (HTTP 404)

---

### 6. Results Page - Team Detail Flow (3_🏆_Results.py)
**Trigger:** User clicks on team row
**The other critical flow with 5 failing tests**

#### State Machine:

```
State 1: LEADERBOARD_VIEW
├─ Condition: session_state["view_mode"] = "leaderboard"
├─ UI: Show leaderboard table with clickable rows
└─ No selected_sub_id in session_state

State 2: DETAIL_VIEW_LOADING
├─ Trigger: User clicks team row
├─ Action:
│   - Set session_state["view_mode"] = "team_detail"
│   - Set session_state["selected_sub_id"] = sub_id
│   - st.rerun()
└─ Page reloads

State 3: DETAIL_VIEW_DISPLAY (after rerun)
├─ Condition: session_state["view_mode"] = "team_detail"
├─ UI: Show "⬅️ Back to Leaderboard" button at top
├─ Action: GET /hackathons/{id}/submissions/{sub_id}/scorecard
├─ Display:
│   - 4 tabs: Overview, Agent Analysis, Repository, Team Members
│   - Overview: Overall score, confidence, recommendation, dimension scores, cost
│   - Agent Analysis: Individual agent results (BugHunter, PerformanceAnalyzer, etc.)
│   - Repository: Repo URL, commit hash, languages, file structure
│   - Team Members: Member list with hiring scores
└─ Scorecard data structure expected

State 4: BACK_TO_LEADERBOARD
├─ Trigger: User clicks "Back to Leaderboard"
├─ Action:
│   - Set session_state["view_mode"] = "leaderboard"
│   - st.rerun()
└─ Page reloads → Back to State 1
```

**API Endpoints:**
- `GET /hackathons/{id}/leaderboard` → `{submissions: [{sub_id, team_name, overall_score, ...}], total_submissions, analyzed_count}`
- `GET /hackathons/{id}/submissions/{sub_id}/scorecard` → Full scorecard object

**Scorecard Structure Expected:**
```python
{
    "team_name": str,
    "overall_score": float,
    "confidence": float,
    "recommendation": str,  # "must_interview" | "consider" | "pass"
    "dimension_scores": {
        "code_quality": {"raw": float, "weight": float, "weighted": float},
        "bug_severity": {...},
        "performance": {...},
        "innovation": {...},
        "documentation": {...}
    },
    "total_cost_usd": float,
    "agent_results": {
        "bug_hunter": {"cost_usd": float, "findings": [...]},
        "performance_analyzer": {...},
        "innovation_scorer": {...},
        "ai_detection": {...}
    },
    "repository": {
        "url": str,
        "commit_hash": str,
        "primary_language": str,
        "languages": {...},
        "file_structure": [...]
    },
    "team_dynamics": {
        "members": [{"name": str, "github_username": str, "hiring_score": float}],
        "team_size": int
    }
}
```

**Edge Cases (5 FAILING TESTS):**
1. ❌ Team detail navigation → test_team_detail_navigation
2. ❌ Scorecard display completeness → test_scorecard_display_completeness
3. ❌ Pagination limit 50 → test_pagination_limit_50_submissions
4. ❌ Back to leaderboard button → test_back_to_leaderboard_button
5. ❌ No submissions message → test_no_submissions_message

---

### 7. Intelligence Page - Insights Flow (4_💡_Intelligence.py)
**Trigger:** User navigates to Intelligence page
**Steps:**
1. Fetch hackathons → `GET /hackathons`
2. Display dropdown
3. User selects hackathon → `GET /hackathons/{id}/intelligence`
4. Display 3 tabs:
   - Must-Interview Candidates (name, team, skills, hiring_score)
   - Technology Trends (chart + table)
   - Sponsor API Usage (metrics)
5. Handle unavailable data gracefully

**Edge Cases:**
- Intelligence not ready (analysis not complete) → Info message
- Empty data for each section
- API error (HTTP 500) → Graceful handling

---

## Test Strategy for 12 Remaining Failures

### Core Issues to Solve

1. **Session State Persistence After st.rerun()**
   - Problem: AppTest doesn't maintain session_state across reruns
   - Solution: Manually set session_state before each at.run()

2. **Comprehensive API Mocking**
   - Problem: Tests mock initial endpoints but not post-rerun endpoints
   - Solution: Mock ALL possible endpoints the page might call

3. **UI Element Visibility After State Changes**
   - Problem: Button disappears/reappears based on fetch_active_job() result
   - Solution: Mock fetch_active_job() to return correct values at each stage

4. **Detail View Navigation**
   - Problem: Session state changes not persisting across reruns
   - Solution: Set view_mode and selected_sub_id explicitly in test

---

## Next Steps

1. Fix Live Dashboard tests (7 failures)
2. Fix Results Page tests (5 failures)
3. Run full test suite
4. Verify 330/330 passing
