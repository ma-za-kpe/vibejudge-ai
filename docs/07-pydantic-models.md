# VibeJudge AI — Pydantic Models

> **Version:** 1.0  
> **Date:** February 2026  
> **Author:** Maku Mazakpe / Vibe Coders  
> **Status:** APPROVED  
> **Depends On:** Deliverable #3 (Data Model), #4 (Agent Prompts), #5 (API Spec)  
> **Python:** 3.12 | **Pydantic:** v2.x

---

## Overview

All request/response schemas, internal data structures, and agent output schemas defined as Pydantic v2 models. These models serve triple duty:

1. **FastAPI request/response validation** — auto-validated on every API call
2. **Agent output parsing** — validate LLM JSON responses against strict schemas
3. **DynamoDB serialization** — `.model_dump()` produces DynamoDB-compatible dicts

---

## File: `src/models/common.py`

```python
"""Common base models and utilities shared across all VibeJudge models."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, ConfigDict


# ============================================================
# ENUMS
# ============================================================

class HackathonStatus(str, Enum):
    DRAFT = "draft"
    CONFIGURED = "configured"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class SubmissionStatus(str, Enum):
    PENDING = "pending"
    CLONING = "cloning"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentName(str, Enum):
    BUG_HUNTER = "bug_hunter"
    PERFORMANCE = "performance"
    INNOVATION = "innovation"
    AI_DETECTION = "ai_detection"


class AIPolicyMode(str, Enum):
    FULL_VIBE = "full_vibe"
    AI_ASSISTED = "ai_assisted"
    TRADITIONAL = "traditional"
    CUSTOM = "custom"


class Tier(str, Enum):
    FREE = "free"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Recommendation(str, Enum):
    STRONG_CONTENDER = "strong_contender"
    SOLID_SUBMISSION = "solid_submission"
    NEEDS_IMPROVEMENT = "needs_improvement"
    CONCERNS_FLAGGED = "concerns_flagged"


class ServiceTier(str, Enum):
    STANDARD = "standard"
    FLEX = "flex"


# ============================================================
# BASE MODELS
# ============================================================

class VibeJudgeBase(BaseModel):
    """Base model with shared configuration."""
    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        json_encoders={datetime: lambda v: v.isoformat()},
    )


class TimestampMixin(BaseModel):
    """Mixin for created_at/updated_at fields."""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

---

## File: `src/models/organizer.py`

```python
"""Organizer account models."""

from pydantic import Field, EmailStr

from .common import VibeJudgeBase, TimestampMixin, Tier


# --- Request Models ---

class OrganizerCreate(VibeJudgeBase):
    """POST /api/v1/organizers"""
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)
    organization: str | None = Field(None, max_length=200)


class OrganizerLogin(VibeJudgeBase):
    """POST /api/v1/organizers/login"""
    email: EmailStr


# --- Response Models ---

class OrganizerResponse(VibeJudgeBase, TimestampMixin):
    """GET /api/v1/organizers/me"""
    org_id: str
    email: str
    name: str
    organization: str | None = None
    tier: Tier = Tier.FREE
    hackathon_count: int = 0


class OrganizerCreateResponse(OrganizerResponse):
    """POST /api/v1/organizers — includes one-time API key"""
    api_key: str
    _warning: str = "Store your API key securely. It will not be shown again."


class OrganizerLoginResponse(VibeJudgeBase):
    """POST /api/v1/organizers/login"""
    org_id: str
    api_key: str
    _warning: str = "Previous API key has been invalidated."


# --- Internal / DynamoDB ---

class OrganizerRecord(OrganizerResponse):
    """Full DynamoDB record for organizer."""
    PK: str  # ORG#<org_id>
    SK: str = "PROFILE"
    entity_type: str = "ORGANIZER"
    api_key_hash: str
    GSI1PK: str  # EMAIL#<email>
    GSI1SK: str  # ORG#<org_id>
```

---

## File: `src/models/hackathon.py`

```python
"""Hackathon configuration models."""

from datetime import datetime

from pydantic import Field, field_validator

from .common import (
    VibeJudgeBase, TimestampMixin, HackathonStatus,
    AgentName, AIPolicyMode,
)


# --- Rubric Models ---

class RubricDimension(VibeJudgeBase):
    """A single scoring dimension within a rubric."""
    name: str = Field(..., min_length=1, max_length=50)
    weight: float = Field(..., ge=0.0, le=1.0)
    agent: AgentName
    description: str = Field("", max_length=500)


