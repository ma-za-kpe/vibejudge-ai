"""Feedback transformation data models."""

from pydantic import Field

from src.models.common import VibeJudgeBase


class CodeExample(VibeJudgeBase):
    """Before/after code example."""

    vulnerable_code: str
    fixed_code: str
    explanation: str


class LearningResource(VibeJudgeBase):
    """Learning resource link."""

    title: str
    url: str
    resource_type: str  # documentation | tutorial | guide | video


class EffortEstimate(VibeJudgeBase):
    """Effort estimate for fix."""

    minutes: int
    difficulty: str  # Easy | Moderate | Advanced


class ActionableFeedback(VibeJudgeBase):
    """Transformed feedback item."""

    priority: int = Field(..., ge=1, le=5)
    finding: str
    acknowledgment: str  # What they did right
    context: str  # Why this is common in hackathons
    code_example: CodeExample | None = None
    why_vulnerable: str
    why_fixed: str
    testing_instructions: str
    learning_resources: list[LearningResource] = Field(default_factory=list)
    effort_estimate: EffortEstimate
    business_impact: str
