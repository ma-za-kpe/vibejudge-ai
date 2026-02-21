"""Analysis job and orchestration models."""

from datetime import datetime

from pydantic import Field

from src.models.common import VibeJudgeBase, JobStatus, AgentName
from src.models.submission import RepoMeta


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


class RepoData(VibeJudgeBase):
    """Extracted repository data passed to agents.
    
    This is the INTERNAL representation — not exposed via API.
    Built by git_analyzer.py after cloning a repo.
    """
    repo_url: str
    repo_owner: str
    repo_name: str
    default_branch: str = "main"
    meta: RepoMeta
    file_tree: str = ""
    readme_content: str = ""
    source_files: list[SourceFile] = Field(default_factory=list)
    commit_history: list[CommitInfo] = Field(default_factory=list)
    diff_summary: list[DiffEntry] = Field(default_factory=list)
    workflow_definitions: list[str] = Field(default_factory=list)
    workflow_runs: list[WorkflowRun] = Field(default_factory=list)