class RubricConfig(VibeJudgeBase):
    """Complete rubric configuration for a hackathon."""
    name: str = Field("Default Rubric", max_length=200)
    version: str = "1.0"
    max_score: float = 100.0
    dimensions: list[RubricDimension] = Field(..., min_length=1, max_length=10)

    @field_validator("dimensions")
    @classmethod
    def validate_weights_sum(cls, v: list[RubricDimension]) -> list[RubricDimension]:
        total = sum(d.weight for d in v)
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"Dimension weights must sum to 1.0, got {total:.4f}")
        return v


# --- Request Models ---

class HackathonCreate(VibeJudgeBase):
    """POST /api/v1/hackathons"""
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field("", max_length=2000)
    start_date: datetime | None = None
    end_date: datetime | None = None
    rubric: RubricConfig
    agents_enabled: list[AgentName] = Field(..., min_length=1, max_length=4)
    ai_policy_mode: AIPolicyMode = AIPolicyMode.AI_ASSISTED
    ai_policy_config: dict | None = None
    budget_limit_usd: float | None = Field(None, ge=0.01, le=10000.0)

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v, info):
        start = info.data.get("start_date")
        if v and start and v <= start:
            raise ValueError("end_date must be after start_date")
        return v

    @field_validator("agents_enabled")
    @classmethod
    def validate_agents_match_rubric(cls, v, info):
        rubric = info.data.get("rubric")
        if rubric:
            rubric_agents = {d.agent for d in rubric.dimensions}
            enabled_set = set(v)
            missing = rubric_agents - enabled_set
            if missing:
                raise ValueError(
                    f"Rubric references agents not in agents_enabled: {missing}"
                )
        return v


class HackathonUpdate(VibeJudgeBase):
    """PUT /api/v1/hackathons/{hack_id} — all fields optional."""
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=2000)
    start_date: datetime | None = None
    end_date: datetime | None = None
    rubric: RubricConfig | None = None
    agents_enabled: list[AgentName] | None = None
    ai_policy_mode: AIPolicyMode | None = None
    budget_limit_usd: float | None = Field(None, ge=0.01, le=10000.0)


# --- Response Models ---

class HackathonResponse(VibeJudgeBase, TimestampMixin):
    """Standard hackathon response."""
    hack_id: str
    name: str
    description: str = ""
    status: HackathonStatus = HackathonStatus.DRAFT
    start_date: datetime | None = None
    end_date: datetime | None = None
    rubric: RubricConfig
    agents_enabled: list[AgentName]
    ai_policy_mode: AIPolicyMode
    submission_count: int = 0
    budget_limit_usd: float | None = None


class HackathonListItem(VibeJudgeBase):
    """Compact hackathon item for list endpoint."""
    hack_id: str
    name: str
    status: HackathonStatus
    submission_count: int
    created_at: datetime


class HackathonListResponse(VibeJudgeBase):
    """GET /api/v1/hackathons"""
    hackathons: list[HackathonListItem]
    next_cursor: str | None = None
    has_more: bool = False
```

---

## File: `src/models/submission.py`

```python
"""Submission and scoring models."""

from datetime import datetime

from pydantic import Field, HttpUrl, field_validator

from .common import (
    VibeJudgeBase, TimestampMixin, SubmissionStatus,
    Recommendation,
)


# --- Request Models ---

class SubmissionInput(VibeJudgeBase):
    """Single submission within a batch add request."""
    team_name: str = Field(..., min_length=1, max_length=100)
    repo_url: str = Field(..., pattern=r"^https://github\.com/[\w\-\.]+/[\w\-\.]+/?$")


class SubmissionBatchCreate(VibeJudgeBase):
    """POST /api/v1/hackathons/{hack_id}/submissions"""
    submissions: list[SubmissionInput] = Field(..., min_length=1, max_length=500)


# --- Repo Metadata ---

class RepoMeta(VibeJudgeBase):
    """Extracted metadata from a cloned repository."""
    commit_count: int = 0
    branch_count: int = 0
    contributor_count: int = 0
    primary_language: str | None = None
    languages: dict[str, float] = Field(default_factory=dict)  # {lang: percentage}
    total_files: int = 0
    total_lines: int = 0
    has_readme: bool = False
    has_tests: bool = False
    has_ci: bool = False
    has_dockerfile: bool = False
    first_commit_at: datetime | None = None
    last_commit_at: datetime | None = None
    development_duration_hours: float = 0.0
    workflow_run_count: int = 0
    workflow_success_rate: float = 0.0


