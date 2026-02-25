# VIBEJUDGE - FRONTEND vs BACKEND ARCHITECTURAL BREAKDOWN

**Based on:** VIBEJUDGE_SELF_SERVICE_PORTAL_CONCEPT.md

This document clearly separates what belongs in the frontend (user interface, client-side logic) versus the backend (APIs, services, business logic, database operations).

---

## FRONTEND (What Users See & Interact With)

### 1. ORGANIZER CREATE HACKATHON PAGE

**Route:** `/organizer/create`

**Components:**
```
┌─────────────────────────────────────┐
│ CreateHackathonForm                 │
├─────────────────────────────────────┤
│ • NameInput                         │
│ • DateTimePicker (deadline)         │
│ • AnalysisScheduleSelector          │
│   ○ Radio: Immediate                │
│   ○ Radio: Manual                   │
│   ○ Radio: Scheduled (DatePicker)   │
│ • BudgetInput (optional)            │
│ • SubmitButton                      │
└─────────────────────────────────────┘
```

**State Management:**
```javascript
{
  name: string,
  deadline: DateTime,
  analysisMode: "immediate" | "manual" | "scheduled",
  scheduledTime: DateTime | null,
  budget: number | null,
  isSubmitting: boolean,
  errors: Record<string, string>
}
```

**Frontend Validation:**
- Name: 2-100 chars, no special characters
- Deadline: Must be future date
- Scheduled time: Must be after deadline
- Budget: Positive number or empty

**API Call:**
```
POST /api/v1/hackathons
Body: { name, deadline, analysis_schedule, budget }
Response: { hack_id, slug, submission_url, qr_code_url }
```

---

### 2. HACKATHON CREATED SUCCESS PAGE

**Route:** `/organizer/hackathon/:slug/created`

**Components:**
```
┌─────────────────────────────────────┐
│ HackathonCreatedSuccess             │
├─────────────────────────────────────┤
│ • SubmissionLinkDisplay             │
│   - CopyButton                      │
│   - QRCodeButton → opens modal      │
│   - EmbedCodeButton → opens modal   │
│                                     │
│ • TimelineDisplay                   │
│   - Submissions open: Now           │
│   - Deadline: [date]                │
│   - Analysis: [scheduled time]      │
│                                     │
│ • ShareTemplates                    │
│   - Pre-written Discord message     │
│   - Pre-written Email template      │
│   - CopyButton for each             │
│                                     │
│ • CTAButton: "Go to Dashboard"      │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ QRCodeModal (when opened)           │
├─────────────────────────────────────┤
│ • QR Code Image (generated)         │
│ • DownloadButton (PNG, SVG, PDF)    │
│ • Print-ready poster preview        │
└─────────────────────────────────────┘
```

**API Calls:**
```
GET /api/v1/hackathons/:slug/qr-code
Response: { qr_code_png_url, qr_code_svg_url }

GET /api/v1/hackathons/:slug/poster
Response: { poster_pdf_url }
```

---

### 3. TEAM SUBMISSION PAGE (The Main Portal)

**Route:** `/submit/:hackathon_slug`

**Components:**
```
┌─────────────────────────────────────────────┐
│ SubmissionPage                              │
├─────────────────────────────────────────────┤
│ • Header                                    │
│   - Hackathon name                          │
│   - Countdown timer (live)                  │
│   - Stats: "47 teams submitted"             │
│                                             │
│ • SubmissionForm                            │
│   ┌───────────────────────────────────┐    │
│   │ • TeamNameInput                   │    │
│   │   - Real-time uniqueness check    │    │
│   │   - Debounced API call (500ms)    │    │
│   │   - Inline validation messages    │    │
│   │                                   │    │
│   │ • RepoURLInput                    │    │
│   │   - Real-time GitHub validation   │    │
│   │   - Loading spinner               │    │
│   │   - RepoPreviewCard (on success)  │    │
│   │   - Warning messages              │    │
│   │                                   │    │
│   │ • TeamMembersList                 │    │
│   │   - Dynamic add/remove            │    │
│   │   - Name + Email per member       │    │
│   │   - Validation per field          │    │
│   │                                   │    │
│   │ • ConfirmationCheckbox            │    │
│   │                                   │    │
│   │ • SubmitButton                    │    │
│   │   - Disabled until valid          │    │
│   │   - Loading state                 │    │
│   └───────────────────────────────────┘    │
│                                             │
│ • HelpText: "You can edit later"           │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ RepoPreviewCard (inline component)          │
├─────────────────────────────────────────────┤
│ ✅ Repository verified!                     │
│                                             │
│ 📦 neural-ninjas                            │
│ ⭐ 0 stars • 🐍 Python                      │
│ 📝 23 commits • 👥 3 contributors           │
│ 🕐 Last updated: 5 minutes ago              │
│                                             │
│ ⚠️ Repo created 5 days before hackathon    │
│    Judges will review commit timeline       │
└─────────────────────────────────────────────┘
```

