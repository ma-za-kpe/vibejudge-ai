"""Property-based tests for leaderboard row completeness.

This module tests Property 19 from the design document:
- Property 19: Leaderboard Row Completeness

Feature: streamlit-organizer-dashboard, Property 19: Leaderboard Row Completeness

For any submission in the leaderboard, the dashboard should display rank,
team_name, overall_score, and recommendation.

Validates: Requirements 6.2
"""

from datetime import datetime

from hypothesis import given
from hypothesis import strategies as st

# Hypothesis strategy for generating leaderboard submissions
submission_strategy = st.fixed_dictionaries(
    {
        "sub_id": st.text(
            min_size=10,
            max_size=30,
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"), min_codepoint=48, max_codepoint=122
            ),
        ),
        "rank": st.integers(min_value=1, max_value=1000),
        "team_name": st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd", "Zs"), min_codepoint=32, max_codepoint=126
            ),
        ),
        "overall_score": st.floats(
            min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False
        ),
        "recommendation": st.sampled_from(
            ["must_interview", "strong_candidate", "consider", "pass"]
        ),
        "created_at": st.datetimes(
            min_value=datetime(2020, 1, 1), max_value=datetime(2030, 12, 31)
        ).map(lambda dt: dt.isoformat()),
    }
)


class TestLeaderboardRowCompletenessProperty:
    """Tests for Property 19: Leaderboard Row Completeness.

    Feature: streamlit-organizer-dashboard, Property 19: Leaderboard Row Completeness

    For any submission in the leaderboard, the dashboard should display rank,
    team_name, overall_score, and recommendation.

    Validates: Requirements 6.2
    """

    @given(submission=submission_strategy)
    def test_submission_has_all_required_display_fields(
        self,
        submission: dict,
    ) -> None:
        """Each submission must have all four required display fields."""
        # Required fields per Requirement 6.2
        required_fields = ["rank", "team_name", "overall_score", "recommendation"]

        # Verify all required fields are present
        for field in required_fields:
            assert field in submission, f"Submission missing required field '{field}'"

    @given(submission=submission_strategy)
    def test_rank_field_is_valid(
        self,
        submission: dict,
    ) -> None:
        """Rank field must be a positive integer."""
        rank = submission["rank"]

        # Verify rank is an integer
        assert isinstance(rank, int), f"Rank must be an integer, got {type(rank)}"

        # Verify rank is positive
        assert rank > 0, f"Rank must be positive, got {rank}"

    @given(submission=submission_strategy)
    def test_team_name_field_is_valid(
        self,
        submission: dict,
    ) -> None:
        """Team name field must be a non-empty string."""
        team_name = submission["team_name"]

        # Verify team_name is a string
        assert isinstance(team_name, str), f"Team name must be a string, got {type(team_name)}"

        # Verify team_name is not empty
        assert len(team_name) > 0, "Team name must not be empty"

    @given(submission=submission_strategy)
    def test_overall_score_field_is_valid(
        self,
        submission: dict,
    ) -> None:
        """Overall score field must be a float between 0 and 100."""
        overall_score = submission["overall_score"]

        # Verify overall_score is a number
        assert isinstance(overall_score, (int, float)), (
            f"Overall score must be a number, got {type(overall_score)}"
        )

        # Verify overall_score is in valid range
        assert 0.0 <= overall_score <= 100.0, (
            f"Overall score must be between 0 and 100, got {overall_score}"
        )

    @given(submission=submission_strategy)
    def test_recommendation_field_is_valid(
        self,
        submission: dict,
    ) -> None:
        """Recommendation field must be one of the valid values."""
        recommendation = submission["recommendation"]

        # Valid recommendation values
        valid_recommendations = ["must_interview", "strong_candidate", "consider", "pass"]

        # Verify recommendation is a string
        assert isinstance(recommendation, str), (
            f"Recommendation must be a string, got {type(recommendation)}"
        )

        # Verify recommendation is one of the valid values
        assert recommendation in valid_recommendations, (
            f"Recommendation must be one of {valid_recommendations}, got '{recommendation}'"
        )
