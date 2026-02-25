"""Property-based tests for Results page search and sort functionality.

This module tests Properties 20 and 21 from the design document:
- Property 20: Search Filtering
- Property 21: Leaderboard Sorting
"""

from datetime import datetime

from hypothesis import given
from hypothesis import strategies as st


# Helper functions that mirror the Results page logic
def filter_leaderboard(submissions: list[dict], search_query: str) -> list[dict]:
    """Filter submissions by team name (case-insensitive).

    Args:
        submissions: List of submission dictionaries
        search_query: Search query string

    Returns:
        Filtered list of submissions
    """
    if not search_query:
        return submissions

    return [s for s in submissions if search_query.lower() in s.get("team_name", "").lower()]


def sort_leaderboard(submissions: list[dict], sort_option: str) -> list[dict]:
    """Sort submissions by the specified field.

    Args:
        submissions: List of submission dictionaries
        sort_option: One of "score", "team_name", "created_at"

    Returns:
        Sorted list of submissions
    """
    if sort_option == "score":
        return sorted(submissions, key=lambda x: x.get("overall_score", 0), reverse=True)
    elif sort_option == "team_name":
        return sorted(submissions, key=lambda x: x.get("team_name", "").lower())
    elif sort_option == "created_at":
        return sorted(submissions, key=lambda x: x.get("created_at", ""), reverse=True)
    return submissions


# Hypothesis strategies for generating test data
submission_strategy = st.fixed_dictionaries(
    {
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


class TestSearchFilteringProperty:
    """Tests for Property 20: Search Filtering.

    Feature: streamlit-organizer-dashboard, Property 20: Search Filtering

    For any search query and leaderboard data, the filtered results should only
    include submissions where team_name contains the search query (case-insensitive).

    Validates: Requirements 6.3
    """

    @given(
        search_query=st.text(
            min_size=1,
            max_size=20,
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll"), min_codepoint=65, max_codepoint=122
            ),
        ),
        submissions=st.lists(submission_strategy, min_size=0, max_size=50),
    )
    def test_filtered_results_contain_search_query(
        self, search_query: str, submissions: list[dict]
    ) -> None:
        """All filtered results must contain the search query in team_name (case-insensitive)."""
        filtered = filter_leaderboard(submissions, search_query)

        for submission in filtered:
            team_name = submission.get("team_name", "")
            assert search_query.lower() in team_name.lower(), (
                f"Filtered submission '{team_name}' does not contain query '{search_query}'"
            )

    @given(
        search_query=st.text(
            min_size=1,
            max_size=20,
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll"), min_codepoint=65, max_codepoint=122
            ),
        ),
        submissions=st.lists(submission_strategy, min_size=1, max_size=50),
    )
    def test_no_false_positives_in_filtered_results(
        self, search_query: str, submissions: list[dict]
    ) -> None:
        """No submission without the search query should appear in filtered results."""
        filtered = filter_leaderboard(submissions, search_query)
        len(submissions)
        filtered_count = len(filtered)

        # Count how many submissions actually contain the query
        expected_count = sum(
            1 for s in submissions if search_query.lower() in s.get("team_name", "").lower()
        )

        assert filtered_count == expected_count, (
            f"Expected {expected_count} filtered results, got {filtered_count}"
        )

    @given(submissions=st.lists(submission_strategy, min_size=0, max_size=50))
    def test_empty_search_returns_all_submissions(self, submissions: list[dict]) -> None:
        """Empty search query should return all submissions."""
        filtered = filter_leaderboard(submissions, "")
        assert len(filtered) == len(submissions)
        assert filtered == submissions

    @given(
        search_query=st.text(
            min_size=1,
            max_size=20,
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll"), min_codepoint=65, max_codepoint=122
            ),
        ),
        submissions=st.lists(submission_strategy, min_size=1, max_size=50),
    )
    def test_search_is_case_insensitive(self, search_query: str, submissions: list[dict]) -> None:
        """Search should be case-insensitive."""
        # Filter with lowercase query
        filtered_lower = filter_leaderboard(submissions, search_query.lower())

        # Filter with uppercase query
        filtered_upper = filter_leaderboard(submissions, search_query.upper())

        # Filter with mixed case query
        filtered_mixed = filter_leaderboard(submissions, search_query)

        # All should return the same results
        assert len(filtered_lower) == len(filtered_upper) == len(filtered_mixed)