# --- Weighted Score ---

class WeightedDimensionScore(VibeJudgeBase):
    """A single dimension's weighted score breakdown."""
    raw: float = Field(..., ge=0, le=10)
    weight: float = Field(..., ge=0, le=1)
    weighted: float = Field(..., ge=0, le=100)


# --- Response Models ---

class SubmissionResponse(VibeJudgeBase, TimestampMixin):
    """GET /api/v1/submissions/{sub_id}"""
    sub_id: str
    hack_id: str
    team_name: str
    repo_url: str
    status: SubmissionStatus
    overall_score: float | None = None
    rank: int | None = None
    recommendation: Recommendation | None = None
    repo_meta: RepoMeta | None = None
    weighted_scores: dict[str, WeightedDimensionScore] | None = None
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    agent_scores: dict[str, float] = Field(default_factory=dict)
    total_cost_usd: float | None = None
    total_tokens: int | None = None
    analysis_duration_ms: int | None = None
    analyzed_at: datetime | None = None


class SubmissionListItem(VibeJudgeBase):
    """Compact submission item for list endpoint."""
    sub_id: str
    team_name: str
    repo_url: str
    status: SubmissionStatus
    overall_score: float | None = None
    rank: int | None = None
    total_cost_usd: float | None = None
    created_at: datetime


class SubmissionListResponse(VibeJudgeBase):
    """GET /api/v1/hackathons/{hack_id}/submissions"""
    submissions: list[SubmissionListItem]
    next_cursor: str | None = None
    has_more: bool = False


class SubmissionBatchCreateResponse(VibeJudgeBase):
    """POST /api/v1/hackathons/{hack_id}/submissions response."""
    created: int
    submissions: list[SubmissionListItem]
    hackathon_submission_count: int
```

---

## File: `src/models/scores.py`

```python
"""Agent scoring models — validated output schemas for LLM responses."""

from pydantic import Field, field_validator

from .common import VibeJudgeBase, AgentName, Severity


# ============================================================
# EVIDENCE MODELS
# ============================================================

class BugHunterEvidence(VibeJudgeBase):
    """Evidence item from BugHunter agent."""
    finding: str
    file: str
    line: int | None = None
    severity: Severity
    category: str  # bug | security | code_smell | testing | dependency
    recommendation: str


class PerformanceEvidence(VibeJudgeBase):
    """Evidence item from PerformanceAnalyzer agent."""
    finding: str
    file: str
    line: int | None = None
    severity: Severity
    category: str  # architecture | database | api | scalability | efficiency
    recommendation: str


class InnovationEvidence(VibeJudgeBase):
    """Evidence item from InnovationScorer agent."""
    finding: str
    file: str  # Can be "git_history" or "README.md"
    line: int | None = None
    impact: str  # breakthrough | significant | notable | minor
    category: str  # novelty | creativity | elegance | documentation | demo
    detail: str


class AIDetectionEvidence(VibeJudgeBase):
    """Evidence item from AIDetectionAnalyst agent."""
    finding: str
    source: str  # commit_history | file_analysis | actions_data | timing_analysis
    detail: str
    signal: str  # human | ai_generated | ai_assisted | ambiguous
    confidence: float = Field(..., ge=0, le=1)


# ============================================================
# CI OBSERVATIONS
# ============================================================

class CIObservations(VibeJudgeBase):
    """CI/CD observations from BugHunter."""
    has_ci: bool = False
    has_automated_tests: bool = False
    has_linting: bool = False
    has_security_scanning: bool = False
    build_success_rate: float | None = None
    notable_findings: str | None = None


class PerformanceCIObservations(VibeJudgeBase):
    """CI/CD observations from PerformanceAnalyzer."""
    has_ci: bool = False
    build_optimization: str | None = None
    deployment_sophistication: str = "none"  # none | basic | intermediate | advanced
    infrastructure_as_code: bool = False
    notable_findings: str | None = None


class TechStackAssessment(VibeJudgeBase):
    """Technology stack assessment from PerformanceAnalyzer."""
    technologies_identified: list[str] = Field(default_factory=list)
    stack_appropriateness: str = ""
    notable_choices: str = ""


