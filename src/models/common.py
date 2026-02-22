"""Common base models and utilities shared across all VibeJudge models."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

# ============================================================
# ENUMS
# ============================================================


class HackathonStatus(StrEnum):
    DRAFT = "draft"
    CONFIGURED = "configured"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class SubmissionStatus(StrEnum):
    PENDING = "pending"
    CLONING = "cloning"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentName(StrEnum):
    BUG_HUNTER = "bug_hunter"
    PERFORMANCE = "performance"
    INNOVATION = "innovation"
    AI_DETECTION = "ai_detection"


class AIPolicyMode(StrEnum):
    FULL_VIBE = "full_vibe"
    AI_ASSISTED = "ai_assisted"
    TRADITIONAL = "traditional"
    CUSTOM = "custom"


class Tier(StrEnum):
    FREE = "free"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Recommendation(StrEnum):
    STRONG_CONTENDER = "strong_contender"
    SOLID_SUBMISSION = "solid_submission"
    NEEDS_IMPROVEMENT = "needs_improvement"
    CONCERNS_FLAGGED = "concerns_flagged"


class ServiceTier(StrEnum):
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