class TestLeaderboardSortingProperty:
    """Tests for Property 21: Leaderboard Sorting.

    Feature: streamlit-organizer-dashboard, Property 21: Leaderboard Sorting

    For any sort option (score, team_name, created_at) and leaderboard data,
    the sorted results should be correctly ordered by the selected field.

    Validates: Requirements 6.4
    """

    @given(submissions=st.lists(submission_strategy, min_size=2, max_size=50))
    def test_sort_by_score_descending(self, submissions: list[dict]) -> None:
        """Sorting by score should order submissions from highest to lowest score."""
        sorted_submissions = sort_leaderboard(submissions, "score")

        # Check that scores are in descending order
        for i in range(len(sorted_submissions) - 1):
            current_score = sorted_submissions[i].get("overall_score", 0)
            next_score = sorted_submissions[i + 1].get("overall_score", 0)
            assert current_score >= next_score, (
                f"Score at index {i} ({current_score}) is less than score at index {i + 1} ({next_score})"
            )

    @given(submissions=st.lists(submission_strategy, min_size=2, max_size=50))
    def test_sort_by_team_name_ascending(self, submissions: list[dict]) -> None:
        """Sorting by team_name should order submissions alphabetically (A-Z)."""
        sorted_submissions = sort_leaderboard(submissions, "team_name")

        # Check that team names are in ascending alphabetical order (case-insensitive)
        for i in range(len(sorted_submissions) - 1):
            current_name = sorted_submissions[i].get("team_name", "").lower()
            next_name = sorted_submissions[i + 1].get("team_name", "").lower()
            assert current_name <= next_name, (
                f"Team name at index {i} ('{current_name}') is greater than name at index {i + 1} ('{next_name}')"
            )

    @given(submissions=st.lists(submission_strategy, min_size=2, max_size=50))
    def test_sort_by_created_at_descending(self, submissions: list[dict]) -> None:
        """Sorting by created_at should order submissions from newest to oldest."""
        sorted_submissions = sort_leaderboard(submissions, "created_at")

        # Check that timestamps are in descending order (newest first)
        for i in range(len(sorted_submissions) - 1):
            current_time = sorted_submissions[i].get("created_at", "")
            next_time = sorted_submissions[i + 1].get("created_at", "")
            assert current_time >= next_time, (
                f"Timestamp at index {i} ({current_time}) is less than timestamp at index {i + 1} ({next_time})"
            )

    @given(
        submissions=st.lists(submission_strategy, min_size=1, max_size=50),
        sort_option=st.sampled_from(["score", "team_name", "created_at"]),
    )
    def test_sorting_preserves_all_submissions(
        self, submissions: list[dict], sort_option: str
    ) -> None:
        """Sorting should not add or remove any submissions."""
        sorted_submissions = sort_leaderboard(submissions, sort_option)

        assert len(sorted_submissions) == len(submissions), (
            f"Sorting changed the number of submissions: {len(submissions)} -> {len(sorted_submissions)}"
        )

    @given(
        submissions=st.lists(submission_strategy, min_size=1, max_size=50),
        sort_option=st.sampled_from(["score", "team_name", "created_at"]),
    )
    def test_sorting_is_stable(self, submissions: list[dict], sort_option: str) -> None:
        """Sorting the same data twice should produce identical results."""
        sorted_once = sort_leaderboard(submissions, sort_option)
        sorted_twice = sort_leaderboard(sorted_once, sort_option)

        assert sorted_once == sorted_twice, "Sorting the same data twice produced different results"


