"""VibeJudge AI — Pydantic Models.

All request/response schemas, agent output schemas, and internal data models.
"""

# Common
from src.models.common import (
    HackathonStatus, SubmissionStatus, JobStatus, AgentName,
    AIPolicyMode, Tier, Severity, Recommendation, ServiceTier,
    VibeJudgeBase, TimestampMixin,
)

# Organizer
from src.models.organizer import (
    OrganizerCreate, OrganizerLogin,
    OrganizerResponse, OrganizerCreateResponse, OrganizerLoginResponse,
    OrganizerRecord,
)

# Hackathon
from src.models.hackathon import (
    RubricDimension, RubricConfig,
    HackathonCreate, HackathonUpdate,
    HackathonResponse, HackathonListItem, HackathonListResponse,
)

# Submission
from src.models.submission import (
    SubmissionInput, SubmissionBatchCreate,
    RepoMeta, WeightedDimensionScore,
    SubmissionResponse, SubmissionListItem, SubmissionListResponse,
    SubmissionBatchCreateResponse,
)

# Scores
from src.models.scores import (
    BugHunterEvidence, PerformanceEvidence, InnovationEvidence, AIDetectionEvidence,
    CIObservations, PerformanceCIObservations, TechStackAssessment, CommitAnalysis,
    BaseAgentResponse, BugHunterScores, BugHunterResponse,
    PerformanceScores, PerformanceResponse,
    InnovationScores, InnovationResponse,
    AIDetectionScores, AIDetectionResponse,
    AGENT_RESPONSE_MODELS,
)

# Costs
from src.models.costs import (
    CostRecord, BudgetInfo, SubmissionCostResponse, HackathonCostResponse,
    CostRange, AgentCostEstimate, BudgetCheck, CostEstimateDetail, CostEstimate,
)

# Analysis
from src.models.analysis import (
    AnalysisTrigger, AnalysisJobResponse, AnalysisProgress,
    AnalysisCurrentSubmission, AnalysisError, AnalysisStatusResponse,
    SourceFile, CommitInfo, DiffEntry, WorkflowRun, RepoData,
)

# Leaderboard
from src.models.leaderboard import (
    LeaderboardEntry, LeaderboardStats, LeaderboardHackathonInfo,
    LeaderboardResponse,
)

# Errors
from src.models.errors import (
    ErrorDetail, ErrorResponse,
)

__all__ = [
    # Common
    "HackathonStatus", "SubmissionStatus", "JobStatus", "AgentName",
    "AIPolicyMode", "Tier", "Severity", "Recommendation", "ServiceTier",
    "VibeJudgeBase", "TimestampMixin",
    # Organizer
    "OrganizerCreate", "OrganizerLogin",
    "OrganizerResponse", "OrganizerCreateResponse", "OrganizerLoginResponse",
    "OrganizerRecord",
    # Hackathon
    "RubricDimension", "RubricConfig",
    "HackathonCreate", "HackathonUpdate",
    "HackathonResponse", "HackathonListItem", "HackathonListResponse",
    # Submission
    "SubmissionInput", "SubmissionBatchCreate",
    "RepoMeta", "WeightedDimensionScore",
    "SubmissionResponse", "SubmissionListItem", "SubmissionListResponse",
    "SubmissionBatchCreateResponse",
    # Scores
    "BugHunterEvidence", "PerformanceEvidence", "InnovationEvidence", "AIDetectionEvidence",
    "CIObservations", "PerformanceCIObservations", "TechStackAssessment", "CommitAnalysis",
    "BaseAgentResponse", "BugHunterScores", "BugHunterResponse",
    "PerformanceScores", "PerformanceResponse",
    "InnovationScores", "InnovationResponse",
    "AIDetectionScores", "AIDetectionResponse",
    "AGENT_RESPONSE_MODELS",
    # Costs
    "CostRecord", "BudgetInfo", "SubmissionCostResponse", "HackathonCostResponse",
    "CostRange", "AgentCostEstimate", "BudgetCheck", "CostEstimateDetail", "CostEstimate",
    # Analysis
    "AnalysisTrigger", "AnalysisJobResponse", "AnalysisProgress",
    "AnalysisCurrentSubmission", "AnalysisError", "AnalysisStatusResponse",
    "SourceFile", "CommitInfo", "DiffEntry", "WorkflowRun", "RepoData",
    # Leaderboard
    "LeaderboardEntry", "LeaderboardStats", "LeaderboardHackathonInfo",
    "LeaderboardResponse",
    # Errors
    "ErrorDetail", "ErrorResponse",
]
