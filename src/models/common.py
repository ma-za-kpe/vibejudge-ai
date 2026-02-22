"""Common base models and utilities shared across all VibeJudge models."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

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