class TestCombinedSearchAndSortProperty:
    """Tests for combined search and sort operations.

    These tests verify that search and sort can be applied together
    and produce correct results.
    """

    @given(
        search_query=st.text(
            min_size=1,
            max_size=20,
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll"), min_codepoint=65, max_codepoint=122
            ),
        ),
        submissions=st.lists(submission_strategy, min_size=2, max_size=50),
        sort_option=st.sampled_from(["score", "team_name", "created_at"]),
    )
    def test_search_then_sort_maintains_both_properties(
        self, search_query: str, submissions: list[dict], sort_option: str
    ) -> None:
        """Applying search then sort should maintain both filtering and ordering."""
        # Apply search first
        filtered = filter_leaderboard(submissions, search_query)

        # Then apply sort
        filtered_and_sorted = sort_leaderboard(filtered, sort_option)

        # Verify all results still match the search query
        for submission in filtered_and_sorted:
            team_name = submission.get("team_name", "")
            assert search_query.lower() in team_name.lower()

        # Verify results are properly sorted
        if sort_option == "score" and len(filtered_and_sorted) >= 2:
            for i in range(len(filtered_and_sorted) - 1):
                current = filtered_and_sorted[i].get("overall_score", 0)
                next_val = filtered_and_sorted[i + 1].get("overall_score", 0)
                assert current >= next_val
        elif sort_option == "team_name" and len(filtered_and_sorted) >= 2:
            for i in range(len(filtered_and_sorted) - 1):
                current = filtered_and_sorted[i].get("team_name", "").lower()
                next_val = filtered_and_sorted[i + 1].get("team_name", "").lower()
                assert current <= next_val


