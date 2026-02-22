"""Agent scoring models — validated output schemas for LLM responses."""

from pydantic import Field, field_validator

from src.models.common import VibeJudgeBase, AgentName, Severity


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
    confidence: float = Field(default=1.0, ge=0, le=1)

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
