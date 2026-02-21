# VibeJudge AI — API Specification

> **Version:** 1.0  
> **Date:** February 2026  
> **Author:** Maku Mazakpe / Vibe Coders  
> **Status:** APPROVED  
> **Depends On:** ADR-003 (FastAPI+Mangum), ADR-012 (API-First), Data Model (Deliverable #3)  
> **Base URL:** `https://{api-id}.execute-api.{region}.amazonaws.com/`  
> **Auth:** API Key via `X-API-Key` header (MVP). OAuth2/Cognito for Phase 2.

---

## API Overview

| Group | Endpoints | Description |
|-------|-----------|-------------|
| Health | 1 | Health check and version info |
| Organizers | 3 | Account management |
| Hackathons | 5 | Hackathon CRUD and configuration |
| Submissions | 4 | Submission management |
| Analysis | 3 | Trigger and monitor analysis |
| Results | 4 | Scorecards, leaderboard, costs |

**Total: 20 endpoints**

---

## Authentication (MVP)

Simple API key authentication. Organizer receives API key on registration.

```
Header: X-API-Key: vj_live_01JKXYZ...
```

API keys are hashed (SHA-256) and stored in DynamoDB. Lookup via GSI1 on the Organizer entity.

FastAPI dependency:
```python
async def verify_api_key(x_api_key: str = Header(...)) -> Organizer:
    key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()
    organizer = await db.get_organizer_by_key_hash(key_hash)
    if not organizer:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return organizer
```

---

## 1. Health

### GET /health

No authentication required.

**Response 200:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "service": "vibejudge-api",
  "timestamp": "2026-02-13T12:00:00Z",
  "dependencies": {
    "dynamodb": "healthy",
    "bedrock": "healthy"
  }
}
```

---

## 2. Organizers

### POST /organizers

Create a new organizer account. Returns API key (shown ONCE).

**Request Body:**
```json
{
  "email": "organizer@example.com",
  "name": "Jane Smith",
  "organization": "TechHack Inc"
}
```

**Response 201:**
```json
{
  "org_id": "01JKXYZ1234567890ABCDE",
  "email": "organizer@example.com",
  "name": "Jane Smith",
  "organization": "TechHack Inc",
  "tier": "free",
  "api_key": "vj_live_01JKXYZ...",
  "created_at": "2026-02-13T12:00:00Z",
  "message": "Store your API key securely. It cannot be retrieved again."
}
```

**Errors:**
- 409: Email already registered
- 422: Validation error

---

### GET /organizers/me

Get current organizer profile (authenticated).

**Response 200:**
```json
{
  "org_id": "01JKXYZ1234567890ABCDE",
  "email": "organizer@example.com",
  "name": "Jane Smith",
  "organization": "TechHack Inc",
  "tier": "free",
  "hackathon_count": 3,
  "created_at": "2026-02-13T12:00:00Z"
}
```

---

### PUT /organizers/me

Update organizer profile.

**Request Body:**
```json
{
  "name": "Jane Doe",
  "organization": "NewCorp"
}
```

**Response 200:** Updated organizer object.

---

## 3. Hackathons

### POST /hackathons

Create a new hackathon.

**Request Body:**
```json
{
  "name": "AWS Bedrock Builders 2026",
  "description": "Build innovative apps using Amazon Bedrock",
  "start_date": "2026-03-01T00:00:00Z",
  "end_date": "2026-03-02T23:59:59Z",
  "rubric": {
    "template": "aws_cloud_challenge",
    "custom_weights": null
  },
  "agents_enabled": ["bug_hunter", "performance", "innovation", "ai_detection"],
  "ai_policy_mode": "ai_assisted",
  "ai_policy_custom_rules": null,
  "budget_limit_usd": 20.00
}
```

**rubric options:**
- `{"template": "standard"}` — Use default rubric
- `{"template": "aws_cloud_challenge"}` — AWS-specific
- `{"template": "ai_ml_hackathon"}` — AI/ML focused
- `{"template": "security_challenge"}` — Security focused
- `{"template": "custom", "custom_weights": {"code_quality": 0.30, ...}}` — Custom weights

**Response 201:**
```json
{
  "hack_id": "01JKXYZ9876543210FGHIJ",
  "org_id": "01JKXYZ1234567890ABCDE",
  "name": "AWS Bedrock Builders 2026",
  "status": "draft",
  "rubric": {
    "name": "AWS Cloud Challenge",
    "version": "1.0",
    "max_score": 100,
    "dimensions": [
      {"name": "code_quality", "weight": 0.20, "agent": "bug_hunter"},
      {"name": "architecture", "weight": 0.30, "agent": "performance"},
      {"name": "innovation", "weight": 0.35, "agent": "innovation"},
      {"name": "authenticity", "weight": 0.15, "agent": "ai_detection"}
    ]
  },
  "agents_enabled": ["bug_hunter", "performance", "innovation", "ai_detection"],
  "ai_policy_mode": "ai_assisted",
  "budget_limit_usd": 20.00,
  "submission_count": 0,
  "created_at": "2026-02-13T12:00:00Z"
}
```

**Tier Limits:**
- Free: 3 hackathons max, 50 submissions per hackathon, 2 agents (bug_hunter + innovation)
- Premium: Unlimited hackathons, unlimited submissions, all 4 agents
- Enterprise: Everything + custom agents + API access

**Errors:**
- 403: Tier limit exceeded
- 422: Invalid rubric weights (must sum to 1.0), invalid agent names

---

### GET /hackathons

List all hackathons for current organizer.

**Query Params:**
- `status` (optional): Filter by status (draft, configured, analyzing, completed, archived)
- `limit` (optional, default 20, max 100)
- `offset` (optional, default 0)

**Response 200:**
```json
{
  "hackathons": [
    {
      "hack_id": "01JKXYZ9876543210FGHIJ",
      "name": "AWS Bedrock Builders 2026",
      "status": "completed",
      "submission_count": 47,
      "created_at": "2026-02-13T12:00:00Z"
    }
  ],
  "total": 3,
  "limit": 20,
  "offset": 0
}
```

---

### GET /hackathons/{hack_id}

Get full hackathon details.

**Response 200:** Full HackathonDetail object (see Data Model entity 4.3).

**Errors:**
- 404: Hackathon not found
- 403: Not your hackathon

---

### PUT /hackathons/{hack_id}

Update hackathon configuration. Only allowed when status is `draft` or `configured`.

**Request Body:** Same as POST, all fields optional (partial update).

**Errors:**
- 409: Cannot modify hackathon in status `analyzing` or `completed`

---

### DELETE /hackathons/{hack_id}

Delete hackathon and all associated data. Only allowed for `draft` status.

**Response 204:** No content.

**Errors:**
- 409: Cannot delete hackathon with submissions (must archive instead)

---

## 4. Submissions

### POST /hackathons/{hack_id}/submissions

Add submission(s) to a hackathon. Accepts single or batch.

**Request Body (single):**
```json
{
  "team_name": "Team Nova",
  "repo_url": "https://github.com/team-nova/bedrock-app"
}
```

**Request Body (batch):**
```json
{
  "submissions": [
    {"team_name": "Team Nova", "repo_url": "https://github.com/team-nova/bedrock-app"},
    {"team_name": "Team Lambda", "repo_url": "https://github.com/team-lambda/serverless-ai"},
    {"team_name": "Team Dynamo", "repo_url": "https://github.com/team-dynamo/rag-pipeline"}
  ]
}
```

**Response 201:**
```json
{
  "submissions_created": 3,
  "submissions": [
    {
      "sub_id": "01JKXYZAAA...",
      "team_name": "Team Nova",
      "repo_url": "https://github.com/team-nova/bedrock-app",
      "status": "pending"
    }
  ]
}
```

**Validation:**
- repo_url must be valid GitHub URL format
- repo_url must be unique within hackathon
- team_name must be unique within hackathon
- Total submissions must not exceed tier limit

**Errors:**
- 409: Duplicate repo URL or team name
- 403: Submission limit exceeded for tier
- 422: Invalid repo URL format

---

### GET /hackathons/{hack_id}/submissions

List all submissions for a hackathon.

**Query Params:**
- `status` (optional): pending, cloning, analyzing, completed, failed
- `sort_by` (optional): created_at (default), overall_score, team_name
- `sort_order` (optional): asc, desc (default)
- `limit` (optional, default 50, max 500)
- `offset` (optional, default 0)

**Response 200:**
```json
{
  "submissions": [
    {
      "sub_id": "01JKXYZAAA...",
      "team_name": "Team Nova",
      "repo_url": "https://github.com/team-nova/bedrock-app",
      "status": "completed",
      "overall_score": 76.23,
      "rank": 1,
      "primary_language": "Python",
      "commit_count": 47,
      "created_at": "2026-02-13T12:00:00Z"
    }
  ],
  "total": 47,
  "limit": 50,
  "offset": 0
}
```

---

### GET /hackathons/{hack_id}/submissions/{sub_id}

Get full submission details including repo metadata.

**Response 200:** Full Submission object (see Data Model entity 4.4).

---

### DELETE /hackathons/{hack_id}/submissions/{sub_id}

Remove a submission. Only if status is `pending`.

**Response 204:** No content.

---

## 5. Analysis

### POST /hackathons/{hack_id}/analyze

Trigger batch analysis for all pending submissions. This is the main action endpoint.

**Request Body (optional):**
```json
{
  "submission_ids": ["01JKXYZAAA...", "01JKXYZBBB..."],
  "force_reanalysis": false
}
```

- If `submission_ids` omitted: analyze ALL pending submissions
- If `force_reanalysis: true`: re-analyze even completed submissions
- Returns cost estimate before starting

**Response 202 (Accepted):**
```json
{
  "job_id": "01JKXYZJOB...",
  "hack_id": "01JKXYZ9876543210FGHIJ",
  "status": "queued",
  "total_submissions": 47,
  "estimated_cost_usd": 1.08,
  "estimated_duration_minutes": 15,
  "message": "Analysis job queued. Poll GET /hackathons/{hack_id}/jobs/{job_id} for progress."
}
```

**Pre-flight checks (before starting):**
1. Hackathon has at least 1 pending submission
2. Budget limit not already exceeded
3. Estimated cost within budget_limit_usd (if set)
4. All required agents are available (Bedrock model access)

**Errors:**
- 400: No pending submissions
- 402: Estimated cost exceeds budget limit
- 409: Analysis already running for this hackathon
- 503: Bedrock models unavailable

---

### GET /hackathons/{hack_id}/jobs/{job_id}

Poll analysis job progress.

**Response 200:**
```json
{
  "job_id": "01JKXYZJOB...",
  "hack_id": "01JKXYZ9876543210FGHIJ",
  "status": "running",
  "total_submissions": 47,
  "completed_submissions": 23,
  "failed_submissions": 1,
  "progress_percent": 48.9,
  "current_cost_usd": 0.53,
  "started_at": "2026-02-13T12:05:00Z",
  "estimated_completion": "2026-02-13T12:20:00Z",
  "errors": [
    {
      "sub_id": "01JKXYZFAIL...",
      "team_name": "Team Error",
      "error": "Repository not accessible (404)"
    }
  ]
}
```

---

### POST /hackathons/{hack_id}/estimate

Get cost estimate WITHOUT triggering analysis.

**Request Body (optional):**
```json
{
  "submission_ids": ["01JKXYZAAA..."]
}
```

**Response 200:**
```json
{
  "hack_id": "01JKXYZ9876543210FGHIJ",
  "submissions_to_analyze": 47,
  "agents_enabled": ["bug_hunter", "performance", "innovation", "ai_detection"],
  "estimated_cost": {
    "total_usd": 1.08,
    "per_submission_usd": 0.023,
    "by_agent": {
      "bug_hunter": 0.094,
      "performance": 0.094,
      "innovation": 0.846,
      "ai_detection": 0.047
    },
    "by_model": {
      "amazon.nova-lite-v1:0": 0.188,
      "anthropic.claude-sonnet-4-20250514": 0.846,
      "amazon.nova-micro-v1:0": 0.047
    }
  },
  "estimated_duration_minutes": 15,
  "budget_limit_usd": 20.00,
  "budget_remaining_usd": 18.92,
  "within_budget": true
}
```

---

## 6. Results

### GET /hackathons/{hack_id}/leaderboard

Get ranked submissions with scores.

**Query Params:**
- `limit` (optional, default 50, max 500)
- `offset` (optional, default 0)

**Response 200:**
```json
{
  "hackathon": "AWS Bedrock Builders 2026",
  "total_submissions": 47,
  "analyzed": 46,
  "failed": 1,
  "leaderboard": [
    {
      "rank": 1,
      "sub_id": "01JKXYZAAA...",
      "team_name": "Team Nova",
      "overall_score": 82.45,
      "confidence": 0.89,
      "recommendation": "strong_contender",
      "dimension_scores": {
        "code_quality": {"raw": 7.2, "weighted": 1.44},
        "architecture": {"raw": 8.5, "weighted": 2.55},
        "innovation": {"raw": 9.1, "weighted": 3.19},
        "authenticity": {"raw": 8.0, "weighted": 1.20}
      }
    },
    {
      "rank": 2,
      "sub_id": "01JKXYZBBB...",
      "team_name": "Team Lambda",
      "overall_score": 76.23
    }
  ]
}
```

---

### GET /hackathons/{hack_id}/submissions/{sub_id}/scorecard

Get full scorecard for a submission — all agent results.

**Response 200:**
```json
{
  "sub_id": "01JKXYZAAA...",
  "team_name": "Team Nova",
  "repo_url": "https://github.com/team-nova/bedrock-app",
  "overall_score": 82.45,
  "confidence": 0.89,
  "recommendation": "strong_contender",
  "weighted_scores": {
    "code_quality": {"raw": 7.2, "weight": 0.20, "weighted": 1.44},
    "architecture": {"raw": 8.5, "weight": 0.30, "weighted": 2.55},
    "innovation": {"raw": 9.1, "weight": 0.35, "weighted": 3.19},
    "authenticity": {"raw": 8.0, "weight": 0.15, "weighted": 1.20}
  },
  "agents": {
    "bug_hunter": {
      "overall_score": 7.2,
      "confidence": 0.92,
      "scores": {
        "code_quality": 7.5,
        "security": 6.0,
        "test_coverage": 8.0,
        "error_handling": 7.0,
        "dependency_hygiene": 8.5
      },
      "summary": "Solid codebase with good structure...",
      "strengths": ["Well-organized modules", "Comprehensive test suite"],
      "improvements": ["SQL injection in user endpoint", "Missing rate limiting"],
      "evidence_count": 5,
      "model_used": "amazon.nova-lite-v1:0",
      "prompt_version": "1.0"
    },
    "performance": { "..." : "..." },
    "innovation": { "..." : "..." },
    "ai_detection": {
      "overall_score": 8.0,
      "ai_usage_estimate": "moderate",
      "development_pattern": "ai_assisted_iterative",
      "..." : "..."
    }
  },
  "repo_meta": {
    "primary_language": "Python",
    "commit_count": 47,
    "development_duration_hours": 38.75,
    "has_tests": true,
    "has_ci": true
  },
  "cost": {
    "total_usd": 0.023,
    "by_agent": {
      "bug_hunter": 0.002,
      "performance": 0.002,
      "innovation": 0.018,
      "ai_detection": 0.001
    }
  },
  "analyzed_at": "2026-02-13T12:15:00Z"
}
```

---

### GET /hackathons/{hack_id}/submissions/{sub_id}/evidence

Get detailed evidence/findings for a submission (all agents combined).

**Query Params:**
- `agent` (optional): Filter by agent name
- `severity` (optional): critical, high, medium, low, info
- `category` (optional): security, quality, architecture, etc.
- `verified_only` (optional, default false): Only return verified evidence

**Response 200:**
```json
{
  "sub_id": "01JKXYZAAA...",
  "total_findings": 12,
  "findings": [
    {
      "agent": "bug_hunter",
      "finding": "SQL injection vulnerability in user query",
      "file": "src/api/users.py",
      "line": 42,
      "commit": "a1b2c3d",
      "severity": "critical",
      "category": "security",
      "verified": true
    },
    {
      "agent": "innovation",
      "finding": "Creative use of Bedrock multi-model routing",
      "file": "src/ai/router.py",
      "line": 15,
      "severity": "info",
      "category": "novelty",
      "verified": true
    }
  ]
}
```

---

### GET /hackathons/{hack_id}/costs

Get cost analytics for a hackathon.

**Response 200:**
```json
{
  "hack_id": "01JKXYZ9876543210FGHIJ",
  "total_cost_usd": 1.06,
  "submissions_analyzed": 46,
  "avg_cost_per_submission": 0.023,
  "budget_limit_usd": 20.00,
  "budget_used_percent": 5.3,
  "by_agent": {
    "bug_hunter": {"cost_usd": 0.092, "percent": 8.7, "total_tokens": 147200},
    "performance": {"cost_usd": 0.092, "percent": 8.7, "total_tokens": 138000},
    "innovation": {"cost_usd": 0.828, "percent": 78.1, "total_tokens": 243800},
    "ai_detection": {"cost_usd": 0.048, "percent": 4.5, "total_tokens": 271400}
  },
  "by_model": {
    "amazon.nova-lite-v1:0": {"cost_usd": 0.184, "percent": 17.4},
    "anthropic.claude-sonnet-4-20250514": {"cost_usd": 0.828, "percent": 78.1},
    "amazon.nova-micro-v1:0": {"cost_usd": 0.048, "percent": 4.5}
  },
  "optimization_tips": [
    "InnovationScorer uses 78% of budget. Consider Nova Pro for 30% savings.",
    "46 of 47 submissions analyzed. 1 failed (repo inaccessible)."
  ]
}
```

---

## Error Response Format

All errors follow consistent format:

```json
{
  "error": {
    "code": "SUBMISSION_LIMIT_EXCEEDED",
    "message": "Free tier allows 50 submissions per hackathon. Current: 50.",
    "details": {
      "tier": "free",
      "limit": 50,
      "current": 50,
      "upgrade_url": "https://vibejudge.ai/pricing"
    }
  }
}
```

### Error Code Catalog

| HTTP | Code | When |
|------|------|------|
| 400 | INVALID_REQUEST | Malformed request body |
| 400 | NO_PENDING_SUBMISSIONS | Analyze called with nothing to analyze |
| 401 | INVALID_API_KEY | Missing or invalid X-API-Key |
| 402 | BUDGET_EXCEEDED | Analysis cost would exceed budget_limit_usd |
| 403 | TIER_LIMIT | Feature not available on current tier |
| 403 | NOT_OWNER | Accessing another organizer's resource |
| 404 | NOT_FOUND | Resource doesn't exist |
| 409 | DUPLICATE | Duplicate email, repo URL, or team name |
| 409 | INVALID_STATUS | Action not allowed in current status |
| 409 | ANALYSIS_IN_PROGRESS | Another analysis job already running |
| 422 | VALIDATION_ERROR | Pydantic validation failure |
| 429 | RATE_LIMITED | Too many requests |
| 500 | INTERNAL_ERROR | Unexpected server error |
| 502 | BEDROCK_ERROR | Bedrock API returned error |
| 503 | SERVICE_UNAVAILABLE | Bedrock models temporarily unavailable |

---

## Rate Limits (MVP)

| Endpoint Group | Limit | Window |
|----------------|-------|--------|
| Read endpoints (GET) | 100 req | per minute |
| Write endpoints (POST/PUT/DELETE) | 20 req | per minute |
| Analysis trigger (POST /analyze) | 5 req | per hour |
| Cost estimate (POST /estimate) | 20 req | per hour |

Implemented via API Gateway throttling, not application-level.

---

## FastAPI Router Structure

```python
# src/api/main.py
app = FastAPI(
    title="VibeJudge AI API",
    description="AI-powered hackathon judging platform",
    version="1.0.0",
)

# src/api/routes/health.py      → GET /health
# src/api/routes/organizers.py   → POST, GET, PUT /organizers
# src/api/routes/hackathons.py   → CRUD /hackathons
# src/api/routes/submissions.py  → CRUD /hackathons/{id}/submissions
# src/api/routes/analysis.py     → POST /analyze, GET /jobs, POST /estimate
# src/api/routes/results.py      → GET /leaderboard, /scorecard, /evidence, /costs
```

---

*End of API Specification v1.0*
*Next deliverable: #6 — SAM Template (IaC)*
