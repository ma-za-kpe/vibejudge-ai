"""Hackathon configuration models."""

from datetime import datetime

from pydantic import Field, field_validator

from src.models.common import (
    AgentName,
    AIPolicyMode,
    HackathonStatus,
    TimestampMixin,
    VibeJudgeBase,
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
                raise ValueError(f"Rubric references agents not in agents_enabled: {missing}")
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
    org_id: str
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
