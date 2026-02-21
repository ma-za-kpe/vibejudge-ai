# VibeJudge AI — MVP Specification

> **Version:** 1.0  
> **Created:** February 21, 2026  
> **Status:** DRAFT  
> **Competition:** AWS 10,000 AIdeas (Semi-Finalist)  
> **Deadline:** March 6, 2026

---

## Executive Summary

VibeJudge AI is an automated hackathon judging platform using 4 specialized AI agents on Amazon Bedrock to evaluate code submissions. The system analyzes GitHub repositories through multi-agent collaboration, providing evidence-based scoring with file:line citations, cost transparency, and comprehensive feedback in minutes instead of days.

**Core Innovation:** Multi-agent architecture with specialized judges (BugHunter, PerformanceAnalyzer, InnovationScorer, AIDetection) coordinated through custom orchestration, delivering transparent token-level cost tracking and validated evidence to prevent AI hallucinations.

**Target:** Hackathon organizers managing 50-500 team competitions who need fair, scalable, unbiased judging with detailed feedback.

---

## Table of Contents

1. [User Stories & Acceptance Criteria](#1-user-stories--acceptance-criteria)
2. [Technical Architecture](#2-technical-architecture)
3. [Data Model](#3-data-model)
4. [API Endpoints](#4-api-endpoints)
5. [AI Agents Design](#5-ai-agents-design)
6. [Implementation Tasks](#6-implementation-tasks)
7. [Task Dependencies](#7-task-dependencies)
8. [Testing Strategy](#8-testing-strategy)
9. [Success Metrics](#9-success-metrics)
10. [Constraints & Risks](#10-constraints--risks)

---

## 1. User Stories & Acceptance Criteria

### Epic 1: Organizer Account Management

#### US-1.1: Create Organizer Account
**As a** hackathon organizer  
**When** I register for VibeJudge AI  
**If** I provide valid email and name  
**Then** the system creates my account and generates a unique API key  
**And** I can use this API key to authenticate all subsequent requests

**Acceptance Criteria:**
- Email validation (RFC 5322 compliant)
- API key format: `vj_live_<ULID>` (32 chars)
- API key shown ONCE on creation, SHA-256 hashed in storage
- Response includes org_id, tier (default: free), created_at
- Duplicate email returns 409 Conflict

**EARS Notation:**
```
WHEN organizer submits POST /organizers with {email, name, organization}
IF email is valid AND not already registered
THEN system SHALL create organizer record with tier=free
AND system SHALL generate API key with prefix vj_live_
AND system SHALL return 201 with api_key in response body
AND system SHALL hash api_key (SHA-256) before DynamoDB storage
```


#### US-1.2: Authenticate with API Key
**As a** registered organizer  
**When** I make API requests  
**If** I include valid API key in X-API-Key header  
**Then** the system authenticates me and allows access to my resources

**Acceptance Criteria:**
- Header format: `X-API-Key: vj_live_<ULID>`
- Invalid key returns 401 Unauthorized
- Key lookup via GSI1 on hashed value
- Authentication middleware applied to all protected routes
- Rate limiting: 100 reads/min, 20 writes/min

---

### Epic 2: Hackathon Configuration

#### US-2.1: Create Hackathon with Custom Rubric
**As an** organizer  
**When** I create a hackathon  
**If** I provide name, rubric, and agent selection  
**Then** the system validates the configuration and creates the hackathon

**Acceptance Criteria:**
- Rubric dimensions must reference enabled agents
- Dimension weights must sum to 1.0 (±0.001 tolerance)
- Agents: bug_hunter, performance, innovation, ai_detection
- AI policy modes: full_vibe, ai_assisted, traditional, custom
- Free tier: max 3 hackathons, 50 submissions, 2 agents only
- Premium tier: unlimited hackathons/submissions, all 4 agents
- Budget limit optional (0.01-10000.0 USD)

**EARS Notation:**
```
WHEN organizer submits POST /hackathons with rubric config
IF rubric.dimensions weights sum to 1.0
AND all dimension.agent values are in agents_enabled list
AND tier limits not exceeded
THEN system SHALL create hackathon with status=draft
AND system SHALL store rubric in HackathonDetail entity
AND system SHALL return 201 with hack_id
```

#### US-2.2: Update Hackathon Configuration
**As an** organizer  
**When** I update a hackathon  
**If** status is draft or configured  
**Then** the system applies the changes

**Acceptance Criteria:**
- Cannot modify if status is analyzing or completed
- Partial updates supported (PATCH semantics)
- Rubric changes re-validated
- Returns 409 if status prevents modification


---

### Epic 3: Submission Management

#### US-3.1: Add Submissions (Batch)
**As an** organizer  
**When** I submit a list of team repos  
**If** all repo URLs are valid GitHub URLs  
**Then** the system creates submission records with status=pending

**Acceptance Criteria:**
- Repo URL format: `https://github.com/{owner}/{repo}`
- Batch size: 1-500 submissions per request
- Duplicate repo URL within hackathon returns 409
- Duplicate team name within hackathon returns 409
- Tier submission limits enforced
- Response includes created submission IDs

**EARS Notation:**
```
WHEN organizer submits POST /hackathons/{id}/submissions with repo list
IF all repo_url match GitHub URL pattern
AND no duplicates within hackathon
AND tier submission limit not exceeded
THEN system SHALL create submission records with status=pending
AND system SHALL increment hackathon.submission_count
AND system SHALL return 201 with submission IDs
```

#### US-3.2: List Submissions with Filtering
**As an** organizer  
**When** I request submission list  
**If** I provide optional filters (status, sort)  
**Then** the system returns filtered, sorted submissions

**Acceptance Criteria:**
- Filter by status: pending, cloning, analyzing, completed, failed
- Sort by: created_at (default), overall_score, team_name
- Sort order: asc, desc (default)
- Pagination: limit (default 50, max 500), offset
- Response includes total count

---

### Epic 4: Analysis Execution

#### US-4.1: Trigger Batch Analysis with Cost Estimate
**As an** organizer  
**When** I trigger analysis for a hackathon  
**If** there are pending submissions  
**Then** the system provides cost estimate and queues analysis job

**Acceptance Criteria:**
- Pre-flight checks: ≥1 pending submission, budget not exceeded
- Cost estimate includes: total, per-submission, by-agent, by-model
- Estimated duration based on submission count
- Budget validation if budget_limit_usd set
- Returns 402 if estimated cost exceeds budget
- Returns 409 if analysis already running
- Job status: queued → running → completed/failed

**EARS Notation:**
```
WHEN organizer submits POST /hackathons/{id}/analyze
IF hackathon has pending submissions
AND estimated_cost <= budget_limit_usd (if set)
AND no active analysis job exists
THEN system SHALL create AnalysisJob with status=queued
AND system SHALL invoke Analyzer Lambda asynchronously
AND system SHALL return 202 with job_id and cost estimate
```


#### US-4.2: Monitor Analysis Progress
**As an** organizer  
**When** I poll analysis job status  
**If** job is running  
**Then** the system returns current progress and cost

**Acceptance Criteria:**
- Progress: total, completed, failed, remaining, percent_complete
- Current submission being processed
- Cost accumulated so far
- Estimated completion time
- Error log for failed submissions
- Poll interval recommendation: 10-30 seconds

#### US-4.3: Analyze Single Repository
**As the** analysis orchestrator  
**When** processing a submission  
**If** repo is accessible  
**Then** the system clones, extracts data, runs agents, validates evidence

**Acceptance Criteria:**
- Clone to Lambda /tmp (2GB ephemeral storage)
- Timeout: 120s for clone, 900s total per submission
- Fallback to shallow clone (depth=100) if full clone fails
- Extract: commits (max 100), file tree, source files (max 25), README
- Run 4 agents sequentially with configured models
- Validate evidence: file paths exist, line numbers valid
- Record token usage and cost per agent
- Cleanup /tmp after analysis
- Update submission status: pending → cloning → analyzing → completed/failed

**EARS Notation:**
```
WHEN Analyzer Lambda processes submission
IF repo clone succeeds within 120s timeout
THEN system SHALL extract git history (max 100 commits)
AND system SHALL extract source files (max 25, prioritized)
AND system SHALL extract README (max 12KB)
AND system SHALL fetch GitHub Actions data via REST API
AND system SHALL build RepoData object
AND system SHALL invoke each enabled agent with RepoData
AND system SHALL validate evidence against file tree
AND system SHALL record CostRecord per agent
AND system SHALL aggregate scores using rubric weights
AND system SHALL write AgentScore, SubmissionSummary, CostRecord to DynamoDB
AND system SHALL update submission status to completed
AND system SHALL cleanup /tmp clone directory
```

---

### Epic 5: Results & Leaderboard

#### US-5.1: View Leaderboard
**As an** organizer  
**When** I request hackathon leaderboard  
**If** analysis is complete  
**Then** the system returns ranked submissions with scores

**Acceptance Criteria:**
- Sorted by overall_score descending
- Includes: rank, team_name, overall_score, dimension_scores
- Recommendation: strong_contender, solid_submission, needs_improvement, concerns_flagged
- Pagination: limit (default 50, max 500)
- Statistics: mean, median, std_dev, score distribution


#### US-5.2: View Detailed Scorecard
**As an** organizer  
**When** I request submission scorecard  
**If** analysis is complete  
**Then** the system returns all agent results with evidence

**Acceptance Criteria:**
- Overall score and confidence
- Per-agent scores with sub-dimensions
- Evidence list with file:line citations
- Verification status per evidence item
- Strengths and improvements lists
- Repo metadata (commits, languages, duration)
- Cost breakdown by agent
- Model and prompt version used

#### US-5.3: View Evidence Details
**As an** organizer  
**When** I request evidence for a submission  
**If** I provide optional filters  
**Then** the system returns filtered evidence findings

**Acceptance Criteria:**
- Filter by: agent, severity, category, verified_only
- Severity: critical, high, medium, low, info
- Each finding includes: agent, description, file, line, commit, severity
- Verified flag indicates if file/line exists in repo
- Unverified evidence flagged for manual review

---

### Epic 6: Cost Tracking & Analytics

#### US-6.1: View Hackathon Cost Analytics
**As an** organizer  
**When** I request cost analytics  
**If** analysis has run  
**Then** the system returns detailed cost breakdown

**Acceptance Criteria:**
- Total cost, submissions analyzed, avg per submission
- Cost by agent (amount, percentage, token count)
- Cost by model (amount, percentage)
- Budget utilization if budget_limit_usd set
- Optimization tips based on usage patterns

**EARS Notation:**
```
WHEN organizer requests GET /hackathons/{id}/costs
IF hackathon has completed analysis
THEN system SHALL aggregate CostRecord entities
AND system SHALL calculate total_cost_usd
AND system SHALL group by agent_name and model_id
AND system SHALL calculate budget utilization percentage
AND system SHALL return cost breakdown with optimization tips
```

#### US-6.2: Get Cost Estimate Before Analysis
**As an** organizer  
**When** I request cost estimate  
**If** I specify submission IDs or use all pending  
**Then** the system calculates estimated cost without running analysis

**Acceptance Criteria:**
- Estimate based on: submission count, agents enabled, avg tokens per agent
- Range: low, expected, high (accounts for repo size variance)
- Estimated duration in minutes
- Budget check if budget_limit_usd set
- No charges incurred for estimate

---

## 2. Technical Architecture

### 2.1 System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         VibeJudge AI                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐         ┌──────────────┐                     │
│  │   Organizer   │────────▶│  API Gateway │                     │
│  │   (Client)    │         │  (HTTP API)  │                     │
│  └──────────────┘         └──────┬───────┘                     │
│                                   │                             │
│                                   ▼                             │
│                          ┌────────────────┐                     │
│                          │  API Lambda    │                     │
│                          │  (FastAPI +    │                     │
│                          │   Mangum)      │                     │
│                          └────────┬───────┘                     │
│                                   │                             │
│                    ┌──────────────┼──────────────┐              │
│                    ▼              ▼              ▼              │
│            ┌──────────────┐ ┌──────────┐ ┌──────────────┐      │
│            │  DynamoDB     │ │ Analyzer │ │   Bedrock    │      │
│            │  (Single      │ │ Lambda   │ │  (Converse   │      │
│            │   Table)      │ │ (Async)  │ │   API)       │      │
│            └──────────────┘ └─────┬────┘ └──────────────┘      │
│                                   │                             │
│                    ┌──────────────┼──────────────┐              │
│                    ▼              ▼              ▼              │
│            ┌──────────────┐ ┌──────────┐ ┌──────────────┐      │
│            │  GitPython    │ │  httpx   │ │  4 AI Agents │      │
│            │  (Clone to    │ │ (GitHub  │ │  - BugHunter │      │
│            │   /tmp)       │ │  Actions)│ │  - Perf      │      │
│            └──────────────┘ └──────────┘ │  - Innovation│      │
│                                           │  - AIDetect  │      │
│                                           └──────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```


### 2.2 AWS Services Configuration

| Service | Configuration | Free Tier | Our Usage | Rationale |
|---------|--------------|-----------|-----------|-----------|
| **Lambda** | API: 1024MB, 30s timeout<br>Analyzer: 2048MB, 900s timeout | 1M requests/mo<br>400K GB-seconds | ~10K requests/mo<br>~50K GB-seconds | API needs moderate memory<br>Analyzer needs more for git ops |
| **DynamoDB** | Provisioned: 5 RCU / 5 WCU<br>Table Class: STANDARD<br>2 GSIs | 25 RCU/WCU total<br>25 GB storage | 15 RCU/WCU<br>~50 MB | Single-table design<br>CRITICAL: On-demand NOT free |
| **API Gateway** | HTTP API (NOT REST API) | 1M calls/mo (12mo) | ~10K calls/mo | 71% cheaper than REST API |
| **S3** | Standard storage<br>Lifecycle: 30d deletion | 5GB (12mo) | <100 MB | Temp storage for large responses |
| **CloudWatch** | Logs: 14d retention<br>Metrics: 10 alarms | 5GB logs<br>10 alarms | ~500 MB logs<br>5 alarms | Structured JSON logs |
| **Bedrock** | Converse API<br>Models: Nova Micro/Lite, Claude Sonnet | NONE (pay per token) | ~$0.023/submission | Core AI functionality |

### 2.3 Technology Stack

**Backend:**
- Python 3.12 (Lambda runtime)
- FastAPI 0.109+ (ASGI framework)
- Mangum 0.17+ (Lambda adapter)
- Pydantic v2 (validation)

**AI Platform:**
- Amazon Bedrock Converse API
- Models: Nova Micro ($0.035/$0.14 per 1M tokens), Nova Lite ($0.06/$0.24), Claude Sonnet 4 ($3/$15)

**Data & Storage:**
- DynamoDB (single-table design)
- S3 (optional large response storage)

**Git & GitHub:**
- GitPython 3.1.40+ (git operations)
- httpx 0.25+ (GitHub REST API)

**Infrastructure:**
- AWS SAM (IaC)
- CloudWatch (observability)

**Development:**
- pytest (testing)
- moto (AWS mocking)
- ruff (linting)
- mypy (type checking)

### 2.4 Agent Model Assignments

| Agent | Model | Temperature | Max Tokens | Cost/Submission | Rationale |
|-------|-------|-------------|------------|-----------------|-----------|
| BugHunter | Nova Lite | 0.1 | 2048 | ~$0.002 | Deterministic code analysis |
| Performance | Nova Lite | 0.1 | 2048 | ~$0.002 | Deterministic architecture eval |
| Innovation | Claude Sonnet 4 | 0.3 | 3000 | ~$0.018 | Deep reasoning for creativity |
| AIDetection | Nova Micro | 0.0 | 1500 | ~$0.001 | Pattern matching only |
| **Total** | | | | **~$0.023** | 78% cost from Innovation agent |

---

## 3. Data Model

### 3.1 DynamoDB Single-Table Design

**Table:** VibeJudgeTable  
**Billing:** PROVISIONED (5 RCU / 5 WCU)  
**Keys:** PK (partition), SK (sort)  
**GSIs:** GSI1 (cross-entity lookup), GSI2 (status+time queries)


### 3.2 Entity Catalog

| Entity | PK | SK | Description |
|--------|----|----|-------------|
| Organizer | ORG#{org_id} | PROFILE | Account info, API key hash |
| Hackathon | ORG#{org_id} | HACK#{hack_id} | Hackathon listing |
| HackathonDetail | HACK#{hack_id} | META | Full config, rubric |
| Submission | HACK#{hack_id} | SUB#{sub_id} | Repo submission |
| AgentScore | SUB#{sub_id} | SCORE#{agent} | Individual agent result |
| SubmissionSummary | SUB#{sub_id} | SUMMARY | Aggregated scorecard |
| CostRecord | SUB#{sub_id} | COST#{agent} | Token/cost per agent |
| HackathonCost | HACK#{hack_id} | COST#SUMMARY | Aggregated hackathon cost |
| AnalysisJob | HACK#{hack_id} | JOB#{job_id} | Batch job tracking |

### 3.3 Key Access Patterns

| Pattern | Operation | Keys | Index |
|---------|-----------|------|-------|
| Get organizer by ID | GetItem | PK=ORG#{id}, SK=PROFILE | Table |
| Get organizer by email | Query | GSI1PK=EMAIL#{email} | GSI1 |
| List hackathons for org | Query | PK=ORG#{id}, SK begins_with HACK# | Table |
| Get hackathon config | GetItem | PK=HACK#{id}, SK=META | Table |
| List submissions | Query | PK=HACK#{id}, SK begins_with SUB# | Table |
| Get submission scores | Query | PK=SUB#{id}, SK begins_with SCORE# | Table |
| Get submission costs | Query | PK=SUB#{id}, SK begins_with COST# | Table |
| Get leaderboard | Query + sort | PK=HACK#{id}, SK begins_with SUB# | Table (app-side sort) |
| List jobs by status | Query | GSI2PK=JOB_STATUS#{status} | GSI2 |

---

## 4. API Endpoints

### 4.1 Endpoint Summary

| Group | Endpoints | Auth | Description |
|-------|-----------|------|-------------|
| Health | 1 | No | Health check |
| Organizers | 3 | Mixed | Account management |
| Hackathons | 5 | Yes | Hackathon CRUD |
| Submissions | 4 | Yes | Submission management |
| Analysis | 3 | Yes | Trigger & monitor |
| Results | 4 | Yes | Scorecards & leaderboard |

**Total: 20 endpoints**

### 4.2 Core Endpoints

```
POST   /organizers                    # Create account, get API key
GET    /organizers/me                 # Get profile
PUT    /organizers/me                 # Update profile

POST   /hackathons                    # Create hackathon
GET    /hackathons                    # List hackathons
GET    /hackathons/{id}               # Get hackathon details
PUT    /hackathons/{id}               # Update hackathon
DELETE /hackathons/{id}               # Delete hackathon (draft only)

POST   /hackathons/{id}/submissions   # Add submissions (batch)
GET    /hackathons/{id}/submissions   # List submissions
GET    /hackathons/{id}/submissions/{sub_id}  # Get submission
DELETE /hackathons/{id}/submissions/{sub_id}  # Delete submission

POST   /hackathons/{id}/analyze       # Trigger analysis
GET    /hackathons/{id}/jobs/{job_id} # Poll job status
POST   /hackathons/{id}/estimate      # Get cost estimate

GET    /hackathons/{id}/leaderboard   # Get ranked submissions
GET    /hackathons/{id}/submissions/{sub_id}/scorecard  # Full scorecard
GET    /hackathons/{id}/submissions/{sub_id}/evidence   # Evidence details
GET    /hackathons/{id}/costs         # Cost analytics
```


---

## 5. AI Agents Design

### 5.1 Agent Architecture

Each agent is a Python class that:
1. Receives system prompt (static, versioned)
2. Receives user message (dynamic RepoData)
3. Calls Bedrock Converse API
4. Parses JSON response
5. Validates evidence against repo files
6. Returns structured score object

### 5.2 Agent Specifications

#### Agent 1: BugHunter
**Model:** amazon.nova-lite-v1:0  
**Purpose:** Code quality, security, testing  
**Dimensions:**
- code_quality (30%): Structure, naming, DRY, readability
- security (30%): Hardcoded secrets, SQL injection, XSS, auth
- test_coverage (15%): Test files present, framework, coverage
- error_handling (15%): Try/catch, validation, logging
- dependency_hygiene (10%): Lock files, versions, .gitignore

**Critical Rules:**
- Hardcoded secrets = CRITICAL severity, flag HARDCODED_SECRETS_DETECTED
- No tests = max score 2.0
- Evidence required for all scores <6.0

#### Agent 2: PerformanceAnalyzer
**Model:** amazon.nova-lite-v1:0  
**Purpose:** Architecture, scalability, design  
**Dimensions:**
- architecture (30%): Separation of concerns, patterns, coupling
- database_design (20%): Schema, ORM, migrations, pooling
- api_design (20%): RESTful, validation, auth, documentation
- scalability (20%): Stateless, caching, async, indexing
- resource_efficiency (10%): Algorithms, memory, batch ops

**GitHub Actions Intelligence:**
- Build time trends (caching, multi-stage)
- CI/CD sophistication (lint → test → build → deploy)
- Deployment strategy (staging, blue-green)

#### Agent 3: InnovationScorer
**Model:** anthropic.claude-sonnet-4-20250514  
**Purpose:** Creativity, novelty, documentation  
**Dimensions:**
- technical_novelty (30%): Novel combinations, creative solutions
- creative_problem_solving (25%): Git history shows iteration
- architecture_elegance (20%): Right-sized, clear domain thinking
- readme_quality (15%): Problem, solution, architecture, setup
- demo_potential (10%): Working deployment, visual appeal

**Scoring Guide:**
- 1-3: Tutorial-level (todo app)
- 4-5: Functional but unoriginal
- 6-7: Interesting twist
- 8-9: Genuinely novel
- 9-10: "Haven't seen this before"

#### Agent 4: AIDetection
**Model:** amazon.nova-micro-v1:0  
**Purpose:** Development authenticity, AI usage patterns  
**Dimensions:**
- commit_authenticity (30%): Timing, size, messages
- development_velocity (20%): Lines/hour (typical: 50-150, AI: 200-500+)
- authorship_consistency (20%): Style variation
- iteration_depth (20%): Bug fixes, refactoring, dead code
- ai_generation_indicators (10%): Perfect structure, comprehensive error handling

**AI Policy Modes:**
- full_vibe: High AI usage = GOOD (score 10)
- traditional: No AI indicators = GOOD (score 10)
- ai_assisted: AI + iteration = GOOD (score 10)


### 5.3 Scoring Aggregation

```python
# Weighted score calculation
overall_score = sum(
    agent_result.overall_score * dimension.weight
    for dimension in rubric.dimensions
) * 10  # Scale 0-10 to 0-100

# Confidence = minimum of all agent confidences
confidence = min(agent.confidence for agent in results)

# Recommendation classification
if overall_score >= 80: "strong_contender"
elif overall_score >= 65: "solid_submission"
elif overall_score >= 45: "needs_improvement"
else: "concerns_flagged"
```

### 5.4 Evidence Validation (Anti-Hallucination)

```python
def validate_evidence(evidence: Evidence, repo_data: RepoData) -> bool:
    """Verify evidence references exist in repo."""
    if evidence.file:
        if evidence.file not in repo_data.file_paths:
            evidence.verified = False
            evidence.error = "File not found in repository"
            return False
    
    if evidence.line:
        file_line_count = repo_data.file_line_counts.get(evidence.file, 0)
        if evidence.line > file_line_count:
            evidence.verified = False
            evidence.error = f"Line {evidence.line} exceeds file length {file_line_count}"
            return False
    
    if evidence.commit:
        if evidence.commit not in repo_data.commit_hashes:
            evidence.verified = False
            evidence.error = "Commit not found in history"
            return False
    
    evidence.verified = True
    return True
```

---

## 6. Implementation Tasks

### Phase 1: Foundation (Week 1)

#### T1.1: Project Setup
**Module:** Root  
**Effort:** 2 hours  
**Dependencies:** None

**Tasks:**
- Create requirements.txt with pinned versions
- Create requirements-dev.txt
- Create pyproject.toml with project metadata
- Create .gitignore (Python, AWS, IDE)
- Create .env.example
- Create Makefile with common commands
- Create README.md with setup instructions

**Acceptance:**
- `make install` installs all dependencies
- `make test` runs pytest (even if no tests yet)
- `make lint` runs ruff and mypy

#### T1.2: Pydantic Models - Common & Enums
**Module:** src/models/common.py  
**Effort:** 3 hours  
**Dependencies:** T1.1

**Tasks:**
- Define all enums (HackathonStatus, SubmissionStatus, AgentName, etc.)
- Create VibeJudgeBase with shared config
- Create TimestampMixin
- Add type hints and docstrings

**Acceptance:**
- All enums importable
- BaseModel config includes populate_by_name, use_enum_values
- mypy passes with no errors


#### T1.3: Pydantic Models - All Entities
**Module:** src/models/*.py  
**Effort:** 8 hours  
**Dependencies:** T1.2

**Tasks:**
- organizer.py: OrganizerCreate, OrganizerResponse, OrganizerRecord
- hackathon.py: RubricDimension, RubricConfig, HackathonCreate, HackathonResponse
- submission.py: SubmissionInput, SubmissionResponse, RepoMeta, WeightedDimensionScore
- scores.py: All agent response models (BugHunterResponse, etc.)
- costs.py: CostRecord, CostEstimate, HackathonCostResponse
- analysis.py: RepoData, SourceFile, CommitInfo, AnalysisJobResponse
- leaderboard.py: LeaderboardEntry, LeaderboardResponse
- errors.py: ErrorDetail, ErrorResponse

**Acceptance:**
- All models have type hints
- Field validators for weights (sum to 1.0), dates, URLs
- Model exports in __init__.py
- pytest tests for validation rules
- mypy passes

#### T1.4: Utilities - Configuration & Logging
**Module:** src/utils/config.py, src/utils/logging.py  
**Effort:** 3 hours  
**Dependencies:** T1.1

**Tasks:**
- config.py: Settings class with pydantic-settings
- Environment variables: TABLE_NAME, BEDROCK_REGION, LOG_LEVEL, etc.
- logging.py: structlog configuration for JSON logs
- Logger factory function

**Acceptance:**
- Settings loaded from environment
- Structured JSON logs to stdout
- Log context includes: timestamp, level, event, request_id

#### T1.5: Utilities - ID Generation & DynamoDB Helper
**Module:** src/utils/id_gen.py, src/utils/dynamo.py  
**Effort:** 4 hours  
**Dependencies:** T1.3

**Tasks:**
- id_gen.py: ULID generation functions
- dynamo.py: DynamoHelper class with query methods
- Methods: get_item, put_item, query, batch_write
- Access pattern helpers (get_hackathon, list_submissions, etc.)

**Acceptance:**
- ULIDs are sortable by time
- DynamoDB helper methods handle pagination
- Error handling for throttling, not found
- Unit tests with moto

#### T1.6: Constants & Model Rates
**Module:** src/constants.py  
**Effort:** 1 hour  
**Dependencies:** None

**Tasks:**
- MODEL_RATES dict with input/output costs per token
- TIER_LIMITS dict (free, premium, enterprise)
- FILE_PRIORITIES for source file selection
- SOURCE_EXTENSIONS, CONFIG_EXTENSIONS
- IGNORE_PATTERNS for git analysis

**Acceptance:**
- All constants documented
- Type hints for all dicts
- Importable from src.constants

---

### Phase 2: Core Infrastructure (Week 1-2)

#### T2.1: SAM Template - DynamoDB
**Module:** template.yaml  
**Effort:** 3 hours  
**Dependencies:** T1.1

**Tasks:**
- Define VibeJudgeTable resource
- BillingMode: PROVISIONED (5 RCU / 5 WCU)
- TableClass: STANDARD
- GSI1 and GSI2 definitions
- TTL configuration on expires_at
- Outputs: TableName, TableArn

**Acceptance:**
- `sam validate` passes
- Table creates with correct capacity
- GSIs have correct projections
- Free tier compliant


#### T2.2: SAM Template - Lambda Functions
**Module:** template.yaml  
**Effort:** 4 hours  
**Dependencies:** T2.1

**Tasks:**
- ApiFunction: Runtime python3.12, 1024MB, 30s timeout
- AnalyzerFunction: Runtime python3.12, 2048MB, 900s timeout, 2GB ephemeral storage
- IAM roles with least privilege
- Environment variables from Parameters
- Lambda layers for shared dependencies (optional)

**Acceptance:**
- Both functions defined with correct memory/timeout
- IAM policies allow DynamoDB, Bedrock, CloudWatch
- Environment variables injected
- `sam build` succeeds

#### T2.3: SAM Template - API Gateway
**Module:** template.yaml  
**Effort:** 2 hours  
**Dependencies:** T2.2

**Tasks:**
- HTTP API (NOT REST API)
- Proxy integration to ApiFunction
- CORS configuration
- Throttling: 100 req/min (burst: 200)
- Access logging to CloudWatch

**Acceptance:**
- API Gateway created as HTTP API
- All routes proxy to ApiFunction
- CORS headers present
- Logs include request_id, latency

#### T2.4: Bedrock Client Wrapper
**Module:** src/utils/bedrock.py  
**Effort:** 5 hours  
**Dependencies:** T1.3, T1.4

**Tasks:**
- BedrockClient class wrapping boto3 bedrock-runtime
- converse() method with token tracking
- Retry logic with exponential backoff
- Error handling: ThrottlingException, ValidationException
- Response parsing and usage extraction

**Acceptance:**
- Returns usage.inputTokens, usage.outputTokens
- Retries on throttling (max 3 attempts)
- Logs all calls with model_id, latency, tokens
- Unit tests with mocked boto3

#### T2.5: GitHub Client
**Module:** src/utils/github_client.py  
**Effort:** 4 hours  
**Dependencies:** T1.4

**Tasks:**
- GitHubClient class wrapping httpx
- Methods: get_workflow_runs, get_workflow_files
- Pagination handling
- Rate limit tracking (X-RateLimit-Remaining header)
- Optional token authentication

**Acceptance:**
- Handles pagination automatically
- Respects rate limits
- Returns structured data (not raw JSON)
- Unit tests with httpx mocking

---

### Phase 3: API Layer (Week 2)

#### T3.1: FastAPI Application Setup
**Module:** src/api/main.py  
**Effort:** 3 hours  
**Dependencies:** T1.3, T1.4

**Tasks:**
- Create FastAPI app with metadata
- Configure CORS middleware
- Add exception handlers
- Add request logging middleware
- Mangum handler for Lambda
- Health check endpoint

**Acceptance:**
- App starts locally with uvicorn
- /docs shows Swagger UI
- /health returns 200
- Mangum handler exports as `handler`


#### T3.2: API Dependencies (DI)
**Module:** src/api/dependencies.py  
**Effort:** 3 hours  
**Dependencies:** T2.4, T2.5, T1.5

**Tasks:**
- get_settings() - inject Settings
- get_dynamodb_table() - inject boto3 Table resource
- get_bedrock_client() - inject BedrockClient
- get_github_client() - inject GitHubClient
- verify_api_key() - authentication dependency

**Acceptance:**
- All dependencies use FastAPI Depends()
- Singletons cached appropriately
- verify_api_key raises 401 on invalid key
- Unit tests with dependency overrides

#### T3.3: Organizer Routes
**Module:** src/api/routes/organizers.py, src/services/organizer_service.py  
**Effort:** 6 hours  
**Dependencies:** T3.2, T1.3

**Tasks:**
- POST /organizers - create account, generate API key
- GET /organizers/me - get profile (authenticated)
- PUT /organizers/me - update profile
- OrganizerService: create, get_by_id, get_by_email, update
- API key generation (vj_live_ prefix + ULID)
- SHA-256 hashing for storage

**Acceptance:**
- API key shown once on creation
- Duplicate email returns 409
- Authentication works with X-API-Key header
- Integration tests with TestClient

#### T3.4: Hackathon Routes
**Module:** src/api/routes/hackathons.py, src/services/hackathon_service.py  
**Effort:** 8 hours  
**Dependencies:** T3.2, T1.3

**Tasks:**
- POST /hackathons - create with rubric validation
- GET /hackathons - list with pagination
- GET /hackathons/{id} - get details
- PUT /hackathons/{id} - update (status checks)
- DELETE /hackathons/{id} - delete (draft only)
- HackathonService: CRUD + validation
- Tier limit enforcement

**Acceptance:**
- Rubric weights validated (sum to 1.0)
- Agents match rubric dimensions
- Free tier: max 3 hackathons
- Cannot modify if analyzing/completed
- Integration tests

#### T3.5: Submission Routes
**Module:** src/api/routes/submissions.py, src/services/submission_service.py  
**Effort:** 6 hours  
**Dependencies:** T3.4

**Tasks:**
- POST /hackathons/{id}/submissions - batch add
- GET /hackathons/{id}/submissions - list with filters
- GET /hackathons/{id}/submissions/{sub_id} - get details
- DELETE /hackathons/{id}/submissions/{sub_id} - delete (pending only)
- SubmissionService: CRUD + validation
- Duplicate detection (repo URL, team name)

**Acceptance:**
- Batch size: 1-500
- GitHub URL validation
- Tier submission limits enforced
- Integration tests

---

### Phase 4: Git Analysis Engine (Week 2-3)

#### T4.1: Git Analyzer - Clone & Extract
**Module:** src/analysis/git_analyzer.py  
**Effort:** 10 hours  
**Dependencies:** T1.3, T1.4, T1.6

**Tasks:**
- clone_repo() with GitPython
- Fallback to shallow clone on timeout/size
- extract_commits() - max 100 commits
- extract_file_tree() - max depth 4
- extract_source_files() - prioritized selection, max 25
- extract_readme() - max 12KB
- extract_repo_meta() - language detection, stats
- Cleanup /tmp after extraction

**Acceptance:**
- Clones to /tmp/{submission_id}
- Handles 404, timeout, large repos
- File priority scoring works
- Always cleans up /tmp
- Unit tests with sample repos


#### T4.2: Actions Analyzer
**Module:** src/analysis/actions_analyzer.py  
**Effort:** 4 hours  
**Dependencies:** T2.5

**Tasks:**
- ActionsAnalyzer class using GitHubClient
- fetch_workflow_runs() - max 50 runs
- fetch_workflow_files() - YAML definitions
- Handle 404 (no Actions or private repo)
- Non-fatal failures (Actions data is supplementary)

**Acceptance:**
- Returns WorkflowRun list
- Returns workflow YAML content (truncated to 3KB each)
- Handles rate limiting gracefully
- Unit tests with mocked httpx

#### T4.3: Context Builder
**Module:** src/analysis/context_builder.py  
**Effort:** 6 hours  
**Dependencies:** T4.1, T4.2, T1.3

**Tasks:**
- assemble_repo_context() - build full context string
- Format source files block
- Format commit history block
- Format workflow runs block
- Apply context window budgeting
- Use REPO_CONTEXT_TEMPLATE

**Acceptance:**
- Context fits within model limits (Nova Lite: 300K, Claude: 200K)
- Prioritizes important files
- Includes all required sections
- Unit tests verify formatting

---

### Phase 5: AI Agents (Week 3)

#### T5.1: Agent Prompts
**Module:** src/prompts/*.py  
**Effort:** 8 hours  
**Dependencies:** None

**Tasks:**
- bug_hunter_v1.py - system prompt as string constant
- performance_v1.py - system prompt
- innovation_v1.py - system prompt
- ai_detection_v1.py - system prompt
- retry_prompts.py - JSON retry messages
- context_template.py - REPO_CONTEXT_TEMPLATE

**Acceptance:**
- All prompts include output schema
- Grounding rules clearly stated
- Evidence requirements specified
- Version numbers in prompts

#### T5.2: Base Agent Class
**Module:** src/agents/base.py  
**Effort:** 8 hours  
**Dependencies:** T2.4, T5.1, T1.3

**Tasks:**
- BaseAgent abstract class
- converse() wrapper with token tracking
- JSON response parsing with retry
- Evidence validation against RepoData
- Configurable model, temperature, max_tokens
- Error handling and logging

**Acceptance:**
- Captures usage.inputTokens, usage.outputTokens
- Retries once on JSON parse failure
- Validates evidence file paths and line numbers
- Returns structured AgentResponse
- Unit tests with mocked Bedrock

#### T5.3: Specialized Agents
**Module:** src/agents/bug_hunter.py, performance.py, innovation.py, ai_detection.py  
**Effort:** 6 hours  
**Dependencies:** T5.2

**Tasks:**
- BugHunterAgent extends BaseAgent
- PerformanceAgent extends BaseAgent
- InnovationAgent extends BaseAgent
- AIDetectionAgent extends BaseAgent
- Each implements evaluate(repo_data) method
- Model and prompt configuration per agent

**Acceptance:**
- Each agent uses correct model and temperature
- Returns agent-specific response model
- Integration tests with sample RepoData
- Mock Bedrock responses for testing


---

### Phase 6: Analysis Orchestration (Week 3-4)

#### T6.1: Cost Tracker
**Module:** src/analysis/cost_tracker.py  
**Effort:** 4 hours  
**Dependencies:** T1.3, T1.6

**Tasks:**
- CostTracker class
- record() method to log agent usage
- calculate_cost() using MODEL_RATES
- summary() method for aggregation
- Per-agent and per-model breakdowns

**Acceptance:**
- Accurate cost calculation
- Tracks input/output tokens separately
- Returns CostRecord objects
- Unit tests verify calculations

#### T6.2: Orchestrator
**Module:** src/analysis/orchestrator.py  
**Effort:** 10 hours  
**Dependencies:** T5.3, T6.1, T4.3

**Tasks:**
- AnalysisOrchestrator class
- analyze_submission() - full pipeline
- Run agents sequentially (or parallel if time permits)
- Aggregate scores using rubric weights
- Validate all evidence
- Handle agent failures gracefully
- Update submission status throughout

**Acceptance:**
- Runs all enabled agents
- Calculates weighted overall_score
- Validates evidence against repo files
- Continues if 1-2 agents fail
- Marks submission failed if all agents fail
- Integration tests with mocked agents

#### T6.3: Analyzer Lambda Handler
**Module:** src/analysis/lambda_handler.py  
**Effort:** 8 hours  
**Dependencies:** T6.2, T4.1

**Tasks:**
- handler() function for Lambda entry point
- Parse event (job_id, submission_ids)
- Loop through submissions
- For each: clone, extract, orchestrate, write results
- Update AnalysisJob progress
- Error handling and logging
- Cleanup /tmp between submissions

**Acceptance:**
- Processes submissions sequentially
- Updates job status: queued → running → completed
- Writes AgentScore, SubmissionSummary, CostRecord to DynamoDB
- Updates HackathonCost aggregate
- Handles timeouts gracefully
- Integration tests with moto

---

### Phase 7: Analysis API & Results (Week 4)

#### T7.1: Analysis Service
**Module:** src/services/analysis_service.py  
**Effort:** 6 hours  
**Dependencies:** T6.3, T1.5

**Tasks:**
- create_analysis_job() - validate and create job
- Pre-flight checks (pending submissions, budget)
- Invoke Analyzer Lambda asynchronously
- get_job_status() - query job progress
- estimate_cost() - calculate without running

**Acceptance:**
- Creates AnalysisJob with status=queued
- Invokes Lambda with InvocationType='Event'
- Returns cost estimate with ranges
- Budget validation works
- Unit tests

#### T7.2: Analysis Routes
**Module:** src/api/routes/analysis.py  
**Effort:** 5 hours  
**Dependencies:** T7.1

**Tasks:**
- POST /hackathons/{id}/analyze - trigger analysis
- GET /hackathons/{id}/jobs/{job_id} - poll status
- POST /hackathons/{id}/estimate - get cost estimate
- Error responses: 402 (budget), 409 (already running)

**Acceptance:**
- Returns 202 with job_id
- Poll endpoint shows progress
- Estimate endpoint doesn't charge
- Integration tests


#### T7.3: Scoring Service
**Module:** src/services/scoring_service.py  
**Effort:** 6 hours  
**Dependencies:** T1.3, T1.5

**Tasks:**
- get_leaderboard() - query and sort submissions
- get_scorecard() - fetch all agent scores
- get_evidence() - filter and return findings
- calculate_statistics() - mean, median, std_dev
- Application-side sorting by overall_score

**Acceptance:**
- Leaderboard sorted descending by score
- Scorecard includes all agent results
- Evidence filtering works
- Statistics calculated correctly
- Unit tests

#### T7.4: Cost Service
**Module:** src/services/cost_service.py  
**Effort:** 4 hours  
**Dependencies:** T1.3, T1.5

**Tasks:**
- get_hackathon_costs() - aggregate cost data
- get_submission_costs() - per-submission breakdown
- generate_optimization_tips() - based on usage patterns
- Budget utilization calculation

**Acceptance:**
- Aggregates by agent and model
- Calculates percentages
- Tips suggest cheaper models when appropriate
- Unit tests

#### T7.5: Results Routes
**Module:** src/api/routes/costs.py (results endpoints)  
**Effort:** 5 hours  
**Dependencies:** T7.3, T7.4

**Tasks:**
- GET /hackathons/{id}/leaderboard
- GET /hackathons/{id}/submissions/{sub_id}/scorecard
- GET /hackathons/{id}/submissions/{sub_id}/evidence
- GET /hackathons/{id}/costs
- Pagination and filtering

**Acceptance:**
- All endpoints return correct data
- Pagination works
- Filtering works (status, severity, agent)
- Integration tests

---

## 7. Task Dependencies

### Dependency Graph

```
T1.1 (Setup)
  ├─→ T1.2 (Common Models)
  │     └─→ T1.3 (All Models)
  │           ├─→ T1.5 (DynamoDB Helper)
  │           ├─→ T2.4 (Bedrock Client)
  │           ├─→ T3.2 (API Dependencies)
  │           └─→ T4.1 (Git Analyzer)
  ├─→ T1.4 (Config & Logging)
  │     ├─→ T2.4 (Bedrock Client)
  │     ├─→ T2.5 (GitHub Client)
  │     └─→ T3.1 (FastAPI Setup)
  └─→ T1.6 (Constants)
        └─→ T4.1 (Git Analyzer)

T2.1 (SAM DynamoDB)
  └─→ T2.2 (SAM Lambda)
        └─→ T2.3 (SAM API Gateway)

T2.4 (Bedrock Client)
  └─→ T5.2 (Base Agent)

T2.5 (GitHub Client)
  └─→ T4.2 (Actions Analyzer)

T3.1 (FastAPI Setup)
  └─→ T3.2 (API Dependencies)
        ├─→ T3.3 (Organizer Routes)
        ├─→ T3.4 (Hackathon Routes)
        └─→ T3.5 (Submission Routes)

T4.1 (Git Analyzer) + T4.2 (Actions Analyzer)
  └─→ T4.3 (Context Builder)

T5.1 (Prompts)
  └─→ T5.2 (Base Agent)
        └─→ T5.3 (Specialized Agents)

T5.3 (Agents) + T4.3 (Context Builder)
  └─→ T6.2 (Orchestrator)
        └─→ T6.3 (Analyzer Lambda)
              └─→ T7.1 (Analysis Service)
                    └─→ T7.2 (Analysis Routes)

T6.1 (Cost Tracker)
  └─→ T6.2 (Orchestrator)

T7.3 (Scoring Service) + T7.4 (Cost Service)
  └─→ T7.5 (Results Routes)
```

### Critical Path

```
T1.1 → T1.2 → T1.3 → T1.5 → T3.2 → T3.4 → T4.1 → T4.3 → T5.2 → T5.3 → T6.2 → T6.3 → T7.1 → T7.2
```

**Estimated Critical Path Duration:** ~85 hours (~2 weeks with 1 developer)


---

## 8. Testing Strategy

### 8.1 Unit Tests

**Coverage Target:** 80%+ for business logic, 60%+ overall

**Test Files:**
- tests/unit/test_models.py - Pydantic validation
- tests/unit/test_git_analyzer.py - Git extraction logic
- tests/unit/test_scoring.py - Score aggregation
- tests/unit/test_agents.py - Agent response parsing
- tests/unit/test_cost_tracker.py - Cost calculations
- tests/unit/test_context_builder.py - Context assembly

**Mocking Strategy:**
- boto3 → moto for DynamoDB
- Bedrock → manual mocks (no moto support)
- httpx → respx for GitHub API
- GitPython → sample repos in tests/fixtures/

**Example Test:**
```python
def test_rubric_weights_must_sum_to_one():
    """Rubric validation rejects weights that don't sum to 1.0"""
    with pytest.raises(ValidationError, match="must sum to 1.0"):
        RubricConfig(
            name="Invalid",
            dimensions=[
                RubricDimension(name="code", weight=0.5, agent="bug_hunter"),
                RubricDimension(name="arch", weight=0.3, agent="performance"),
            ]
        )
```

### 8.2 Integration Tests

**Test Files:**
- tests/integration/test_api.py - FastAPI endpoints with TestClient
- tests/integration/test_orchestrator.py - Full analysis pipeline
- tests/integration/test_dynamo.py - DynamoDB operations with moto

**Setup:**
- Use FastAPI TestClient (no Lambda required)
- Override dependencies to inject mocks
- Use moto for DynamoDB
- Mock Bedrock responses

**Example Test:**
```python
def test_create_hackathon_with_valid_rubric(client, auth_headers):
    """POST /hackathons creates hackathon with valid rubric"""
    response = client.post(
        "/hackathons",
        json={
            "name": "Test Hackathon",
            "rubric": {
                "dimensions": [
                    {"name": "code", "weight": 0.5, "agent": "bug_hunter"},
                    {"name": "arch", "weight": 0.5, "agent": "performance"},
                ]
            },
            "agents_enabled": ["bug_hunter", "performance"],
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Hackathon"
    assert data["status"] == "draft"
```

### 8.3 Property-Based Tests (Scoring Validation)

**Purpose:** Verify scoring invariants hold across random inputs

**Test Cases:**

#### PBT-1: Weighted Score Bounds
```python
from hypothesis import given, strategies as st

@given(
    scores=st.lists(
        st.floats(min_value=0.0, max_value=10.0),
        min_size=2,
        max_size=4
    ),
    weights=st.lists(
        st.floats(min_value=0.0, max_value=1.0),
        min_size=2,
        max_size=4
    ).filter(lambda w: abs(sum(w) - 1.0) < 0.001)
)
def test_weighted_score_always_in_range(scores, weights):
    """Weighted score must be 0-100 regardless of inputs"""
    # Ensure same length
    n = min(len(scores), len(weights))
    scores, weights = scores[:n], weights[:n]
    
    weighted = sum(s * w for s, w in zip(scores, weights)) * 10
    assert 0.0 <= weighted <= 100.0
```

#### PBT-2: Evidence Validation Idempotence
```python
@given(
    evidence=st.builds(Evidence),
    repo_data=st.builds(RepoData)
)
def test_evidence_validation_idempotent(evidence, repo_data):
    """Validating evidence twice gives same result"""
    result1 = validate_evidence(evidence, repo_data)
    result2 = validate_evidence(evidence, repo_data)
    assert result1 == result2
    assert evidence.verified == evidence.verified  # No mutation
```

#### PBT-3: Cost Calculation Monotonicity
```python
@given(
    input_tokens=st.integers(min_value=0, max_value=1000000),
    output_tokens=st.integers(min_value=0, max_value=1000000),
    model_id=st.sampled_from(list(MODEL_RATES.keys()))
)
def test_cost_increases_with_tokens(input_tokens, output_tokens, model_id):
    """More tokens = higher cost"""
    cost1 = calculate_cost(input_tokens, output_tokens, model_id)
    cost2 = calculate_cost(input_tokens + 100, output_tokens + 100, model_id)
    assert cost2 > cost1
```


#### PBT-4: Leaderboard Sorting Consistency
```python
@given(
    submissions=st.lists(
        st.builds(
            SubmissionListItem,
            overall_score=st.floats(min_value=0, max_value=100)
        ),
        min_size=1,
        max_size=100
    )
)
def test_leaderboard_always_sorted_descending(submissions):
    """Leaderboard must be sorted by score descending"""
    leaderboard = sort_leaderboard(submissions)
    scores = [s.overall_score for s in leaderboard]
    assert scores == sorted(scores, reverse=True)
```

### 8.4 End-to-End Test Scenario

**Scenario:** Complete hackathon workflow

```python
def test_complete_hackathon_workflow(client, sample_repo_url):
    """E2E: Create org → hackathon → submissions → analyze → leaderboard"""
    
    # 1. Create organizer
    org_resp = client.post("/organizers", json={
        "email": "test@example.com",
        "name": "Test Organizer"
    })
    assert org_resp.status_code == 201
    api_key = org_resp.json()["api_key"]
    headers = {"X-API-Key": api_key}
    
    # 2. Create hackathon
    hack_resp = client.post("/hackathons", json={
        "name": "Test Hack",
        "rubric": {...},
        "agents_enabled": ["bug_hunter", "innovation"],
    }, headers=headers)
    hack_id = hack_resp.json()["hack_id"]
    
    # 3. Add submissions
    sub_resp = client.post(f"/hackathons/{hack_id}/submissions", json={
        "submissions": [
            {"team_name": "Team A", "repo_url": sample_repo_url},
        ]
    }, headers=headers)
    assert sub_resp.status_code == 201
    
    # 4. Trigger analysis
    analyze_resp = client.post(
        f"/hackathons/{hack_id}/analyze",
        headers=headers
    )
    assert analyze_resp.status_code == 202
    job_id = analyze_resp.json()["job_id"]
    
    # 5. Poll until complete (mocked to complete immediately)
    job_resp = client.get(
        f"/hackathons/{hack_id}/jobs/{job_id}",
        headers=headers
    )
    assert job_resp.json()["status"] == "completed"
    
    # 6. Get leaderboard
    lb_resp = client.get(
        f"/hackathons/{hack_id}/leaderboard",
        headers=headers
    )
    assert lb_resp.status_code == 200
    assert len(lb_resp.json()["leaderboard"]) == 1
    
    # 7. Get scorecard
    sub_id = sub_resp.json()["submissions"][0]["sub_id"]
    sc_resp = client.get(
        f"/hackathons/{hack_id}/submissions/{sub_id}/scorecard",
        headers=headers
    )
    assert sc_resp.status_code == 200
    assert "agents" in sc_resp.json()
    assert "bug_hunter" in sc_resp.json()["agents"]
```

### 8.5 Test Fixtures

**Location:** tests/fixtures/

**Sample Repos:**
- basic_python/ - Minimal Flask app (50 lines, 5 commits)
- react_app/ - Small React app (200 lines, 15 commits, CI)
- security_issues/ - Intentional vulnerabilities for BugHunter

**Mock Bedrock Responses:**
- bug_hunter_response.json - Valid BugHunter JSON
- innovation_response.json - Valid Innovation JSON
- invalid_json_response.txt - Malformed response for retry testing

---

## 9. Success Metrics

### 9.1 Performance Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Analyze 50 repos | < 30 minutes | End-to-end time from trigger to completion |
| Cost per repo | < $0.025 | Average across 50 repos |
| API response time | < 200ms (p95) | All endpoints except /analyze |
| Evidence verification | > 95% | Verified / total evidence items |
| Lambda timeouts | 0 | No 15min timeout errors |

### 9.2 Quality Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Test coverage | > 80% business logic | pytest-cov |
| Type coverage | 100% | mypy strict mode |
| Linting | 0 errors | ruff check |
| Agent JSON parse success | > 98% | Successful parses / total calls |
| Evidence hallucination rate | < 5% | Unverified evidence / total |


### 9.3 AWS Free Tier Compliance

| Service | Free Tier | Usage Target | Status |
|---------|-----------|--------------|--------|
| Lambda Requests | 1M/month | ~10K/month | ✅ 1% |
| Lambda GB-seconds | 400K/month | ~50K/month | ✅ 12.5% |
| DynamoDB RCU | 25 total | 15 (5+5+5) | ✅ 60% |
| DynamoDB WCU | 25 total | 15 (5+5+5) | ✅ 60% |
| DynamoDB Storage | 25 GB | ~50 MB | ✅ 0.2% |
| API Gateway | 1M calls/month | ~10K/month | ✅ 1% |
| CloudWatch Logs | 5 GB | ~500 MB | ✅ 10% |
| S3 Storage | 5 GB (12mo) | <100 MB | ✅ 2% |

**Bedrock:** NOT free tier - pay per token (~$0.023/submission)

---

## 10. Constraints & Risks

### 10.1 Technical Constraints

| Constraint | Impact | Mitigation |
|------------|--------|------------|
| Lambda 15min timeout | Cannot analyze very large repos | Shallow clone fallback, skip if >2GB |
| Lambda /tmp 2GB | Cannot clone huge repos | Shallow clone, fail gracefully |
| DynamoDB 400KB item limit | Large scorecards may exceed | Store raw_response in S3 if >400KB |
| Bedrock rate limits | Throttling on high volume | Exponential backoff, retry logic |
| GitHub API rate limit | 60 req/hr unauthenticated | Actions data optional, degrade gracefully |
| Context window limits | Cannot fit entire large repos | Prioritized file selection, truncation |

### 10.2 Risks & Mitigation

#### Risk 1: Agent Hallucinations
**Probability:** Medium  
**Impact:** High (destroys trust)  
**Mitigation:**
- Evidence validation against file tree
- Confidence scoring
- Flag unverified evidence for manual review
- Property-based tests for validation logic

#### Risk 2: Bedrock Cost Overruns
**Probability:** Medium  
**Impact:** High (budget exceeded)  
**Mitigation:**
- Pre-flight cost estimation
- Budget limits enforced
- Cost tracking per agent
- Optimization tips in dashboard

#### Risk 3: Lambda Cold Starts
**Probability:** High  
**Impact:** Low (latency, not correctness)  
**Mitigation:**
- 1GB memory for API Lambda (faster cold start)
- Keep dependencies lean
- Accept cold starts for MVP (optimize in Phase 2)

#### Risk 4: DynamoDB Throttling
**Probability:** Low  
**Impact:** Medium (failed writes)  
**Mitigation:**
- Provisioned capacity with headroom (5 vs 25 limit)
- Exponential backoff in DynamoDB helper
- Batch writes where possible

#### Risk 5: GitHub Repo Inaccessible
**Probability:** Medium  
**Impact:** Low (single submission fails)  
**Mitigation:**
- Handle 404 gracefully
- Mark submission as failed with clear error
- Continue with remaining submissions

#### Risk 6: Agent JSON Parse Failures
**Probability:** Medium  
**Impact:** Medium (submission fails)  
**Mitigation:**
- Retry once with correction prompt
- Fallback to partial results if 1-2 agents fail
- Log failures for prompt improvement

### 10.3 Competition-Specific Risks

#### Risk 7: Deadline Miss (March 6, 2026)
**Probability:** Low  
**Impact:** Critical (disqualification)  
**Mitigation:**
- Prioritize critical path tasks
- Cut scope if needed (e.g., only 2 agents for MVP)
- Daily progress tracking
- Buffer time for debugging

#### Risk 8: Article Not Published (March 13, 2026)
**Probability:** Low  
**Impact:** Critical (disqualification)  
**Mitigation:**
- Draft article outline early (Week 2)
- Write sections as features complete
- Reserve March 7-12 for article writing
- Have peer review article before submission

---

## 11. Deployment & Operations

### 11.1 Deployment Process

```bash
# 1. Install dependencies
make install

# 2. Run tests
make test

# 3. Lint and type check
make lint

# 4. Build SAM application
sam build

# 5. Deploy to AWS
sam deploy --guided  # First time
sam deploy           # Subsequent deploys

# 6. Get API endpoint
aws cloudformation describe-stacks \
  --stack-name vibejudge-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
  --output text
```


### 11.2 Environment Variables

**API Lambda:**
```
TABLE_NAME=vibejudge-dev-table
BEDROCK_REGION=us-east-1
LOG_LEVEL=INFO
ANALYZER_FUNCTION_NAME=vibejudge-dev-analyzer
```

**Analyzer Lambda:**
```
TABLE_NAME=vibejudge-dev-table
BEDROCK_REGION=us-east-1
LOG_LEVEL=INFO
GITHUB_TOKEN=<optional>
```

### 11.3 Monitoring & Alarms

**CloudWatch Alarms:**
1. API Lambda errors > 5 in 5 minutes
2. Analyzer Lambda timeouts > 1 in 15 minutes
3. DynamoDB throttled requests > 10 in 5 minutes
4. API Gateway 5xx errors > 10 in 5 minutes
5. Bedrock cost > $50/day

**CloudWatch Dashboards:**
- API request count, latency, errors
- Lambda invocations, duration, memory
- DynamoDB read/write capacity utilization
- Bedrock token usage and cost

**Log Insights Queries:**
```
# Failed submissions
fields @timestamp, sub_id, error_message
| filter status = "failed"
| sort @timestamp desc

# High-cost submissions
fields @timestamp, sub_id, total_cost_usd
| filter total_cost_usd > 0.05
| sort total_cost_usd desc

# Agent failures
fields @timestamp, agent_name, error
| filter event = "agent_failed"
| stats count() by agent_name
```

---

## 12. Future Enhancements (Phase 2)

### 12.1 Real-Time Analysis
- GitHub App installation
- Webhook receiver for push events
- SQS queue for buffering
- Diff-only analysis (not full repo)
- Live leaderboard updates

### 12.2 Dashboard
- React + Tailwind CSS
- Real-time job progress
- Interactive scorecard viewer
- Cost analytics charts
- Rubric builder UI

### 12.3 Advanced Features
- Custom agent creation (organizer-defined prompts)
- PDF scorecard generation
- Email notifications
- Slack/Discord integration
- Multi-language support (beyond English)
- Private repo support (GitHub App auth)

### 12.4 Enterprise Features
- White-label deployment
- SSO integration (Okta, Auth0)
- Audit logs
- Team management
- Custom SLAs
- Dedicated Bedrock capacity

---

## 13. Appendix

### 13.1 Glossary

| Term | Definition |
|------|------------|
| Agent | Specialized AI judge (BugHunter, Performance, Innovation, AIDetection) |
| Rubric | Scoring configuration with weighted dimensions |
| Evidence | File:line citation supporting a finding |
| Dimension | Scoring category (e.g., code_quality, security) |
| Submission | GitHub repo submitted to hackathon |
| Organizer | Hackathon host using VibeJudge |
| Converse API | Bedrock API for LLM inference with token tracking |
| ULID | Universally Unique Lexicographically Sortable Identifier |
| GSI | Global Secondary Index (DynamoDB) |
| EARS | Easy Approach to Requirements Syntax |

### 13.2 References

- [AWS SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/)
- [Bedrock Converse API](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic v2 Documentation](https://docs.pydantic.dev/latest/)
- [DynamoDB Single-Table Design](https://aws.amazon.com/blogs/compute/creating-a-single-table-design-with-amazon-dynamodb/)
- [GitPython Documentation](https://gitpython.readthedocs.io/)

### 13.3 Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-21 | Kiro AI | Initial comprehensive specification |

---

**END OF SPECIFICATION**