class CommitAnalysis(VibeJudgeBase):
    """Commit pattern analysis from AIDetectionAnalyst."""
    total_commits: int = 0
    avg_lines_per_commit: float = 0
    largest_commit_lines: int = 0
    commit_frequency_pattern: str = "steady"  # steady|burst|front_loaded|back_loaded|sporadic
    meaningful_message_ratio: float = 0
    fix_commit_count: int = 0
    refactor_commit_count: int = 0


# ============================================================
# AGENT RESPONSE MODELS (parsed from LLM JSON output)
# ============================================================

class BaseAgentResponse(VibeJudgeBase):
    """Base fields shared by all agent responses."""
    agent: str
    prompt_version: str
    overall_score: float = Field(..., ge=0, le=10)
    summary: str

    @field_validator("overall_score")
    @classmethod
    def clamp_score(cls, v: float) -> float:
        return max(0.0, min(10.0, round(v, 2)))


class BugHunterScores(VibeJudgeBase):
    code_quality: float = Field(..., ge=0, le=10)
    security: float = Field(..., ge=0, le=10)
    test_coverage: float = Field(..., ge=0, le=10)
    error_handling: float = Field(..., ge=0, le=10)
    dependency_hygiene: float = Field(..., ge=0, le=10)


class BugHunterResponse(BaseAgentResponse):
    """Validated output from BugHunter agent."""
    agent: str = "bug_hunter"
    scores: BugHunterScores
    evidence: list[BugHunterEvidence] = Field(default_factory=list, max_length=10)
    ci_observations: CIObservations = Field(default_factory=CIObservations)


class PerformanceScores(VibeJudgeBase):
    architecture: float = Field(..., ge=0, le=10)
    database_design: float = Field(..., ge=0, le=10)
    api_design: float = Field(..., ge=0, le=10)
    scalability: float = Field(..., ge=0, le=10)
    resource_efficiency: float = Field(..., ge=0, le=10)


class PerformanceResponse(BaseAgentResponse):
    """Validated output from PerformanceAnalyzer agent."""
    agent: str = "performance"
    scores: PerformanceScores
    evidence: list[PerformanceEvidence] = Field(default_factory=list, max_length=10)
    ci_observations: PerformanceCIObservations = Field(
        default_factory=PerformanceCIObservations
    )
    tech_stack_assessment: TechStackAssessment = Field(
        default_factory=TechStackAssessment
    )


class InnovationScores(VibeJudgeBase):
    technical_novelty: float = Field(..., ge=0, le=10)
    creative_problem_solving: float = Field(..., ge=0, le=10)
    architecture_elegance: float = Field(..., ge=0, le=10)
    readme_quality: float = Field(..., ge=0, le=10)
    demo_potential: float = Field(..., ge=0, le=10)


class InnovationResponse(BaseAgentResponse):
    """Validated output from InnovationScorer agent."""
    agent: str = "innovation"
    scores: InnovationScores
    evidence: list[InnovationEvidence] = Field(default_factory=list, max_length=8)
    innovation_highlights: list[str] = Field(default_factory=list, max_length=3)
    development_story: str = ""
    hackathon_context_assessment: str = ""


class AIDetectionScores(VibeJudgeBase):
    commit_authenticity: float = Field(..., ge=0, le=10)
    development_velocity: float = Field(..., ge=0, le=10)
    authorship_consistency: float = Field(..., ge=0, le=10)
    iteration_depth: float = Field(..., ge=0, le=10)
    ai_generation_indicators: float = Field(..., ge=0, le=10)  # INVERTED: 10=no AI


class AIDetectionResponse(BaseAgentResponse):
    """Validated output from AIDetectionAnalyst agent."""
    agent: str = "ai_detection"
    scores: AIDetectionScores
    evidence: list[AIDetectionEvidence] = Field(default_factory=list, max_length=8)
    commit_analysis: CommitAnalysis = Field(default_factory=CommitAnalysis)
    ai_policy_observation: str = ""


# ============================================================
# AGENT RESPONSE TYPE MAPPING
# ============================================================

AGENT_RESPONSE_MODELS: dict[str, type[BaseAgentResponse]] = {
    "bug_hunter": BugHunterResponse,
    "performance": PerformanceResponse,
    "innovation": InnovationResponse,
    "ai_detection": AIDetectionResponse,
}
```

---

## File: `src/models/costs.py`

```python
"""Cost tracking models for LLM billing intelligence."""

from .common import VibeJudgeBase, AgentName, ServiceTier


