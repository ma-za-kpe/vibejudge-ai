"""Submission and scoring models."""

from datetime import datetime

from pydantic import Field, HttpUrl, field_validator

from src.models.common import (
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