**State Management:**
```javascript
{
  hackathon: {
    name: string,
    slug: string,
    deadline: DateTime,
    stats: { total_submissions: number }
  },

  form: {
    teamName: string,
    repoUrl: string,
    members: Array<{name: string, email: string}>,
    confirmed: boolean
  },

  validation: {
    teamName: {
      status: "idle" | "checking" | "valid" | "invalid",
      message: string | null
    },
    repoUrl: {
      status: "idle" | "checking" | "valid" | "invalid",
      message: string | null,
      metadata: RepoMetadata | null
    }
  },

  isSubmitting: boolean,
  errors: Record<string, string>
}
```

**Real-Time API Calls:**
```javascript
// Debounced team name check
useDebounce(teamName, 500) →
  GET /api/v1/hackathons/:slug/check-team-name?name=Neural%20Ninjas
  Response: { available: boolean, suggestion?: string }

// Debounced repo validation
useDebounce(repoUrl, 500) →
  POST /api/v1/portal/validate-repo
  Body: { repo_url, hackathon_slug }
  Response: {
    valid: boolean,
    error?: string,
    warning?: string,
    metadata?: {
      name: string,
      language: string,
      commits: number,
      contributors: number,
      created_at: string,
      last_updated: string
    }
  }
```

**Form Submission:**
```javascript
POST /api/v1/portal/submit
Body: {
  hackathon_slug,
  team_name,
  repo_url,
  team_members: [{name, email}, ...],
  agreed_to_terms: true
}
Response: {
  submission_id: string,
  edit_token: string,
  edit_url: string
}
```

---

### 4. SUBMISSION CONFIRMATION PAGE

**Route:** `/submit/:hackathon_slug/success`

**Components:**
```
┌─────────────────────────────────────┐
│ SubmissionSuccess                   │
├─────────────────────────────────────┤
│ ✅ Submitted!                       │
│                                     │
│ Team: Neural Ninjas                 │
│ Submission #48                      │
│                                     │
│ You can edit until [deadline]       │
│                                     │
│ 📋 Your edit link:                  │
│ [long URL]                          │
│ [Copy Link] [Bookmark This]         │
│                                     │
│ Questions? Contact: [organizer]     │
└─────────────────────────────────────┘
```

**No API calls** (just displays data from previous response)

---

### 5. EDIT SUBMISSION PAGE

**Route:** `/edit/:hackathon_slug/:token`

**Components:**
```
Same as SubmissionForm, but:
• Pre-filled with existing data
• "Update" button instead of "Submit"
• Shows "Last edited: [time]"
• Warning if deadline approaching
```

**API Calls:**
```
GET /api/v1/portal/submission/:token
Response: { team_name, repo_url, team_members, submitted_at }

PUT /api/v1/portal/submission/:token
Body: { team_name, repo_url, team_members }
Response: { success: true, updated_at: string }
```

---

### 6. ORGANIZER DASHBOARD (Live Submissions)

**Route:** `/organizer/hackathon/:slug/dashboard`

**Components:**
```
┌───────────────────────────────────────────────┐
│ OrganizerDashboard                            │
├───────────────────────────────────────────────┤
│ • Header                                      │
│   - Hackathon name                            │
│   - Countdown to deadline (live)              │
│                                               │
│ • StatsPanel                                  │
│   ┌─────────┬─────────┬─────────┬─────────┐  │
│   │ Submitted│ Verified│ Pending │ Disputed│  │
│   │   142   │   128   │   12    │    2    │  │
│   └─────────┴─────────┴─────────┴─────────┘  │
│                                               │
│   👥 487 participants across 142 teams        │
│   📈 Avg team size: 3.4                       │
│                                               │
│ • TechnologyTrendsChart                       │
│   [Bar chart of languages]                    │
│                                               │
│ • IssuesPanel (if any)                        │
│   ⚠️ 2 teams disputed                         │
│   ⚠️ 3 repos became private                   │
│   [View Details]                              │
│                                               │
│ • QuickActions                                │
│   [View All Submissions]                      │
│   [Download CSV]                              │
│   [Manually Add Team]                         │
│   [Start Analysis] (if past deadline)         │
└───────────────────────────────────────────────┘
```