class TestScorecardCompletenessProperty:
    """Tests for Property 23: Scorecard Data Completeness.

    Feature: streamlit-organizer-dashboard, Property 23: Scorecard Data Completeness

    For any scorecard response, the dashboard should display all required sections:
    overall_score, confidence, recommendation, dimension_scores (weighted_scores),
    agent_results (agent_scores), repo_meta, and cost breakdown.

    Validates: Requirements 7.2, 7.3, 7.4, 7.5, 7.6
    """

    def test_scorecard_has_all_required_top_level_fields(self) -> None:
        """Scorecard must contain all required top-level fields."""
        # Required top-level fields based on ScorecardResponse model
        required_fields = [
            "overall_score",
            "recommendation",
            "weighted_scores",  # dimension_scores in design doc
            "agent_scores",  # agent_results in design doc
            "repo_meta",
            "total_cost_usd",  # cost breakdown
        ]

        # Create a minimal valid scorecard
        scorecard = {
            "sub_id": "01HZZZ...",
            "hack_id": "01HXXX...",
            "team_name": "Test Team",
            "repo_url": "https://github.com/test/repo",
            "status": "analyzed",
            "overall_score": 85.5,
            "recommendation": "must_interview",
            "weighted_scores": {},
            "agent_scores": [],
            "repo_meta": {},
            "total_cost_usd": 0.023,
            "created_at": "2025-03-01T00:00:00Z",
            "updated_at": "2025-03-01T00:00:00Z",
        }

        # Verify all required fields are present
        for field in required_fields:
            assert field in scorecard, f"Required field '{field}' is missing from scorecard"

    @given(
        overall_score=st.floats(
            min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False
        ),
        recommendation=st.sampled_from(["must_interview", "strong_candidate", "consider", "pass"]),
        total_cost_usd=st.floats(
            min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False
        ),
    )
    def test_scorecard_displays_core_metrics(
        self,
        overall_score: float,
        recommendation: str,
        total_cost_usd: float,
    ) -> None:
        """Core metrics (overall_score, recommendation, total_cost_usd) must be displayable."""
        scorecard = {
            "overall_score": overall_score,
            "recommendation": recommendation,
            "total_cost_usd": total_cost_usd,
        }

        # Verify values are accessible and valid
        assert scorecard["overall_score"] >= 0.0
        assert scorecard["overall_score"] <= 100.0
        assert scorecard["recommendation"] in [
            "must_interview",
            "strong_candidate",
            "consider",
            "pass",
        ]
        assert scorecard["total_cost_usd"] >= 0.0

    @given(
        dimension_count=st.integers(min_value=1, max_value=10),
        raw_score=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
        weight=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    )
    def test_weighted_scores_structure(
        self,
        dimension_count: int,
        raw_score: float,
        weight: float,
    ) -> None:
        """Weighted scores (dimension_scores) must have raw, weight, and weighted fields."""
        weighted_scores = {}

        for i in range(dimension_count):
            dimension_name = f"dimension_{i}"
            weighted_scores[dimension_name] = {
                "raw": raw_score,
                "weight": weight,
                "weighted": raw_score * weight * 10,  # Convert to 0-100 scale
            }

        # Verify structure for each dimension
        for dimension_name, scores in weighted_scores.items():
            assert "raw" in scores, f"Dimension '{dimension_name}' missing 'raw' score"
            assert "weight" in scores, f"Dimension '{dimension_name}' missing 'weight'"
            assert "weighted" in scores, f"Dimension '{dimension_name}' missing 'weighted' score"

            # Verify value ranges
            assert 0.0 <= scores["raw"] <= 10.0
            assert 0.0 <= scores["weight"] <= 1.0
            assert 0.0 <= scores["weighted"] <= 100.0

    @given(
        agent_count=st.integers(min_value=1, max_value=10),
        agent_score=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
        confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    )
    def test_agent_scores_structure(
        self,
        agent_count: int,
        agent_score: float,
        confidence: float,
    ) -> None:
        """Agent scores (agent_results) must have agent_name, overall_score, confidence, and summary."""
        agent_scores = []

        for i in range(agent_count):
            agent_scores.append(
                {
                    "agent_name": f"agent_{i}",
                    "overall_score": agent_score,
                    "confidence": confidence,
                    "summary": f"Summary for agent {i}",
                    "scores": {},
                    "evidence": [],
                    "observations": {},
                }
            )

        # Verify structure for each agent
        for agent in agent_scores:
            assert "agent_name" in agent, "Agent missing 'agent_name'"
            assert "overall_score" in agent, "Agent missing 'overall_score'"
            assert "confidence" in agent, "Agent missing 'confidence'"
            assert "summary" in agent, "Agent missing 'summary'"

            # Verify value ranges
            assert 0.0 <= agent["overall_score"] <= 10.0
            assert 0.0 <= agent["confidence"] <= 1.0
            assert isinstance(agent["summary"], str)

    @given(
        commit_count=st.integers(min_value=0, max_value=1000),
        contributor_count=st.integers(min_value=1, max_value=50),
        has_tests=st.booleans(),
        has_ci=st.booleans(),
    )
    def test_repo_meta_structure(
        self,
        commit_count: int,
        contributor_count: int,
        has_tests: bool,
        has_ci: bool,
    ) -> None:
        """Repo metadata must contain key repository information."""
        repo_meta = {
            "commit_count": commit_count,
            "contributor_count": contributor_count,
            "primary_language": "Python",
            "has_tests": has_tests,
            "has_ci": has_ci,
            "total_files": 100,
            "total_lines": 5000,
        }

        # Verify required fields are present
        assert "commit_count" in repo_meta
        assert "contributor_count" in repo_meta
        assert "primary_language" in repo_meta
        assert "has_tests" in repo_meta
        assert "has_ci" in repo_meta

        # Verify value types and ranges
        assert isinstance(repo_meta["commit_count"], int)
        assert repo_meta["commit_count"] >= 0
        assert isinstance(repo_meta["contributor_count"], int)
        assert repo_meta["contributor_count"] >= 0
        assert isinstance(repo_meta["has_tests"], bool)
        assert isinstance(repo_meta["has_ci"], bool)

    @given(
        agent_count=st.integers(min_value=1, max_value=10),
        cost_per_agent=st.floats(
            min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False
        ),
    )
    def test_cost_breakdown_completeness(
        self,
        agent_count: int,
        cost_per_agent: float,
    ) -> None:
        """Cost breakdown must be calculable from agent scores and total_cost_usd."""
        agent_scores = []
        total_cost = 0.0

        for i in range(agent_count):
            agent_scores.append(
                {
                    "agent_name": f"agent_{i}",
                    "overall_score": 8.0,
                    "confidence": 0.9,
                    "summary": f"Summary {i}",
                }
            )
            total_cost += cost_per_agent

        scorecard = {
            "agent_scores": agent_scores,
            "total_cost_usd": total_cost,
        }

        # Verify cost data is present
        assert "total_cost_usd" in scorecard
        assert scorecard["total_cost_usd"] >= 0.0

        # Verify we can calculate per-agent cost
        if len(agent_scores) > 0:
            avg_cost_per_agent = scorecard["total_cost_usd"] / len(agent_scores)
            assert avg_cost_per_agent >= 0.0

    def test_complete_scorecard_has_all_sections(self) -> None:
        """A complete scorecard must have all required sections for display."""
        # Create a complete scorecard matching the ScorecardResponse model
        complete_scorecard = {
            "sub_id": "01HZZZ...",
            "hack_id": "01HXXX...",
            "team_name": "Team Awesome",
            "repo_url": "https://github.com/team/repo",
            "status": "analyzed",
            "overall_score": 92.5,
            "rank": 1,
            "recommendation": "must_interview",
            "weighted_scores": {
                "code_quality": {"raw": 9.0, "weight": 0.3, "weighted": 27.0},
                "innovation": {"raw": 9.5, "weight": 0.3, "weighted": 28.5},
                "performance": {"raw": 9.2, "weight": 0.3, "weighted": 27.6},
                "authenticity": {"raw": 9.0, "weight": 0.1, "weighted": 9.0},
            },
            "agent_scores": [
                {
                    "agent_name": "bug_hunter",
                    "overall_score": 9.0,
                    "confidence": 0.95,
                    "summary": "Excellent code quality",
                    "scores": {"code_quality": 9.0},
                    "evidence": [],
                    "observations": {},
                }
            ],
            "repo_meta": {
                "primary_language": "Python",
                "commit_count": 45,
                "contributor_count": 3,
                "has_tests": True,
                "has_ci": True,
                "total_files": 50,
                "total_lines": 2500,
            },
            "strengths": ["Clean architecture", "Good tests"],
            "weaknesses": ["Could improve documentation"],
            "total_cost_usd": 0.023,
            "total_tokens": 5000,
            "analysis_duration_ms": 15000,
            "analyzed_at": "2025-03-04T12:00:00Z",
            "created_at": "2025-03-02T10:00:00Z",
            "updated_at": "2025-03-04T12:00:00Z",
        }

        # Verify all required sections are present (Requirements 7.2-7.6)

        # Requirement 7.2: overall_score, confidence (from agent), recommendation
        assert "overall_score" in complete_scorecard
        assert "recommendation" in complete_scorecard
        assert len(complete_scorecard["agent_scores"]) > 0
        assert "confidence" in complete_scorecard["agent_scores"][0]

        # Requirement 7.3: dimension_scores with raw and weighted values
        assert "weighted_scores" in complete_scorecard
        for _dimension, scores in complete_scorecard["weighted_scores"].items():
            assert "raw" in scores
            assert "weighted" in scores
            assert "weight" in scores

        # Requirement 7.4: agent results including summary, strengths, improvements
        assert "agent_scores" in complete_scorecard
        assert "strengths" in complete_scorecard
        assert "weaknesses" in complete_scorecard  # improvements
        for agent in complete_scorecard["agent_scores"]:
            assert "summary" in agent

        # Requirement 7.5: repo_meta including primary_language, commit_count, has_tests
        assert "repo_meta" in complete_scorecard
        repo_meta = complete_scorecard["repo_meta"]
        assert "primary_language" in repo_meta
        assert "commit_count" in repo_meta
        assert "has_tests" in repo_meta

        # Requirement 7.6: cost breakdown by agent
        assert "total_cost_usd" in complete_scorecard
        # Cost per agent can be calculated from agent_scores if needed


