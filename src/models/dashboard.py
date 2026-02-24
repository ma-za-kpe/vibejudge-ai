"""Organizer intelligence dashboard models."""

from pydantic import Field

from src.models.common import VibeJudgeBase
from src.models.team_dynamics import IndividualScorecard


# ============================================================
# DASHBOARD MODELS
# ============================================================


class TopPerformer(VibeJudgeBase):
    """Top performing team."""
    team_name: str
    sub_id: str
    overall_score: float
    key_strengths: list[str]
    sponsor_interest_flags: list[str] = Field(default_factory=list)


class HiringIntelligence(VibeJudgeBase):
    """Hiring intelligence by role."""
    backend_candidates: list[IndividualScorecard] = Field(default_factory=list)
    frontend_candidates: list[IndividualScorecard] = Field(default_factory=list)
    devops_candidates: list[IndividualScorecard] = Field(default_factory=list)
    full_stack_candidates: list[IndividualScorecard] = Field(default_factory=list)
    must_interview: list[IndividualScorecard] = Field(default_factory=list)


class TechnologyTrends(VibeJudgeBase):
    """Technology trend analysis."""
    most_used: list[tuple[str, int]]  # (technology, count)
    emerging: list[str] = Field(default_factory=list)
    popular_stacks: list[tuple[str, int]] = Field(default_factory=list)  # (stack combination, count)


class CommonIssue(VibeJudgeBase):
    """Common issue across submissions."""
    issue_type: str
    percentage_affected: float
    workshop_recommendation: str
    example_teams: list[str] = Field(default_factory=list)


class PrizeRecommendation(VibeJudgeBase):
    """Prize recommendation with evidence."""
    prize_category: str
    recommended_team: str
    sub_id: str
    justification: str
    evidence: list[str] = Field(default_factory=list)


class OrganizerDashboard(VibeJudgeBase):
    """Complete organizer intelligence dashboard."""
    hack_id: str
    hackathon_name: str
    total_submissions: int
    top_performers: list[TopPerformer] = Field(default_factory=list)
    hiring_intelligence: HiringIntelligence
    technology_trends: TechnologyTrends
    common_issues: list[CommonIssue] = Field(default_factory=list)
    standout_moments: list[str] = Field(default_factory=list)
    prize_recommendations: list[PrizeRecommendation] = Field(default_factory=list)
    next_hackathon_recommendations: list[str] = Field(default_factory=list)
    sponsor_follow_up_actions: list[str] = Field(default_factory=list)