**State Management:**
```javascript
{
  hackathon: HackathonMetadata,
  stats: {
    total: number,
    verified: number,
    pending: number,
    disputed: number,
    participants: number
  },
  technologies: Array<{name: string, count: number}>,
  issues: Array<{type: string, count: number}>,

  // Real-time updates via WebSocket or polling
  lastUpdated: DateTime
}
```

**API Calls:**
```
GET /api/v1/hackathons/:slug/stats
Response: { stats, technologies, issues, submissions: [...] }

// WebSocket for real-time updates
WS /api/v1/hackathons/:slug/live
Events: { type: "new_submission" | "update" | "issue", data: {...} }
```

---

### 7. ANALYSIS IN PROGRESS PAGE

**Route:** `/organizer/hackathon/:slug/analysis`

**Components:**
```
┌───────────────────────────────────────────────┐
│ AnalysisProgress                              │
├───────────────────────────────────────────────┤
│ HackMIT 2026 - Analysis in Progress          │
│                                               │
│ [████████████████░░░░░░] 42% Complete         │
│                                               │
│ 62 / 147 teams analyzed                       │
│ Time elapsed: 23 minutes                      │
│ Time remaining: ~32 minutes                   │
│                                               │
│ Cost so far: $2.79 / $6.62 estimated          │
│                                               │
│ 📊 Preliminary insights:                      │
│ • Top language: Python (67 teams)             │
│ • Highest score: 8.9/10 (AI Wizards)          │
│                                               │
│ ⚡ Live Feed: (scrolling)                     │
│ 9:31 - Analyzing "Data Dragons" (4/10 agents) │
│ 9:31 - Analyzing "Code Crushers" (2/10)       │
│ 9:30 - ✅ "Neural Ninjas" complete (7.8/10)   │
│                                               │
│ [Pause Analysis] [Cancel]                     │
└───────────────────────────────────────────────┘
```

**State Management:**
```javascript
{
  progress: {
    total: number,
    completed: number,
    percentage: number,
    startedAt: DateTime,
    estimatedCompletion: DateTime
  },

  cost: {
    spent: number,
    estimated: number,
    budget: number
  },

  insights: {
    topLanguages: Array<{name: string, count: number}>,
    highestScore: { team: string, score: number }
  },

  liveFeed: Array<{
    timestamp: DateTime,
    teamName: string,
    status: "analyzing" | "complete",
    score?: number,
    agentsComplete?: number
  }>
}
```

**API Calls:**
```
GET /api/v1/hackathons/:slug/analysis/progress
Response: { progress, cost, insights, live_feed }

// WebSocket for real-time updates
WS /api/v1/hackathons/:slug/analysis/live
Events: {
  type: "progress_update" | "team_complete" | "analysis_complete",
  data: {...}
}
```

---

### 8. RESULTS DASHBOARD

**Route:** `/organizer/hackathon/:slug/results`

**Components:**
```
┌───────────────────────────────────────────────┐
│ ResultsDashboard                              │
├───────────────────────────────────────────────┤
│ ✅ Analysis Complete - 10:18 AM               │
│                                               │
│ [Search teams...                      ] 🔍    │
│                                               │
│ Filters: [All Teams ▼] [Score: High→Low ▼]   │
│                                               │
│ • TeamResultCard (repeated)                   │
│   ┌─────────────────────────────────────┐    │
│   │ #1 AI Wizards          8.9/10 ⭐⭐⭐  │    │
│   │ Python, TensorFlow, React           │    │
│   │ 4 members • Exceptional quality     │    │
│   │ [View Report] [Contact Team]        │    │
│   └─────────────────────────────────────┘    │
│                                               │
│ [Load More] (pagination)                      │
│                                               │
│ Quick Actions:                                │
│ [Download All Reports] [Export CSV]           │
│ [Email Top 20] [Share with Sponsors]          │
└───────────────────────────────────────────────┘
```