class CostRecord(VibeJudgeBase):
    """Per-agent cost record for a single submission."""
    sub_id: str
    hack_id: str
    agent_name: AgentName
    model_id: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    input_cost_usd: float
    output_cost_usd: float
    total_cost_usd: float
    latency_ms: int
    service_tier: ServiceTier = ServiceTier.STANDARD
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0


class SubmissionCostResponse(VibeJudgeBase):
    """GET /api/v1/submissions/{sub_id}/costs"""
    sub_id: str
    total_cost_usd: float
    total_tokens: int
    total_input_tokens: int
    total_output_tokens: int
    analysis_duration_ms: int
    agents: list[CostRecord]


class HackathonCostResponse(VibeJudgeBase):
    """GET /api/v1/hackathons/{hack_id}/costs"""
    hack_id: str
    total_cost_usd: float
    total_input_tokens: int
    total_output_tokens: int
    submissions_analyzed: int
    avg_cost_per_submission: float
    cost_by_agent: dict[str, float]
    cost_by_model: dict[str, float]
    budget: BudgetInfo | None = None
    optimization_tips: list[str] = []


class BudgetInfo(VibeJudgeBase):
    """Budget utilization info."""
    limit_usd: float
    used_usd: float
    remaining_usd: float
    utilization_pct: float


class CostEstimate(VibeJudgeBase):
    """POST /api/v1/hackathons/{hack_id}/analyze/estimate response."""
    hack_id: str
    submission_count: int
    agents_enabled: list[str]
    estimate: CostEstimateDetail
    budget_check: BudgetCheck | None = None


class CostEstimateDetail(VibeJudgeBase):
    total_cost_usd: CostRange
    per_submission_cost_usd: CostRange
    cost_by_agent: dict[str, AgentCostEstimate]
    estimated_duration_minutes: CostRange


class CostRange(VibeJudgeBase):
    low: float
    expected: float
    high: float


class AgentCostEstimate(VibeJudgeBase):
    model: str
    estimated_usd: float


class BudgetCheck(VibeJudgeBase):
    budget_limit_usd: float
    within_budget: bool
    budget_utilization_pct: float
```

---

## File: `src/models/analysis.py`

```python
"""Analysis job and orchestration models."""

from datetime import datetime

from pydantic import Field

from .common import VibeJudgeBase, JobStatus, AgentName


# --- Request Models ---

class AnalysisTrigger(VibeJudgeBase):
    """POST /api/v1/hackathons/{hack_id}/analyze"""
    submission_ids: list[str] | None = None  # None = analyze all pending
    force_reanalyze: bool = False


# --- Response Models ---

class AnalysisJobResponse(VibeJudgeBase):
    """Analysis job status."""
    job_id: str
    hack_id: str
    status: JobStatus
    total_submissions: int
    completed_submissions: int = 0
    failed_submissions: int = 0
    estimated_cost_usd: float | None = None
    estimated_duration_minutes: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime


class AnalysisProgress(VibeJudgeBase):
    """Detailed progress information."""
    total_submissions: int
    completed: int
    failed: int
    remaining: int
    percent_complete: float


class AnalysisCurrentSubmission(VibeJudgeBase):
    """Currently processing submission info."""
    sub_id: str
    team_name: str
    status: str
    current_agent: AgentName | None = None


class AnalysisError(VibeJudgeBase):
    """Error detail for a failed submission."""
    sub_id: str
    team_name: str
    error: str


class AnalysisStatusResponse(VibeJudgeBase):
    """GET /api/v1/hackathons/{hack_id}/analyze/status"""
    job_id: str
    hack_id: str
    status: JobStatus
    progress: AnalysisProgress
    current_submission: AnalysisCurrentSubmission | None = None
    cost_so_far: dict | None = None
    errors: list[AnalysisError] = Field(default_factory=list)
    started_at: datetime | None = None
    estimated_completion: datetime | None = None


# --- Internal Models ---

class RepoData(VibeJudgeBase):
    """Extracted repository data passed to agents.

    This is the INTERNAL representation — not exposed via API.
    Built by git_analyzer.py after cloning a repo.
    """
    repo_url: str
    repo_owner: str
    repo_name: str
    default_branch: str = "main"
    meta: "RepoMeta"  # from submission.py
    file_tree: str = ""
    readme_content: str = ""
    source_files: list[SourceFile] = Field(default_factory=list)
    commit_history: list[CommitInfo] = Field(default_factory=list)
    diff_summary: list[DiffEntry] = Field(default_factory=list)
    workflow_definitions: list[str] = Field(default_factory=list)
    workflow_runs: list[WorkflowRun] = Field(default_factory=list)


