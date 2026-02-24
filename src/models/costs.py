"""Cost tracking models for LLM billing intelligence."""

from src.models.common import AgentName, ServiceTier, VibeJudgeBase


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


class ComponentPerformanceRecord(VibeJudgeBase):
    """Performance tracking for non-AI components (free static analysis).
    
    These components don't use Bedrock, so they have $0 cost, but we track
    their execution time to show performance and cost savings.
    """
    sub_id: str
    hack_id: str
    component_name: str  # team_analyzer | strategy_detector | brand_voice_transformer | actions_analyzer
    duration_ms: int
    findings_count: int = 0  # Number of findings/items produced
    success: bool = True
    error_message: str | None = None


class BudgetInfo(VibeJudgeBase):
    """Budget utilization info."""
    limit_usd: float
    used_usd: float
    remaining_usd: float
    utilization_pct: float


class SubmissionCostResponse(VibeJudgeBase):
    """GET /api/v1/submissions/{sub_id}/costs"""
    sub_id: str
    total_cost_usd: float
    total_tokens: int
    total_input_tokens: int
    total_output_tokens: int
    analysis_duration_ms: int
    agents: list[CostRecord]
    component_performance: list[ComponentPerformanceRecord] = []
    total_component_duration_ms: int = 0


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


class CostEstimateDetail(VibeJudgeBase):
    total_cost_usd: CostRange
    per_submission_cost_usd: CostRange
    cost_by_agent: dict[str, AgentCostEstimate]
    estimated_duration_minutes: CostRange


class CostEstimate(VibeJudgeBase):
    """POST /api/v1/hackathons/{hack_id}/analyze/estimate response."""
    hack_id: str
    submission_count: int
    agents_enabled: list[str]
    estimate: CostEstimateDetail
    budget_check: BudgetCheck | None = None
