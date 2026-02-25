"""VibeJudge AI — Pydantic Models.

All request/response schemas, agent output schemas, and internal data models.
"""

# Common
# Analysis
from src.models.analysis import (
    AnalysisCurrentSubmission,
    AnalysisError,
    AnalysisJobResponse,
    AnalysisProgress,
    AnalysisStatusResponse,
    AnalysisTrigger,
    CommitInfo,
    DiffEntry,
    RepoData,
    SourceFile,
    WorkflowRun,
)
from src.models.common import (
    AgentName,
    AIPolicyMode,
    HackathonStatus,
    JobStatus,
    Recommendation,
    ServiceTier,
    Severity,
    SubmissionStatus,
    Tier,
    TimestampMixin,
    VibeJudgeBase,
)

# Costs
from src.models.costs import (
    AgentCostEstimate,
    BudgetCheck,
    BudgetInfo,
    CostEstimate,
    CostEstimateDetail,
    CostRange,
    CostRecord,
    HackathonCostResponse,
    SubmissionCostResponse,
)

# Errors
from src.models.errors import (
    ErrorDetail,
    ErrorResponse,
)

# Hackathon
from src.models.hackathon import (
    HackathonCreate,
    HackathonListItem,
    HackathonListResponse,
    HackathonResponse,
    HackathonUpdate,
    RubricConfig,
    RubricDimension,
)

# Leaderboard
from src.models.leaderboard import (
    LeaderboardEntry,
    LeaderboardHackathonInfo,
    LeaderboardResponse,
    LeaderboardStats,
)

# Organizer
from src.models.organizer import (
    OrganizerCreate,
    OrganizerCreateResponse,
    OrganizerLogin,
    OrganizerLoginResponse,
    OrganizerRecord,
    OrganizerResponse,
)

# Scores
from src.models.scores import (
    AGENT_RESPONSE_MODELS,
    AIDetectionEvidence,
    AIDetectionResponse,
    AIDetectionScores,
    BaseAgentResponse,
    BugHunterEvidence,
    BugHunterResponse,
    BugHunterScores,
    CIObservations,
    CommitAnalysis,
    InnovationEvidence,
    InnovationResponse,
    InnovationScores,
    PerformanceCIObservations,
    PerformanceEvidence,
    PerformanceResponse,
    PerformanceScores,
    TechStackAssessment,
)

# Submission
from src.models.submission import (
    RepoMeta,
    SubmissionBatchCreate,
    SubmissionBatchCreateResponse,
    SubmissionInput,
    SubmissionListItem,
    SubmissionListResponse,
    SubmissionResponse,
    WeightedDimensionScore,
)

__all__ = [
    # Common
    "HackathonStatus",
    "SubmissionStatus",
    "JobStatus",
    "AgentName",
    "AIPolicyMode",
    "Tier",
    "Severity",
    "Recommendation",
    "ServiceTier",
    "VibeJudgeBase",
    "TimestampMixin",
    # Organizer
    "OrganizerCreate",
    "OrganizerLogin",
    "OrganizerResponse",
    "OrganizerCreateResponse",
    "OrganizerLoginResponse",
    "OrganizerRecord",
    # Hackathon
    "RubricDimension",
    "RubricConfig",
    "HackathonCreate",
    "HackathonUpdate",
    "HackathonResponse",
    "HackathonListItem",
    "HackathonListResponse",
    # Submission
    "SubmissionInput",
    "SubmissionBatchCreate",
    "RepoMeta",
    "WeightedDimensionScore",
    "SubmissionResponse",
    "SubmissionListItem",
    "SubmissionListResponse",
    "SubmissionBatchCreateResponse",
    # Scores
    "BugHunterEvidence",
    "PerformanceEvidence",
    "InnovationEvidence",
    "AIDetectionEvidence",
    "CIObservations",
    "PerformanceCIObservations",
    "TechStackAssessment",
    "CommitAnalysis",
    "BaseAgentResponse",
    "BugHunterScores",
    "BugHunterResponse",
    "PerformanceScores",
    "PerformanceResponse",
    "InnovationScores",
    "InnovationResponse",
    "AIDetectionScores",
    "AIDetectionResponse",
    "AGENT_RESPONSE_MODELS",
    # Costs
    "CostRecord",
    "BudgetInfo",
    "SubmissionCostResponse",
    "HackathonCostResponse",
    "CostRange",
    "AgentCostEstimate",
    "BudgetCheck",
    "CostEstimateDetail",
    "CostEstimate",
    # Analysis
    "AnalysisTrigger",
    "AnalysisJobResponse",
    "AnalysisProgress",
    "AnalysisCurrentSubmission",
    "AnalysisError",
    "AnalysisStatusResponse",
    "SourceFile",
    "CommitInfo",
    "DiffEntry",
    "WorkflowRun",
    "RepoData",
    # Leaderboard
    "LeaderboardEntry",
    "LeaderboardStats",
    "LeaderboardHackathonInfo",
    "LeaderboardResponse",
    # Errors
    "ErrorDetail",
    "ErrorResponse",
]
