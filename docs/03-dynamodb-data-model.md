# VibeJudge AI — DynamoDB Data Model

> **Version:** 1.0  
> **Date:** February 2026  
> **Author:** Maku Mazakpe / Vibe Coders  
> **Status:** APPROVED  
> **Depends On:** ADR-004 (Single-Table DynamoDB Design)  
> **Table Name:** `VibeJudgeTable`

---

## Table of Contents

1. [Design Principles](#1-design-principles)
2. [Table Configuration](#2-table-configuration)
3. [Entity Catalog](#3-entity-catalog)
4. [Key Schema & Entity Definitions](#4-key-schema--entity-definitions)
5. [Access Patterns](#5-access-patterns)
6. [Global Secondary Indexes](#6-global-secondary-indexes)
7. [Entity Relationship Diagram](#7-entity-relationship-diagram)
8. [TTL & Lifecycle Rules](#8-ttl--lifecycle-rules)
9. [Capacity Planning](#9-capacity-planning)
10. [SAM Template Fragment](#10-sam-template-fragment)
11. [Seed Data](#11-seed-data)

---

## 1. Design Principles

- **Single-table design** — All entities in one table (per ADR-004)
- **Composite keys** — `PK` (partition key) + `SK` (sort key) enable hierarchical queries
- **Overloaded keys** — Same PK/SK columns store different entity types, prefixed for clarity
- **GSIs for cross-entity queries** — 2 GSIs max to stay within free tier
- **Denormalization** — Duplicate data where it avoids extra reads (e.g., hackathon name on submission records)
- **ISO 8601 timestamps** — All dates stored as `YYYY-MM-DDTHH:MM:SSZ` for lexicographic sorting
- **ULID for IDs** — Universally Unique Lexicographically Sortable Identifiers. Sortable by time, globally unique, URL-safe. Python: `python-ulid` package

---

## 2. Table Configuration

```yaml
Table Name:       VibeJudgeTable
Billing Mode:     PROVISIONED (free tier eligible)
Read Capacity:    5 RCU  (within 25 RCU free tier)
Write Capacity:   5 WCU  (within 25 WCU free tier)
Table Class:      STANDARD (CRITICAL: Standard-IA is NOT free tier eligible)

Primary Key:
  PK (String)  — Partition Key
  SK (String)  — Sort Key

GSI1:
  GSI1PK (String) — Partition Key
  GSI1SK (String) — Sort Key
  Projection: ALL
  RCU: 5 | WCU: 5

GSI2:
  GSI2PK (String) — Partition Key
  GSI2SK (String) — Sort Key
  Projection: KEYS_ONLY
  RCU: 5 | WCU: 5

TTL Attribute:    expires_at
Point-in-Time Recovery: Disabled (MVP — enable for production)
Encryption:       AWS owned key (default, free)
```

**Free Tier Budget:**
| Resource | Free Tier | Our Usage | Headroom |
|----------|-----------|-----------|----------|
| RCU (provisioned) | 25 | 15 (5 table + 5 GSI1 + 5 GSI2) | 10 |
| WCU (provisioned) | 25 | 15 (5 table + 5 GSI1 + 5 GSI2) | 10 |
| Storage | 25 GB | ~50 MB (est.) | 24.95 GB |
| Streams | 2.5M reads | 0 (not using) | 2.5M |

---

## 3. Entity Catalog

| Entity | PK Pattern | SK Pattern | Description |
|--------|-----------|-----------|-------------|
| Organizer | `ORG#<org_id>` | `PROFILE` | Organizer account info |
| Hackathon | `ORG#<org_id>` | `HACK#<hack_id>` | Hackathon configuration |
| HackathonDetail | `HACK#<hack_id>` | `META` | Full hackathon metadata (denormalized) |
| Submission | `HACK#<hack_id>` | `SUB#<sub_id>` | Submission record for a repo |
| AgentScore | `SUB#<sub_id>` | `SCORE#<agent_name>` | Individual agent scorecard |
| SubmissionSummary | `SUB#<sub_id>` | `SUMMARY` | Aggregated scorecard across all agents |
| CostRecord | `SUB#<sub_id>` | `COST#<agent_name>` | Token/cost data per agent per submission |
| HackathonCost | `HACK#<hack_id>` | `COST#SUMMARY` | Aggregated cost for entire hackathon |
| AnalysisJob | `HACK#<hack_id>` | `JOB#<job_id>` | Batch analysis job tracking |

---

## 4. Key Schema & Entity Definitions

### 4.1 Organizer

```
PK:     ORG#<org_id>
SK:     PROFILE
GSI1PK: EMAIL#<email>
GSI1SK: ORG#<org_id>
```

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| PK | S | ✅ | `ORG#<ulid>` |
| SK | S | ✅ | `PROFILE` |
| entity_type | S | ✅ | `ORGANIZER` |
| org_id | S | ✅ | ULID |
| email | S | ✅ | Organizer email |
| name | S | ✅ | Display name |
| organization | S | ❌ | Company/org name |
| tier | S | ✅ | `free` \| `premium` \| `enterprise` |
| hackathon_count | N | ✅ | Running count of hackathons created |
| created_at | S | ✅ | ISO 8601 |
| updated_at | S | ✅ | ISO 8601 |
| GSI1PK | S | ✅ | `EMAIL#<email>` (for login lookup) |
| GSI1SK | S | ✅ | `ORG#<org_id>` |

---

### 4.2 Hackathon (on Organizer partition — for "list my hackathons")

```
PK:     ORG#<org_id>
SK:     HACK#<hack_id>
GSI1PK: HACK#<hack_id>
GSI1SK: META
```

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| PK | S | ✅ | `ORG#<org_id>` |
| SK | S | ✅ | `HACK#<hack_id>` |
| entity_type | S | ✅ | `HACKATHON` |
| hack_id | S | ✅ | ULID |
| org_id | S | ✅ | Owner organizer ULID |
| name | S | ✅ | Hackathon name |
| status | S | ✅ | `draft` \| `configured` \| `analyzing` \| `completed` \| `archived` |
| submission_count | N | ✅ | Number of submissions |
| created_at | S | ✅ | ISO 8601 |
| updated_at | S | ✅ | ISO 8601 |
| GSI1PK | S | ✅ | `HACK#<hack_id>` (for direct hackathon lookup) |
| GSI1SK | S | ✅ | `META` |

---

### 4.3 HackathonDetail (denormalized — full config on its own partition)

```
PK:     HACK#<hack_id>
SK:     META
```

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| PK | S | ✅ | `HACK#<hack_id>` |
| SK | S | ✅ | `META` |
| entity_type | S | ✅ | `HACKATHON_DETAIL` |
| hack_id | S | ✅ | ULID |
| org_id | S | ✅ | Owner organizer |
| name | S | ✅ | Hackathon name |
| description | S | ❌ | Description |
| status | S | ✅ | Same as above |
| start_date | S | ❌ | ISO 8601 |
| end_date | S | ❌ | ISO 8601 |
| rubric | M | ✅ | Rubric configuration (see below) |
| agents_enabled | L | ✅ | `["bug_hunter", "performance", "innovation", "ai_detection"]` |
| ai_policy_mode | S | ✅ | `full_vibe` \| `ai_assisted` \| `traditional` \| `custom` |
| ai_policy_config | M | ❌ | Custom AI policy rules (if mode=custom) |
| repo_urls | L | ❌ | List of repo URLs (for batch mode) |
| submission_count | N | ✅ | Count |
| budget_limit_usd | N | ❌ | Max spend for this hackathon |
| created_at | S | ✅ | ISO 8601 |
| updated_at | S | ✅ | ISO 8601 |

**Rubric Structure (Map):**
```json
{
  "rubric": {
    "name": "AWS Bedrock Challenge",
    "version": "1.0",
    "max_score": 100,
    "dimensions": [
      {
        "name": "code_quality",
        "weight": 0.25,
        "agent": "bug_hunter",
        "description": "Code quality, security, test coverage"
      },
      {
        "name": "architecture",
        "weight": 0.25,
        "agent": "performance",
        "description": "Architecture design, scalability, performance"
      },
      {
        "name": "innovation",
        "weight": 0.30,
        "agent": "innovation",
        "description": "Technical innovation, creativity, README quality"
      },
      {
        "name": "authenticity",
        "weight": 0.20,
        "agent": "ai_detection",
        "description": "Development authenticity, commit patterns"
      }
    ]
  }
}
```

---

### 4.4 Submission

```
PK:     HACK#<hack_id>
SK:     SUB#<sub_id>
GSI1PK: SUB#<sub_id>
GSI1SK: HACK#<hack_id>
```

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| PK | S | ✅ | `HACK#<hack_id>` |
| SK | S | ✅ | `SUB#<sub_id>` |
| entity_type | S | ✅ | `SUBMISSION` |
| sub_id | S | ✅ | ULID |
| hack_id | S | ✅ | Parent hackathon |
| team_name | S | ✅ | Team display name |
| repo_url | S | ✅ | GitHub repo URL |
| repo_owner | S | ✅ | GitHub owner (org or user) |
| repo_name | S | ✅ | GitHub repo name |
| default_branch | S | ✅ | `main` \| `master` \| etc. |
| status | S | ✅ | `pending` \| `cloning` \| `analyzing` \| `completed` \| `failed` \| `timeout` |
| error_message | S | ❌ | Error details if status=failed |
| overall_score | N | ❌ | Weighted aggregate (0-100), set after analysis |
| rank | N | ❌ | Position in hackathon leaderboard |
| total_cost_usd | N | ❌ | Total AI cost for this submission |
| total_tokens | N | ❌ | Total tokens consumed |
| analysis_duration_ms | N | ❌ | End-to-end analysis time |
| repo_meta | M | ❌ | Extracted metadata (see below) |
| created_at | S | ✅ | ISO 8601 |
| updated_at | S | ✅ | ISO 8601 |
| GSI1PK | S | ✅ | `SUB#<sub_id>` (for direct submission lookup) |
| GSI1SK | S | ✅ | `HACK#<hack_id>` |

**repo_meta Structure (Map — populated after cloning):**
```json
{
  "repo_meta": {
    "commit_count": 147,
    "branch_count": 3,
    "contributor_count": 4,
    "primary_language": "Python",
    "languages": {"Python": 65, "JavaScript": 30, "HTML": 5},
    "total_files": 42,
    "total_lines": 3850,
    "has_readme": true,
    "has_tests": true,
    "has_ci": true,
    "has_dockerfile": false,
    "first_commit_at": "2026-02-01T09:00:00Z",
    "last_commit_at": "2026-02-02T23:45:00Z",
    "development_duration_hours": 38.75,
    "workflow_run_count": 23,
    "workflow_success_rate": 0.78
  }
}
```

---

### 4.5 AgentScore

```
PK:     SUB#<sub_id>
SK:     SCORE#<agent_name>
```

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| PK | S | ✅ | `SUB#<sub_id>` |
| SK | S | ✅ | `SCORE#bug_hunter` \| `SCORE#performance` \| `SCORE#innovation` \| `SCORE#ai_detection` |
| entity_type | S | ✅ | `AGENT_SCORE` |
| sub_id | S | ✅ | Parent submission |
| hack_id | S | ✅ | Parent hackathon (denormalized) |
| agent_name | S | ✅ | `bug_hunter` \| `performance` \| `innovation` \| `ai_detection` |
| model_id | S | ✅ | Bedrock model used (e.g., `amazon.nova-lite-v1:0`) |
| scores | M | ✅ | Agent-specific sub-scores (see Agent Prompt Library) |
| overall_score | N | ✅ | Agent's overall score (0-100) |
| evidence | L | ✅ | List of findings with file/line/severity |
| summary | S | ✅ | Human-readable summary paragraph |
| raw_response | S | ❌ | Full LLM response (for debugging, stored in S3 if >400KB) |
| latency_ms | N | ✅ | Agent execution time |
| created_at | S | ✅ | ISO 8601 |

**scores Structure per Agent:**

BugHunter:
```json
{"code_quality": 7.5, "security": 6.0, "test_coverage": 8.0, "error_handling": 5.5, "dependency_hygiene": 7.0}
```

Performance:
```json
{"architecture": 8.0, "database_design": 7.0, "api_design": 8.5, "scalability": 6.5, "resource_efficiency": 7.5}
```

Innovation:
```json
{"technical_novelty": 9.0, "creative_problem_solving": 8.5, "architecture_elegance": 7.5, "readme_quality": 8.0, "demo_potential": 7.0}
```

AI Detection:
```json
{"commit_authenticity": 8.5, "development_velocity": 7.0, "authorship_consistency": 9.0, "iteration_depth": 8.0, "ai_generation_indicators": 3.0}
```

---

### 4.6 SubmissionSummary

```
PK:     SUB#<sub_id>
SK:     SUMMARY
```

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| PK | S | ✅ | `SUB#<sub_id>` |
| SK | S | ✅ | `SUMMARY` |
| entity_type | S | ✅ | `SUBMISSION_SUMMARY` |
| sub_id | S | ✅ | Submission ID |
| hack_id | S | ✅ | Hackathon ID (denormalized) |
| team_name | S | ✅ | Team name (denormalized) |
| weighted_scores | M | ✅ | Per-dimension weighted scores |
| overall_score | N | ✅ | Final weighted score (0-100) |
| agent_scores | M | ✅ | `{agent_name: overall_score}` quick lookup |
| strengths | L | ✅ | Top 3 strengths across all agents |
| weaknesses | L | ✅ | Top 3 areas for improvement |
| recommendation | S | ✅ | `strong_contender` \| `solid_submission` \| `needs_improvement` \| `concerns_flagged` |
| total_cost_usd | N | ✅ | Total AI cost |
| total_tokens | N | ✅ | Total tokens |
| analysis_duration_ms | N | ✅ | Total analysis time |
| created_at | S | ✅ | ISO 8601 |

**weighted_scores Structure:**
```json
{
  "weighted_scores": {
    "code_quality": {"raw": 6.75, "weight": 0.25, "weighted": 1.69},
    "architecture": {"raw": 7.50, "weight": 0.25, "weighted": 1.88},
    "innovation": {"raw": 8.20, "weight": 0.30, "weighted": 2.46},
    "authenticity": {"raw": 8.00, "weight": 0.20, "weighted": 1.60}
  }
}
```

---

### 4.7 CostRecord

```
PK:     SUB#<sub_id>
SK:     COST#<agent_name>
```

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| PK | S | ✅ | `SUB#<sub_id>` |
| SK | S | ✅ | `COST#bug_hunter` \| etc. |
| entity_type | S | ✅ | `COST_RECORD` |
| sub_id | S | ✅ | Submission ID |
| hack_id | S | ✅ | Hackathon ID (denormalized) |
| agent_name | S | ✅ | Agent name |
| model_id | S | ✅ | Bedrock model used |
| input_tokens | N | ✅ | From Converse API response |
| output_tokens | N | ✅ | From Converse API response |
| total_tokens | N | ✅ | input + output |
| input_cost_usd | N | ✅ | Calculated: input_tokens × model_rate |
| output_cost_usd | N | ✅ | Calculated: output_tokens × model_rate |
| total_cost_usd | N | ✅ | input_cost + output_cost |
| latency_ms | N | ✅ | Response latency |
| service_tier | S | ✅ | `standard` \| `flex` |
| cache_read_tokens | N | ❌ | Prompt cache read tokens (if caching enabled) |
| cache_write_tokens | N | ❌ | Prompt cache write tokens |
| created_at | S | ✅ | ISO 8601 |

**Model Rate Constants (stored in application config, not DB):**
```python
MODEL_RATES = {
    "amazon.nova-micro-v1:0":  {"input": 0.000000035, "output": 0.000000140},  # per token
    "amazon.nova-lite-v1:0":   {"input": 0.000000060, "output": 0.000000240},
    "amazon.nova-pro-v1:0":    {"input": 0.000000800, "output": 0.000003200},
    "anthropic.claude-sonnet-4-20250514": {"input": 0.000003000, "output": 0.000015000},
}
```

---

### 4.8 HackathonCost (Aggregated)

```
PK:     HACK#<hack_id>
SK:     COST#SUMMARY
```

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| PK | S | ✅ | `HACK#<hack_id>` |
| SK | S | ✅ | `COST#SUMMARY` |
| entity_type | S | ✅ | `HACKATHON_COST` |
| hack_id | S | ✅ | Hackathon ID |
| total_cost_usd | N | ✅ | Sum across all submissions |
| total_input_tokens | N | ✅ | Sum |
| total_output_tokens | N | ✅ | Sum |
| submissions_analyzed | N | ✅ | Count |
| avg_cost_per_submission | N | ✅ | Calculated |
| cost_by_agent | M | ✅ | `{agent_name: total_cost}` |
| cost_by_model | M | ✅ | `{model_id: total_cost}` |
| budget_limit_usd | N | ❌ | From hackathon config |
| budget_remaining_usd | N | ❌ | Calculated |
| updated_at | S | ✅ | ISO 8601 (updated after each submission completes) |

---

### 4.9 AnalysisJob

```
PK:     HACK#<hack_id>
SK:     JOB#<job_id>
GSI2PK: JOB_STATUS#<status>
GSI2SK: <created_at>
```

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| PK | S | ✅ | `HACK#<hack_id>` |
| SK | S | ✅ | `JOB#<ulid>` |
| entity_type | S | ✅ | `ANALYSIS_JOB` |
| job_id | S | ✅ | ULID |
| hack_id | S | ✅ | Hackathon ID |
| status | S | ✅ | `queued` \| `running` \| `completed` \| `failed` \| `cancelled` |
| total_submissions | N | ✅ | Total repos to analyze |
| completed_submissions | N | ✅ | Progress counter |
| failed_submissions | N | ✅ | Error counter |
| started_at | S | ❌ | ISO 8601 |
| completed_at | S | ❌ | ISO 8601 |
| error_log | L | ❌ | List of `{sub_id, error_message}` for failures |
| created_at | S | ✅ | ISO 8601 |
| updated_at | S | ✅ | ISO 8601 |
| GSI2PK | S | ✅ | `JOB_STATUS#<status>` |
| GSI2SK | S | ✅ | `<created_at>` |
| expires_at | N | ❌ | TTL epoch for auto-cleanup |

---

## 5. Access Patterns

| # | Access Pattern | Operation | Key Condition | Index |
|---|---------------|-----------|---------------|-------|
| AP1 | Get organizer by ID | GetItem | `PK=ORG#<id>, SK=PROFILE` | Table |
| AP2 | Get organizer by email | Query | `GSI1PK=EMAIL#<email>` | GSI1 |
| AP3 | List hackathons for organizer | Query | `PK=ORG#<id>, SK begins_with HACK#` | Table |
| AP4 | Get hackathon config | GetItem | `PK=HACK#<id>, SK=META` | Table |
| AP5 | Get hackathon by ID (from any context) | Query | `GSI1PK=HACK#<id>, GSI1SK=META` | GSI1 |
| AP6 | List all submissions for hackathon | Query | `PK=HACK#<id>, SK begins_with SUB#` | Table |
| AP7 | Get single submission | GetItem | `PK=HACK#<id>, SK=SUB#<id>` | Table |
| AP8 | Get submission by ID (from any context) | Query | `GSI1PK=SUB#<id>` | GSI1 |
| AP9 | Get all agent scores for submission | Query | `PK=SUB#<id>, SK begins_with SCORE#` | Table |
| AP10 | Get specific agent score | GetItem | `PK=SUB#<id>, SK=SCORE#<agent>` | Table |
| AP11 | Get submission summary | GetItem | `PK=SUB#<id>, SK=SUMMARY` | Table |
| AP12 | Get all cost records for submission | Query | `PK=SUB#<id>, SK begins_with COST#` | Table |
| AP13 | Get hackathon cost summary | GetItem | `PK=HACK#<id>, SK=COST#SUMMARY` | Table |
| AP14 | List analysis jobs for hackathon | Query | `PK=HACK#<id>, SK begins_with JOB#` | Table |
| AP15 | List jobs by status | Query | `GSI2PK=JOB_STATUS#<status>` | GSI2 |
| AP16 | Get leaderboard (sorted by score) | Query + Sort | `PK=HACK#<id>, SK begins_with SUB#`, sort by overall_score | Table* |

*AP16 Note: DynamoDB doesn't natively sort by a non-key attribute. Two options: (1) Query all submissions, sort in application code (fine for <500 items). (2) Add GSI with `HACK#<id>` as PK and zero-padded score as SK (e.g., `SK=RANK#0087.50`). For MVP, option (1) is simpler.

---

## 6. Global Secondary Indexes

### GSI1 — Cross-Entity Lookup Index

**Purpose:** Look up any entity by its own ID regardless of its partition placement.

```
GSI1PK (String) — Partition Key
GSI1SK (String) — Sort Key
Projection: ALL
```

| Entity | GSI1PK | GSI1SK | Use Case |
|--------|--------|--------|----------|
| Organizer | `EMAIL#<email>` | `ORG#<org_id>` | Login by email |
| Hackathon | `HACK#<hack_id>` | `META` | Direct hackathon lookup |
| Submission | `SUB#<sub_id>` | `HACK#<hack_id>` | Direct submission lookup + find parent hackathon |

### GSI2 — Status & Time Index

**Purpose:** Query entities by status with time-based sorting. Primarily for job management.

```
GSI2PK (String) — Partition Key
GSI2SK (String) — Sort Key
Projection: KEYS_ONLY (minimal cost)
```

| Entity | GSI2PK | GSI2SK | Use Case |
|--------|--------|--------|----------|
| AnalysisJob | `JOB_STATUS#<status>` | `<created_at>` | List running/queued jobs |

*KEYS_ONLY projection: GSI2 returns only PK/SK, then we do a GetItem on the table for full data. This minimizes GSI write costs since only key attributes are replicated.*

---

## 7. Entity Relationship Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                        VibeJudgeTable                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐                                             │
│  │  Organizer   │ PK: ORG#<id>  SK: PROFILE                 │
│  │  (account)   │                                            │
│  └──────┬──────┘                                             │
│         │ 1:many                                             │
│         ▼                                                    │
│  ┌─────────────┐                                             │
│  │  Hackathon   │ PK: ORG#<id>  SK: HACK#<id>   (listing)   │
│  │  (config)    │ PK: HACK#<id> SK: META         (detail)    │
│  └──────┬──────┘                                             │
│         │ 1:many                         1:1                 │
│         ▼                                 ▼                  │
│  ┌─────────────┐                  ┌──────────────┐           │
│  │ Submission   │ PK: HACK#<id>   │ HackathonCost│           │
│  │ (repo)       │ SK: SUB#<id>    │ (aggregate)  │           │
│  └──────┬──────┘                  └──────────────┘           │
│         │ 1:many          1:1                                │
│         ├─────────────────┼──────────────────┐               │
│         ▼                 ▼                  ▼               │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐         │
│  │ AgentScore   │  │ Submission   │  │ CostRecord  │         │
│  │ (per agent)  │  │ Summary      │  │ (per agent) │         │
│  │ PK: SUB#<id> │  │ PK: SUB#<id> │  │ PK: SUB#<id>│         │
│  │ SK: SCORE#   │  │ SK: SUMMARY  │  │ SK: COST#   │         │
│  └─────────────┘  └──────────────┘  └─────────────┘         │
│                                                              │
│  ┌─────────────┐                                             │
│  │ AnalysisJob  │ PK: HACK#<id>  SK: JOB#<id>               │
│  │ (batch job)  │ Tracks progress of batch analysis          │
│  └─────────────┘                                             │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 8. TTL & Lifecycle Rules

| Entity | TTL Policy | Rationale |
|--------|-----------|-----------|
| AnalysisJob | 30 days after completion | Job tracking is temporary operational data |
| CostRecord | None | Retained for billing intelligence |
| AgentScore | None | Core product data |
| Submission | None | Core product data |
| Hackathon | None | Core product data |
| Organizer | None | Account data |

**TTL Implementation:**
```python
# When creating an AnalysisJob
import time
expires_at = int(time.time()) + (30 * 24 * 60 * 60)  # 30 days from now
item["expires_at"] = expires_at
```

DynamoDB TTL deletes expired items automatically at no cost (within 48 hours of expiry).

---

## 9. Capacity Planning

### MVP Scenario: 1 hackathon, 50 submissions, 4 agents

**Write Operations (during analysis):**
| Operation | Count | WCU per op | Total WCU-seconds |
|-----------|-------|-----------|-------------------|
| Create submission records | 50 | 1 | 50 |
| Write agent scores | 200 (50×4) | 1 | 200 |
| Write cost records | 200 (50×4) | 1 | 200 |
| Write submission summaries | 50 | 1 | 50 |
| Update hackathon cost | 50 | 1 | 50 |
| Update submission status (×3) | 150 | 1 | 150 |
| **Total** | **700** | | **700 WCU-seconds** |

At 5 WCU provisioned: 700 ÷ 5 = **140 seconds to complete all writes** (if writing continuously).

Analysis of 50 submissions takes ~25-50 minutes (Bedrock API calls dominate), so writes are well within 5 WCU capacity.

**Read Operations (dashboard/API):**
| Operation | Frequency | RCU per op |
|-----------|-----------|-----------|
| Get hackathon config | Low | 1 |
| List submissions (leaderboard) | Medium | 2-3 (50 items) |
| Get submission detail + scores | Medium | 2 (1 + query) |
| Get hackathon cost summary | Low | 1 |

At 5 RCU provisioned: More than sufficient for MVP traffic.

### Scale Scenario: 10 hackathons/month, 500 submissions each

Writes: 7,000 WCU-seconds per hackathon × 10 = 70,000 WCU-seconds/month.
Spread across ~10 analysis windows: peaks at ~50 WCU for short bursts.

**Recommendation:** Stay on provisioned mode with auto-scaling (min: 5, max: 50) for growth. Switch to on-demand only if traffic becomes truly unpredictable.

---

## 10. SAM Template Fragment

```yaml
# template.yaml (DynamoDB section)
Resources:
  VibeJudgeTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: !Sub "${AWS::StackName}-table"
      BillingMode: PROVISIONED
      TableClass: STANDARD
      ProvisionedThroughput:
        ReadCapacityUnits: 5
        WriteCapacityUnits: 5
      AttributeDefinitions:
        - AttributeName: PK
          AttributeType: S
        - AttributeName: SK
          AttributeType: S
        - AttributeName: GSI1PK
          AttributeType: S
        - AttributeName: GSI1SK
          AttributeType: S
        - AttributeName: GSI2PK
          AttributeType: S
        - AttributeName: GSI2SK
          AttributeType: S
      KeySchema:
        - AttributeName: PK
          KeyType: HASH
        - AttributeName: SK
          KeyType: RANGE
      GlobalSecondaryIndexes:
        - IndexName: GSI1
          KeySchema:
            - AttributeName: GSI1PK
              KeyType: HASH
            - AttributeName: GSI1SK
              KeyType: RANGE
          Projection:
            ProjectionType: ALL
          ProvisionedThroughput:
            ReadCapacityUnits: 5
            WriteCapacityUnits: 5
        - IndexName: GSI2
          KeySchema:
            - AttributeName: GSI2PK
              KeyType: HASH
            - AttributeName: GSI2SK
              KeyType: RANGE
          Projection:
            ProjectionType: KEYS_ONLY
          ProvisionedThroughput:
            ReadCapacityUnits: 5
            WriteCapacityUnits: 5
      TimeToLiveSpecification:
        AttributeName: expires_at
        Enabled: true
      Tags:
        - Key: Project
          Value: VibeJudge
        - Key: Environment
          Value: !Ref Environment
```

---

## 11. Seed Data

### Demo Organizer
```json
{
  "PK": "ORG#01JKXYZ1234567890ABCDE",
  "SK": "PROFILE",
  "entity_type": "ORGANIZER",
  "org_id": "01JKXYZ1234567890ABCDE",
  "email": "demo@vibejudge.ai",
  "name": "Demo Organizer",
  "organization": "Vibe Coders",
  "tier": "premium",
  "hackathon_count": 1,
  "created_at": "2026-02-13T00:00:00Z",
  "updated_at": "2026-02-13T00:00:00Z",
  "GSI1PK": "EMAIL#demo@vibejudge.ai",
  "GSI1SK": "ORG#01JKXYZ1234567890ABCDE"
}
```

### Demo Hackathon
```json
{
  "PK": "ORG#01JKXYZ1234567890ABCDE",
  "SK": "HACK#01JKXYZ9876543210FGHIJ",
  "entity_type": "HACKATHON",
  "hack_id": "01JKXYZ9876543210FGHIJ",
  "org_id": "01JKXYZ1234567890ABCDE",
  "name": "AWS Bedrock Builders Hackathon",
  "status": "configured",
  "submission_count": 3,
  "created_at": "2026-02-13T00:00:00Z",
  "updated_at": "2026-02-13T00:00:00Z",
  "GSI1PK": "HACK#01JKXYZ9876543210FGHIJ",
  "GSI1SK": "META"
}
```

### Demo HackathonDetail
```json
{
  "PK": "HACK#01JKXYZ9876543210FGHIJ",
  "SK": "META",
  "entity_type": "HACKATHON_DETAIL",
  "hack_id": "01JKXYZ9876543210FGHIJ",
  "org_id": "01JKXYZ1234567890ABCDE",
  "name": "AWS Bedrock Builders Hackathon",
  "description": "Build innovative applications using Amazon Bedrock",
  "status": "configured",
  "start_date": "2026-03-01T00:00:00Z",
  "end_date": "2026-03-02T23:59:59Z",
  "rubric": {
    "name": "AWS Bedrock Challenge",
    "version": "1.0",
    "max_score": 100,
    "dimensions": [
      {"name": "code_quality", "weight": 0.25, "agent": "bug_hunter", "description": "Code quality, security, test coverage"},
      {"name": "architecture", "weight": 0.25, "agent": "performance", "description": "Architecture design, scalability"},
      {"name": "innovation", "weight": 0.30, "agent": "innovation", "description": "Technical innovation, creativity"},
      {"name": "authenticity", "weight": 0.20, "agent": "ai_detection", "description": "Development authenticity"}
    ]
  },
  "agents_enabled": ["bug_hunter", "performance", "innovation", "ai_detection"],
  "ai_policy_mode": "ai_assisted",
  "repo_urls": [
    "https://github.com/demo-team-1/bedrock-chatbot",
    "https://github.com/demo-team-2/rag-pipeline",
    "https://github.com/demo-team-3/nova-image-gen"
  ],
  "submission_count": 3,
  "budget_limit_usd": 5.00,
  "created_at": "2026-02-13T00:00:00Z",
  "updated_at": "2026-02-13T00:00:00Z"
}
```

---

## DynamoDB Helper Functions (Preview — Full implementation in codebase)

```python
# src/utils/dynamo.py

from boto3.dynamodb.conditions import Key
from typing import Any

class DynamoHelper:
    def __init__(self, table):
        self.table = table

    # --- Hackathon Operations ---

    def get_hackathon(self, hack_id: str) -> dict | None:
        """AP4: Get hackathon config by ID."""
        resp = self.table.get_item(Key={"PK": f"HACK#{hack_id}", "SK": "META"})
        return resp.get("Item")

    def list_organizer_hackathons(self, org_id: str) -> list[dict]:
        """AP3: List all hackathons for an organizer."""
        resp = self.table.query(
            KeyConditionExpression=Key("PK").eq(f"ORG#{org_id}") & Key("SK").begins_with("HACK#")
        )
        return resp["Items"]

    # --- Submission Operations ---

    def list_submissions(self, hack_id: str) -> list[dict]:
        """AP6: List all submissions for a hackathon."""
        resp = self.table.query(
            KeyConditionExpression=Key("PK").eq(f"HACK#{hack_id}") & Key("SK").begins_with("SUB#")
        )
        return resp["Items"]

    def get_submission_scores(self, sub_id: str) -> list[dict]:
        """AP9: Get all agent scores for a submission."""
        resp = self.table.query(
            KeyConditionExpression=Key("PK").eq(f"SUB#{sub_id}") & Key("SK").begins_with("SCORE#")
        )
        return resp["Items"]

    def get_submission_costs(self, sub_id: str) -> list[dict]:
        """AP12: Get all cost records for a submission."""
        resp = self.table.query(
            KeyConditionExpression=Key("PK").eq(f"SUB#{sub_id}") & Key("SK").begins_with("COST#")
        )
        return resp["Items"]

    # --- Leaderboard ---

    def get_leaderboard(self, hack_id: str) -> list[dict]:
        """AP16: Get submissions sorted by score (application-side sort)."""
        submissions = self.list_submissions(hack_id)
        return sorted(submissions, key=lambda x: x.get("overall_score", 0), reverse=True)

    # --- Transactional Write (after analysis completes) ---

    def write_analysis_results(self, items: list[dict]) -> None:
        """Atomic write of scores + costs + summary for a submission."""
        with self.table.batch_writer() as batch:
            for item in items:
                batch.put_item(Item=item)
```

---

*End of DynamoDB Data Model v1.0*  
*Next deliverable: #4 — Agent Prompt Library*