**State Management:**
```javascript
{
  results: Array<TeamResult>,
  filters: {
    search: string,
    sortBy: "score" | "name" | "submitted_at",
    sortOrder: "asc" | "desc",
    technology: string | null,
    teamSize: number | null
  },
  pagination: {
    page: number,
    perPage: number,
    total: number
  }
}
```

**API Calls:**
```
GET /api/v1/hackathons/:slug/results
Query: { search, sort_by, sort_order, technology, page, per_page }
Response: {
  results: Array<{
    rank: number,
    team_name: string,
    score: number,
    technologies: string[],
    member_count: number,
    highlights: string[]
  }>,
  total: number,
  page: number
}
```

---

### 9. TEAM DETAIL VIEW

**Route:** `/organizer/hackathon/:slug/team/:team_id`

**Components:**
```
┌───────────────────────────────────────────────┐
│ TeamDetailView                                │
├───────────────────────────────────────────────┤
│ Team: AI Wizards                              │
│ Overall Score: 8.9/10 ⭐⭐⭐⭐⭐               │
│                                               │
│ 🏆 Recommended Awards:                        │
│ • Best Overall Project                        │
│ • Best Use of AI/ML                           │
│                                               │
│ 📊 Score Breakdown:                           │
│ [Bar chart: Quality 9.2, Innovation 8.8, ...] │
│                                               │
│ 👥 Team Members: (expandable list)            │
│ • Sarah Martinez (Captain)                    │
│   45 commits • ML Engineer                    │
│   ⭐⭐⭐⭐⭐ Senior level                       │
│   [Email] [LinkedIn] [GitHub]                 │
│                                               │
│ 🔍 Project Summary:                           │
│ [Full text description]                       │
│                                               │
│ 💡 What Impressed Us: (expandable)            │
│ ⚠️ Areas for Improvement: (expandable)        │
│                                               │
│ [Download PDF] [Email Team] [Add to Sponsors] │
└───────────────────────────────────────────────┘
```

**API Calls:**
```
GET /api/v1/hackathons/:slug/teams/:team_id/report
Response: {
  team_name: string,
  overall_score: number,
  score_breakdown: {...},
  recommended_awards: string[],
  team_members: Array<MemberDetail>,
  project_summary: string,
  strengths: string[],
  improvements: string[],
  repo_url: string,
  report_pdf_url: string
}
```

---

## BACKEND (APIs, Services, Business Logic)

### 1. HACKATHON MANAGEMENT

**Endpoint:** `POST /api/v1/hackathons`

**Logic:**
```python
def create_hackathon(data: CreateHackathonInput):
    # Generate unique slug
    slug = generate_slug(data.name)  # "hackmit-2026"

    # Ensure slug is unique
    while slug_exists(slug):
        slug = f"{slug}-{random_suffix()}"

    # Generate IDs
    hack_id = f"hack_{secrets.token_urlsafe(16)}"

    # Store in DynamoDB
    hackathon = {
        "PK": f"HACK#{hack_id}",
        "SK": "METADATA",
        "GSI1PK": f"SLUG#{slug}",
        "GSI1SK": "METADATA",

        "hack_id": hack_id,
        "slug": slug,
        "name": data.name,
        "submission_deadline": data.deadline.isoformat(),
        "analysis_schedule": {
            "mode": data.analysis_mode,  # "immediate" | "manual" | "scheduled"
            "scheduled_time": data.scheduled_time.isoformat() if data.scheduled_time else None
        },
        "budget_limit_usd": data.budget,
        "status": "open",  # "open" | "closed" | "analyzing" | "complete"
        "created_at": utcnow().isoformat(),
        "created_by": current_user.id
    }

    dynamo.put_item(hackathon)

    # Generate submission URL
    submission_url = f"https://vibejudge.ai/submit/{slug}"

    # Generate QR code (background job)
    qr_code_url = generate_qr_code(submission_url, hack_id)

    return {
        "hack_id": hack_id,
        "slug": slug,
        "submission_url": submission_url,
        "qr_code_url": qr_code_url
    }
```

**Services Used:**
- `SlugGenerator` - Convert name to URL-safe slug
- `DynamoDB` - Store hackathon metadata
- `QRCodeGenerator` - Generate QR code image (PIL/qrcode library)
- `S3` - Store QR code PNG

