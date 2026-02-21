"""Leaderboard response models."""

from src.models.common import VibeJudgeBase, Recommendation


class LeaderboardEntry(VibeJudgeBase):
    """Single entry in the leaderboard."""
    rank: int
    sub_id: str
    team_name: str
    overall_score: float
    dimension_scores: dict[str, float]
    recommendation: Recommendation


class LeaderboardStats(VibeJudgeBase):
    """Statistical summary of scores."""
    mean_score: float
    median_score: float
    std_dev: float
    highest_score: float
    lowest_score: float
    score_distribution: dict[str, int]  # {"90-100": 0, "80-89": 2, ...}


class LeaderboardHackathonInfo(VibeJudgeBase):
    """Hackathon metadata for leaderboard context."""
    hack_id: str
    name: str
    submission_count: int
    analyzed_count: int
    ai_policy_mode: str


class LeaderboardResponse(VibeJudgeBase):
    """GET /api/v1/hackathons/{hack_id}/leaderboard"""
    hackathon: LeaderboardHackathonInfo
    leaderboard: list[LeaderboardEntry]
    statistics: LeaderboardStats