class SourceFile(VibeJudgeBase):
    """A source file included in agent context."""
    path: str
    content: str
    lines: int
    language: str | None = None
    priority: int = 0  # Higher = more important


class CommitInfo(VibeJudgeBase):
    """Simplified commit from git history."""
    hash: str
    short_hash: str
    message: str
    author: str
    timestamp: datetime
    files_changed: int
    insertions: int
    deletions: int


class DiffEntry(VibeJudgeBase):
    """Summary of a significant diff between commits."""
    commit_hash: str
    file_path: str
    change_type: str  # added | modified | deleted | renamed
    insertions: int
    deletions: int
    summary: str = ""


class WorkflowRun(VibeJudgeBase):
    """GitHub Actions workflow run summary."""
    run_id: int
    name: str
    status: str  # completed | in_progress | queued
    conclusion: str | None = None  # success | failure | cancelled | skipped
    created_at: datetime
    updated_at: datetime
    run_attempt: int = 1
```

---

## File: `src/models/leaderboard.py`

```python
"""Leaderboard response models."""

from .common import VibeJudgeBase, Recommendation


class LeaderboardEntry(VibeJudgeBase):
    """Single entry in the leaderboard."""
    rank: int
    sub_id: str
    team_name: str
    overall_score: float
    dimension_scores: dict[str, float]
    recommendation: Recommendation


class LeaderboardStats(VibeJudgeBase):
    """Statistical summary of scores."""
    mean_score: float
    median_score: float
    std_dev: float
    highest_score: float
    lowest_score: float
    score_distribution: dict[str, int]  # {"90-100": 0, "80-89": 2, ...}


class LeaderboardHackathonInfo(VibeJudgeBase):
    """Hackathon metadata for leaderboard context."""
    hack_id: str
    name: str
    submission_count: int
    analyzed_count: int
    ai_policy_mode: str


class LeaderboardResponse(VibeJudgeBase):
    """GET /api/v1/hackathons/{hack_id}/leaderboard"""
    hackathon: LeaderboardHackathonInfo
    leaderboard: list[LeaderboardEntry]
    statistics: LeaderboardStats
```

---

## File: `src/models/errors.py`

```python
"""Error response models."""

from .common import VibeJudgeBase


class ErrorDetail(VibeJudgeBase):
    """Standard error response body."""
    code: str
    message: str
    status: int
    detail: dict | list | str | None = None
    request_id: str | None = None


class ErrorResponse(VibeJudgeBase):
    """Wrapped error response."""
    error: ErrorDetail
```

---

## File: `src/models/__init__.py`

```python
"""VibeJudge AI — Pydantic Models.

All request/response schemas, agent output schemas, and internal data models.
"""

# Common
from .common import (
    HackathonStatus, SubmissionStatus, JobStatus, AgentName,
    AIPolicyMode, Tier, Severity, Recommendation, ServiceTier,
)

# Organizer
from .organizer import (
    OrganizerCreate, OrganizerLogin,
    OrganizerResponse, OrganizerCreateResponse, OrganizerLoginResponse,
)

# Hackathon
from .hackathon import (
    RubricDimension, RubricConfig,
    HackathonCreate, HackathonUpdate,
    HackathonResponse, HackathonListItem, HackathonListResponse,
)

# Submission
from .submission import (
    SubmissionInput, SubmissionBatchCreate,
    RepoMeta, WeightedDimensionScore,
    SubmissionResponse, SubmissionListItem, SubmissionListResponse,
    SubmissionBatchCreateResponse,
)

# Scores
from .scores import (
    BugHunterResponse, PerformanceResponse,
    InnovationResponse, AIDetectionResponse,
    AGENT_RESPONSE_MODELS,
)

# Costs
from .costs import (
    CostRecord, SubmissionCostResponse, HackathonCostResponse,
    CostEstimate,
)

# Analysis
from .analysis import (
    AnalysisTrigger, AnalysisJobResponse, AnalysisStatusResponse,
    RepoData, SourceFile, CommitInfo, DiffEntry, WorkflowRun,
)

# Leaderboard
from .leaderboard import LeaderboardResponse

# Errors
from .errors import ErrorResponse

__all__ = [
    # ... all exported names
]
```

---

*End of Pydantic Models v1.0*  
*Next deliverable: #8 — Git Analysis Spec*