---

### 2. REAL-TIME REPO VALIDATION

**Endpoint:** `POST /api/v1/portal/validate-repo`

**Logic:**
```python
async def validate_repo(repo_url: str, hackathon_slug: str):
    # Parse GitHub URL
    owner, repo = parse_github_url(repo_url)

    # Check cache first (Redis, 5min TTL)
    cache_key = f"repo_validation:{owner}/{repo}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    try:
        # Parallel GitHub API calls
        repo_data, commits, contributors = await asyncio.gather(
            github_api.get_repo(owner, repo),
            github_api.get_commits(owner, repo, per_page=100),
            github_api.get_contributors(owner, repo)
        )

        # Validation checks
        if repo_data["private"]:
            return {
                "valid": False,
                "error": "Repository is private. Please make it public."
            }

        if len(commits) == 0:
            return {
                "valid": False,
                "error": "Repository has no commits. Push your code first."
            }

        # Check if already submitted
        existing = await dynamo.query_gsi(
            "GSI2",
            pk=f"REPO#{repo_url}",
            sk_begins_with=f"HACK#{hackathon.hack_id}"
        )

        if existing:
            return {
                "valid": False,
                "error": f"Already submitted by team '{existing['team_name']}'"
            }

        # Build metadata response
        result = {
            "valid": True,
            "metadata": {
                "name": repo_data["name"],
                "language": repo_data["language"],
                "stars": repo_data["stargazers_count"],
                "commits": len(commits),
                "contributors": len(contributors),
                "created_at": repo_data["created_at"],
                "last_updated": repo_data["updated_at"]
            }
        }

        # Warning if repo created before hackathon
        if repo_data["created_at"] < hackathon["start_date"]:
            result["warning"] = "Repo created before hackathon start"

        # Cache for 5 minutes
        await redis.setex(cache_key, 300, json.dumps(result))

        return result

    except GitHubRateLimitError:
        # Graceful degradation
        return {
            "valid": True,
            "warning": "GitHub rate limit reached. Will verify during analysis."
        }
```

**Services Used:**
- `GitHubAPI` - Fetch repo data, commits, contributors
- `Redis` - Cache validation results
- `DynamoDB` - Check for duplicate repo submissions

---

### 3. TEAM SUBMISSION

**Endpoint:** `POST /api/v1/portal/submit`

**Logic:**
```python
async def submit_team(data: SubmissionInput):
    # Validate deadline
    if utcnow() > hackathon["submission_deadline"]:
        # Check grace period
        if grace_period and utcnow() <= deadline + grace_period:
            is_late = True
        else:
            raise HTTPException(403, "Submissions closed")

    # Final repo validation
    validation = await validate_repo(data.repo_url, hackathon.slug)
    if not validation["valid"]:
        raise HTTPException(400, validation["error"])

    # Check team name uniqueness
    existing = await dynamo.query_gsi(
        "GSI1",
        pk=f"HACK#{hackathon.hack_id}",
        sk_begins_with=f"TEAM#{data.team_name}"
    )
    if existing:
        raise HTTPException(400, f"Team name '{data.team_name}' already taken")

    # Check for duplicate members
    for member in data.team_members:
        existing_member = await dynamo.query_gsi(
            "GSI2",
            pk=f"EMAIL#{member.email}",
            sk_begins_with=f"HACK#{hackathon.hack_id}"
        )
        if existing_member:
            raise HTTPException(
                400,
                f"{member.email} already on team '{existing_member['team_name']}'"
            )

    # Generate submission ID and edit token
    submission_id = f"sub_{secrets.token_urlsafe(16)}"
    edit_token = secrets.token_urlsafe(32)

    # Create submission record
    submission = {
        "PK": f"SUB#{submission_id}",
        "SK": "METADATA",
        "GSI1PK": f"HACK#{hackathon.hack_id}",
        "GSI1SK": f"TEAM#{data.team_name}",
        "GSI2PK": f"REPO#{data.repo_url}",
        "GSI2SK": f"HACK#{hackathon.hack_id}",

        "submission_id": submission_id,
        "hack_id": hackathon.hack_id,
        "team_name": data.team_name,
        "repo_url": data.repo_url,
        "team_members": [m.dict() for m in data.team_members],
        "edit_token": hash_token(edit_token),  # Store hashed

        "status": "submitted",
        "is_late": is_late,
        "submitted_at": utcnow().isoformat(),

        "repo_metadata": validation["metadata"],
        "repo_snapshot_sha": None  # Set at deadline
    }

    await dynamo.put_item(submission)

    # Send confirmation email (background task)
    await email_service.send_submission_confirmation(
        to=data.team_members[0].email,
        team_name=data.team_name,
        submission_id=submission_id,
        edit_url=f"https://vibejudge.ai/edit/{hackathon.slug}/{edit_token}"
    )

    return {
        "submission_id": submission_id,
        "edit_token": edit_token,  # Send unhashed for frontend
        "edit_url": f"https://vibejudge.ai/edit/{hackathon.slug}/{edit_token}"
    }
```

