"""Strategy analysis data models."""

from enum import Enum

from pydantic import Field

from src.models.common import VibeJudgeBase


class TestStrategy(str, Enum):
    """Test strategy classification."""
    UNIT_FOCUSED = "unit_focused"
    INTEGRATION_FOCUSED = "integration_focused"
    E2E_FOCUSED = "e2e_focused"
    CRITICAL_PATH = "critical_path"
    DEMO_FIRST = "demo_first"
    NO_TESTS = "no_tests"


class MaturityLevel(str, Enum):
    """Team maturity level."""
    JUNIOR = "junior"  # Tutorial-following
    MID = "mid"  # Solid fundamentals
    SENIOR = "senior"  # Production thinking


class Tradeoff(VibeJudgeBase):
    """Detected architecture tradeoff."""
    tradeoff_type: str  # speed_vs_security | simplicity_vs_scalability
    decision: str  # What they chose
    rationale: str  # Why this makes sense for hackathon
    impact_on_score: str  # How this affects scoring


class LearningJourney(VibeJudgeBase):
    """Detected learning during hackathon."""
    technology: str
    evidence: list[str]  # Commit messages
    progression: str  # How they improved
    impressive: bool  # Is this noteworthy?


class StrategyAnalysisResult(VibeJudgeBase):
    """Result from strategy detection."""
    test_strategy: TestStrategy
    critical_path_focus: bool
    tradeoffs: list[Tradeoff] = Field(default_factory=list)
    learning_journey: LearningJourney | None = None
    maturity_level: MaturityLevel
    strategic_context: str  # Overall context for scoring
    duration_ms: int