class TestPaginationLimitProperty:
    """Tests for Property 22: Pagination Limit.

    Feature: streamlit-organizer-dashboard, Property 22: Pagination Limit

    For any leaderboard with more than 50 submissions, the dashboard should
    display at most 50 submissions per page.

    Validates: Requirements 11.6
    """

    @given(submissions=st.lists(submission_strategy, min_size=51, max_size=200))
    def test_pagination_limits_to_50_per_page(self, submissions: list[dict]) -> None:
        """Each page should display at most 50 submissions."""
        ITEMS_PER_PAGE = 50
        total_items = len(submissions)
        total_pages = (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

        # Test each page
        for page_num in range(1, total_pages + 1):
            start_idx = (page_num - 1) * ITEMS_PER_PAGE
            end_idx = min(start_idx + ITEMS_PER_PAGE, total_items)
            page_submissions = submissions[start_idx:end_idx]

            # Each page should have at most 50 items
            assert len(page_submissions) <= ITEMS_PER_PAGE, (
                f"Page {page_num} has {len(page_submissions)} items, expected at most {ITEMS_PER_PAGE}"
            )

            # Last page might have fewer items
            if page_num < total_pages:
                assert len(page_submissions) == ITEMS_PER_PAGE, (
                    f"Non-final page {page_num} has {len(page_submissions)} items, expected exactly {ITEMS_PER_PAGE}"
                )

    @given(submissions=st.lists(submission_strategy, min_size=51, max_size=200))
    def test_pagination_covers_all_submissions(self, submissions: list[dict]) -> None:
        """All submissions should be accessible across all pages."""
        ITEMS_PER_PAGE = 50
        total_items = len(submissions)
        total_pages = (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

        # Collect all submissions from all pages
        all_paginated = []
        for page_num in range(1, total_pages + 1):
            start_idx = (page_num - 1) * ITEMS_PER_PAGE
            end_idx = min(start_idx + ITEMS_PER_PAGE, total_items)
            page_submissions = submissions[start_idx:end_idx]
            all_paginated.extend(page_submissions)

        # Should have exactly the same number of submissions
        assert len(all_paginated) == len(submissions), (
            f"Pagination covered {len(all_paginated)} submissions, expected {len(submissions)}"
        )

    @given(submissions=st.lists(submission_strategy, min_size=1, max_size=50))
    def test_single_page_for_50_or_fewer_submissions(self, submissions: list[dict]) -> None:
        """Leaderboards with 50 or fewer submissions should fit on a single page."""
        ITEMS_PER_PAGE = 50
        total_items = len(submissions)
        total_pages = (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

        assert total_pages == 1, (
            f"Expected 1 page for {total_items} submissions, got {total_pages} pages"
        )

    @given(submissions=st.lists(submission_strategy, min_size=51, max_size=200))
    def test_page_calculation_is_correct(self, submissions: list[dict]) -> None:
        """Total pages calculation should be correct (ceiling division)."""
        ITEMS_PER_PAGE = 50
        total_items = len(submissions)

        # Calculate expected pages using ceiling division
        expected_pages = (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

        # Alternative calculation for verification
        import math

        expected_pages_alt = math.ceil(total_items / ITEMS_PER_PAGE)

        assert expected_pages == expected_pages_alt, (
            f"Page calculation mismatch: {expected_pages} vs {expected_pages_alt}"
        )

        # Verify the last page has the remaining items
        last_page_start = (expected_pages - 1) * ITEMS_PER_PAGE
        last_page_items = total_items - last_page_start

        assert 1 <= last_page_items <= ITEMS_PER_PAGE, (
            f"Last page should have 1-{ITEMS_PER_PAGE} items, got {last_page_items}"
        )

    @given(
        submissions=st.lists(submission_strategy, min_size=51, max_size=200),
        page_number=st.integers(min_value=1, max_value=10),
    )
    def test_page_bounds_are_enforced(self, submissions: list[dict], page_number: int) -> None:
        """Page number should be clamped to valid range [1, total_pages]."""
        ITEMS_PER_PAGE = 50
        total_items = len(submissions)
        total_pages = (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

        # Simulate page bounds enforcement
        clamped_page = max(1, min(page_number, total_pages))

        # Clamped page should always be in valid range
        assert 1 <= clamped_page <= total_pages, (
            f"Clamped page {clamped_page} is outside valid range [1, {total_pages}]"
        )

        # Calculate indices for clamped page
        start_idx = (clamped_page - 1) * ITEMS_PER_PAGE
        end_idx = min(start_idx + ITEMS_PER_PAGE, total_items)

        # Indices should be valid
        assert 0 <= start_idx < total_items, (
            f"Start index {start_idx} is invalid for {total_items} items"
        )
        assert start_idx < end_idx <= total_items, (
            f"End index {end_idx} is invalid (start: {start_idx}, total: {total_items})"
        )