**Services Used:**
- `DynamoDB` - Store submission, check duplicates
- `EmailService` (SES) - Send confirmation email
- `ValidationService` - Final repo check
- `TokenGenerator` - Secure edit tokens

---

### 4. SCHEDULED ANALYSIS TRIGGER

**Service:** EventBridge Scheduled Rule

**Logic:**
```python
# Lambda function triggered by EventBridge at scheduled time

def scheduled_analysis_handler(event):
    """
    Triggered by EventBridge at hackathon's scheduled analysis time.

    EventBridge Rule:
    - Created when hackathon is created
    - Schedule: hackathon.analysis_schedule.scheduled_time
    - Target: This Lambda
    - Payload: { hack_id: "hack_abc123" }
    """

    hack_id = event["hack_id"]

    # Fetch hackathon
    hackathon = dynamo.get_item(
        pk=f"HACK#{hack_id}",
        sk="METADATA"
    )

    # Safety checks
    if hackathon["status"] != "closed":
        logger.warning(f"Hackathon {hack_id} not closed yet, skipping analysis")
        return

    if hackathon.get("analysis_started"):
        logger.warning(f"Analysis already started for {hack_id}")
        return

    # Take repo snapshots if not done
    if not hackathon.get("snapshots_taken"):
        await take_repo_snapshots(hack_id)

    # Trigger analysis
    await start_analysis(hack_id)

    # Update status
    hackathon["status"] = "analyzing"
    hackathon["analysis_started_at"] = utcnow().isoformat()
    dynamo.put_item(hackathon)

    # Notify organizer
    await email_service.send_analysis_started(
        hackathon_id=hack_id,
        organizer_email=hackathon["organizer_email"]
    )
```

**Services Used:**
- `EventBridge` - Scheduled rule execution
- `Lambda` - Analysis trigger handler
- `StepFunctions` - Orchestrate parallel analysis
- `SES` - Notify organizer

---

### 5. DEADLINE ENFORCEMENT (Automatic Lock)

**Service:** EventBridge Scheduled Rule

**Logic:**
```python
def deadline_handler(event):
    """
    Triggered AT submission deadline.

    Tasks:
    1. Lock submissions (no more edits)
    2. Take repository snapshots
    3. Schedule analysis (if mode == "immediate")
    """

    hack_id = event["hack_id"]
    hackathon = dynamo.get_item(pk=f"HACK#{hack_id}", sk="METADATA")

    # Update status to closed
    hackathon["status"] = "closed"
    hackathon["closed_at"] = utcnow().isoformat()
    dynamo.put_item(hackathon)

    # Get all submissions
    submissions = dynamo.query_gsi(
        "GSI1",
        pk=f"HACK#{hack_id}",
        sk_begins_with="TEAM#"
    )

    logger.info(f"Taking snapshots for {len(submissions)} teams")

    # Take snapshots (parallel)
    await asyncio.gather(*[
        take_repo_snapshot(sub)
        for sub in submissions
    ])

    # Mark snapshots taken
    hackathon["snapshots_taken"] = True
    hackathon["snapshot_count"] = len(submissions)
    dynamo.put_item(hackathon)

    # If immediate analysis mode, trigger now
    if hackathon["analysis_schedule"]["mode"] == "immediate":
        await start_analysis(hack_id)

    # Notify organizer
    await email_service.send_deadline_closed(
        hackathon_id=hack_id,
        submissions_count=len(submissions)
    )
```

