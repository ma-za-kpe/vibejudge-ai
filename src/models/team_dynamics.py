"""Team dynamics and individual contributor models."""

from enum import StrEnum

from src.models.common import VibeJudgeBase

# ============================================================
# ENUMS
# ============================================================


class ContributorRole(StrEnum):
    """Detected contributor role."""

    BACKEND = "backend"
    FRONTEND = "frontend"
    DEVOPS = "devops"
    FULL_STACK = "full_stack"
    UNKNOWN = "unknown"


class ExpertiseArea(StrEnum):
    """Expertise area."""

    DATABASE = "database"
    SECURITY = "security"
    TESTING = "testing"
    API = "api"
    UI_UX = "ui_ux"
    INFRASTRUCTURE = "infrastructure"


class RedFlagSeverity(StrEnum):
    """Red flag severity."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"


# ============================================================
# MODELS
# ============================================================


class RedFlag(VibeJudgeBase):
    """Concerning team dynamic pattern."""

    flag_type: str  # extreme_imbalance | ghost_contributor | history_rewriting | etc.
    severity: RedFlagSeverity
    description: str
    evidence: str  # Commit hashes, timestamps
    impact: str  # Why this matters
    hiring_impact: str  # Disqualifies from certain roles
    recommended_action: str


class CollaborationPattern(VibeJudgeBase):
    """Detected collaboration pattern."""

    pattern_type: str  # pair_programming | code_review | alternating_commits
    contributors: list[str]
    evidence: str
    positive: bool  # Is this a good pattern?


class WorkStyle(VibeJudgeBase):
    """Work style patterns."""

    commit_frequency: str  # frequent | moderate | infrequent
    avg_commit_size: int
    active_hours: list[int]  # Hours of day (0-23)
    late_night_commits: int  # 2am-6am
    weekend_commits: int


class HiringSignals(VibeJudgeBase):
    """Hiring recommendations."""

    recommended_role: str
    seniority_level: str  # junior | mid | senior
    salary_range_usd: str  # e.g., "$80k-$100k"
    must_interview: bool
    sponsor_interest: list[str]  # Which sponsors might be interested
    rationale: str


class IndividualScorecard(VibeJudgeBase):
    """Detailed assessment of individual contributor."""

    contributor_name: str
    contributor_email: str
    role: ContributorRole
    expertise_areas: list[ExpertiseArea]
    commit_count: int
    lines_added: int
    lines_deleted: int
    files_touched: list[str]
    notable_contributions: list[str]  # Commits with >500 insertions
    strengths: list[str]
    weaknesses: list[str]
    growth_areas: list[str]
    work_style: WorkStyle
    hiring_signals: HiringSignals


class TeamAnalysisResult(VibeJudgeBase):
    """Result from team dynamics analysis."""

    workload_distribution: dict[str, float]  # contributor -> percentage
    collaboration_patterns: list[CollaborationPattern]
    red_flags: list[RedFlag]
    individual_scorecards: list[IndividualScorecard]
    team_dynamics_grade: str  # A-F
    commit_message_quality: float  # 0-1
    panic_push_detected: bool
    duration_ms: int