**Services Used:**
- `EventBridge` - Deadline trigger
- `Lambda` - Lock and snapshot handler
- `S3` - Store repo snapshots (tar.gz)
- `DynamoDB` - Update hackathon status

---

### 6. REPOSITORY SNAPSHOT SYSTEM

**Logic:**
```python
async def take_repo_snapshot(submission: dict):
    """
    Clone repo at exact commit SHA from deadline time.
    Store as immutable archive.
    """

    repo_url = submission["repo_url"]
    submission_id = submission["submission_id"]

    # Get latest commit SHA at deadline
    latest_commit = await github_api.get_latest_commit(repo_url)
    commit_sha = latest_commit["sha"]
    commit_timestamp = latest_commit["commit"]["committer"]["date"]

    # Clone repo to /tmp (Lambda ephemeral storage)
    clone_path = f"/tmp/{submission_id}"

    await git_clone(
        repo_url=repo_url,
        target_path=clone_path,
        commit_sha=commit_sha,  # Checkout specific commit
        depth=1  # Shallow clone (faster)
    )

    # Create tar.gz archive
    archive_path = f"/tmp/{submission_id}.tar.gz"
    await create_archive(clone_path, archive_path)

    # Upload to S3
    s3_key = f"snapshots/{submission['hack_id']}/{submission_id}/{commit_sha}.tar.gz"

    await s3.upload_file(
        file_path=archive_path,
        bucket="vibejudge-repo-snapshots",
        key=s3_key
    )

    # Update submission with snapshot info
    submission["repo_snapshot"] = {
        "commit_sha": commit_sha,
        "commit_timestamp": commit_timestamp,
        "s3_bucket": "vibejudge-repo-snapshots",
        "s3_key": s3_key,
        "snapshot_taken_at": utcnow().isoformat()
    }

    await dynamo.put_item(submission)

    # Cleanup /tmp
    shutil.rmtree(clone_path)
    os.remove(archive_path)
```

**Services Used:**
- `GitHubAPI` - Get latest commit
- `Git` (subprocess) - Clone repository
- `S3` - Store archive
- `Lambda /tmp` - Temporary storage (up to 10GB)

---

### 7. ANALYSIS ORCHESTRATION

**Service:** Step Functions State Machine

**Logic:**
```python
# Step Functions definition (JSON)
{
  "StartAt": "PreflightCheck",
  "States": {
    "PreflightCheck": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:...:function:preflight-check",
      "Next": "EstimateCost"
    },

    "EstimateCost": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:...:function:estimate-cost",
      "Next": "CheckBudget"
    },

    "CheckBudget": {
      "Type": "Choice",
      "Choices": [{
        "Variable": "$.cost_estimate",
        "NumericGreaterThan": "$.budget_limit",
        "Next": "BudgetExceeded"
      }],
      "Default": "ParallelAnalysis"
    },

    "BudgetExceeded": {
      "Type": "Fail",
      "Error": "BudgetExceeded",
      "Cause": "Estimated cost exceeds budget limit"
    },

    "ParallelAnalysis": {
      "Type": "Map",
      "ItemsPath": "$.submissions",
      "MaxConcurrency": 100,  # 100 parallel Lambdas
      "Iterator": {
        "StartAt": "AnalyzeTeam",
        "States": {
          "AnalyzeTeam": {
            "Type": "Task",
            "Resource": "arn:aws:lambda:...:function:analyzer",
            "End": true
          }
        }
      },
      "Next": "AggregateResults"
    },

    "AggregateResults": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:...:function:aggregate-results",
      "Next": "GenerateReports"
    },

    "GenerateReports": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:...:function:generate-reports",
      "Next": "NotifyComplete"
    },

    "NotifyComplete": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:...:function:notify-organizer",
      "End": true
    }
  }
}
```

**Lambda Functions:**

1. **preflight-check** - Validate all repos still accessible
2. **estimate-cost** - Calculate total cost
3. **analyzer** - Run analysis on single team (parallel invocations)
4. **aggregate-results** - Combine all scores, rank teams
5. **generate-reports** - Create PDFs, CSVs
6. **notify-organizer** - Send completion email

---

### 8. REAL-TIME PROGRESS TRACKING

**Service:** DynamoDB Streams + WebSocket API

**Logic:**
```python
# DynamoDB Stream handler
def stream_handler(event):
    """
    Listens to DynamoDB changes.
    Pushes updates to WebSocket clients.
    """

    for record in event["Records"]:
        if record["eventName"] == "MODIFY":
            new_image = record["dynamodb"]["NewImage"]

            # If submission analysis completed
            if new_image["PK"].startswith("SUB#") and "analysis_result" in new_image:
                hack_id = new_image["hack_id"]
                team_name = new_image["team_name"]
                score = new_image["analysis_result"]["overall_score"]

                # Push to WebSocket clients watching this hackathon
                await websocket_api.broadcast(
                    room=f"hackathon:{hack_id}",
                    message={
                        "type": "team_complete",
                        "data": {
                            "team_name": team_name,
                            "score": score,
                            "timestamp": utcnow().isoformat()
                        }
                    }
                )

                # Update progress counter
                await redis.incr(f"analysis_progress:{hack_id}")
```

**WebSocket Connection:**
```python
# Client connects to WebSocket
@websocket_route("/api/v1/hackathons/:slug/live")
async def websocket_handler(websocket, slug):
    hackathon = await get_hackathon_by_slug(slug)

    # Join room
    await websocket_api.join_room(
        websocket,
        room=f"hackathon:{hackathon.hack_id}"
    )

    # Send initial state
    await websocket.send_json({
        "type": "connected",
        "data": await get_current_progress(hackathon.hack_id)
    })

    # Keep connection alive
    await websocket.wait_closed()
```

---

### 9. REPORT GENERATION

**Service:** Lambda Function

**Logic:**
```python
async def generate_team_report(submission_id: str) -> str:
    """
    Generate PDF report for a single team.
    """

    # Fetch submission + analysis results
    submission = await dynamo.get_item(
        pk=f"SUB#{submission_id}",
        sk="METADATA"
    )

    analysis = submission["analysis_result"]

    # Generate HTML from template
    html = render_template("team_report.html", {
        "team_name": submission["team_name"],
        "score": analysis["overall_score"],
        "breakdown": analysis["score_breakdown"],
        "members": analysis["individual_assessments"],
        "strengths": analysis["strengths"],
        "improvements": analysis["improvements"],
        "recommended_awards": analysis["recommended_awards"]
    })

    # Convert HTML to PDF (using wkhtmltopdf or weasyprint)
    pdf_bytes = await html_to_pdf(html)

    # Upload to S3
    s3_key = f"reports/{submission['hack_id']}/{submission_id}.pdf"

    await s3.put_object(
        bucket="vibejudge-reports",
        key=s3_key,
        body=pdf_bytes,
        content_type="application/pdf"
    )

    # Generate signed URL (expires in 7 days)
    pdf_url = await s3.generate_presigned_url(
        bucket="vibejudge-reports",
        key=s3_key,
        expires_in=604800  # 7 days
    )

    # Update submission with PDF URL
    submission["report_pdf_url"] = pdf_url
    await dynamo.put_item(submission)

    return pdf_url
```

**Services Used:**
- `Jinja2` - Template rendering
- `WeasyPrint` - HTML to PDF conversion
- `S3` - Store PDFs
- `Lambda Layer` - WeasyPrint dependencies

---

## SUMMARY: FRONTEND vs BACKEND

### FRONTEND Responsibilities:
✅ User interface rendering
✅ Form validation (client-side)
✅ Real-time user feedback
✅ Debounced API calls
✅ State management
✅ Countdown timers
✅ Charts/visualizations
✅ Modal dialogs
✅ Copy-to-clipboard
✅ File downloads (trigger backend)
✅ WebSocket connection management
✅ Routing

### BACKEND Responsibilities:
✅ Authentication/authorization
✅ Business logic validation
✅ Database operations (DynamoDB)
✅ GitHub API integration
✅ Repository cloning/snapshotting
✅ Scheduled job execution
✅ Analysis orchestration
✅ Report generation
✅ Email notifications
✅ File storage (S3)
✅ Cost tracking
✅ Real-time event broadcasting
✅ API rate limiting

---

## CLEAN SEPARATION PRINCIPLE

**Frontend focuses on:** User experience, interaction, presentation
**Backend handles:** All critical logic, data persistence, external integrations

This separation ensures:
- Frontend can be rebuilt in any framework without touching backend
- Backend can scale independently
- Security validation happens server-side (never trust client)
- Business logic is centralized and testable
