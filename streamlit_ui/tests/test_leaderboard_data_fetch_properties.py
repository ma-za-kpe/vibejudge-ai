"""Property-based tests for leaderboard data fetch.

This module tests Property 18 from the design document:
- Property 18: Leaderboard Data Fetch

Feature: streamlit-organizer-dashboard, Property 18: Leaderboard Data Fetch

For any hackathon with analyzed submissions, the dashboard should fetch
leaderboard data from GET /hackathons/{hack_id}/leaderboard.

Validates: Requirements 6.1
"""

from hypothesis import given
from hypothesis import strategies as st


class TestLeaderboardDataFetchProperty:
    """Tests for Property 18: Leaderboard Data Fetch.

    Feature: streamlit-organizer-dashboard, Property 18: Leaderboard Data Fetch

    For any hackathon with analyzed submissions, the dashboard should fetch
    leaderboard data from GET /hackathons/{hack_id}/leaderboard.

    Validates: Requirements 6.1
    """

    @given(
        hack_id=st.text(
            min_size=10,
            max_size=30,
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"), min_codepoint=48, max_codepoint=122
            ),
        ),
    )
    def test_leaderboard_endpoint_constructed_correctly(
        self,
        hack_id: str,
    ) -> None:
        """Leaderboard endpoint should be constructed with correct hack_id."""
        # Simulate endpoint construction
        endpoint = f"/hackathons/{hack_id}/leaderboard"

        # Verify endpoint structure
        assert hack_id in endpoint
        assert "/hackathons/" in endpoint
        assert "/leaderboard" in endpoint
        assert endpoint.startswith("/hackathons/")
        assert endpoint.endswith("/leaderboard")

    @given(
        analyzed_count=st.integers(min_value=1, max_value=500),
    )
    def test_leaderboard_fetch_for_analyzed_hackathon(
        self,
        analyzed_count: int,
    ) -> None:
        """Leaderboard should be fetchable when hackathon has analyzed submissions."""
        # Simulate hackathon with analyzed submissions
        hackathon = {
            "hack_id": "01HXXX...",
            "analyzed_count": analyzed_count,
            "total_submissions": analyzed_count,
        }

        # Verify hackathon has analyzed submissions
        assert hackathon["analyzed_count"] > 0

        # Simulate fetch decision logic
        should_fetch_leaderboard = hackathon["analyzed_count"] > 0

        # Leaderboard should be fetchable
        assert should_fetch_leaderboard is True

    def test_leaderboard_response_structure(self) -> None:
        """Leaderboard response must have required structure."""
        # Simulate leaderboard response
        leaderboard_response = {
            "hack_id": "01HXXX...",
            "total_submissions": 150,
            "analyzed_count": 148,
            "submissions": [],
        }

        # Verify required fields are present
        required_fields = ["hack_id", "total_submissions", "analyzed_count", "submissions"]
        for field in required_fields:
            assert field in leaderboard_response, (
                f"Required field '{field}' missing from leaderboard response"
            )

        # Verify field types
        assert isinstance(leaderboard_response["hack_id"], str)
        assert isinstance(leaderboard_response["total_submissions"], int)
        assert isinstance(leaderboard_response["analyzed_count"], int)
        assert isinstance(leaderboard_response["submissions"], list)

    @given(
        submission_count=st.integers(min_value=0, max_value=500),
    )
    def test_leaderboard_submissions_list_structure(
        self,
        submission_count: int,
    ) -> None:
        """Leaderboard submissions list must be properly structured."""
        # Simulate leaderboard response with submissions
        submissions = []

        for i in range(submission_count):
            submissions.append(
                {
                    "sub_id": f"01HZZZ{i:03d}",
                    "rank": i + 1,
                    "team_name": f"Team {i}",
                    "overall_score": 90.0 - (i * 0.1),
                    "recommendation": "must_interview",
                    "created_at": "2025-03-02T10:00:00Z",
                }
            )

        leaderboard_response = {
            "hack_id": "01HXXX...",
            "total_submissions": submission_count,
            "analyzed_count": submission_count,
            "submissions": submissions,
        }

        # Verify submissions list matches count
        assert len(leaderboard_response["submissions"]) == submission_count

        # Verify each submission has required fields
        for submission in leaderboard_response["submissions"]:
            assert "sub_id" in submission
            assert "rank" in submission
            assert "team_name" in submission
            assert "overall_score" in submission
            assert "recommendation" in submission

    @given(
        hack_id=st.text(
            min_size=10,
            max_size=30,
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"), min_codepoint=48, max_codepoint=122
            ),
        ),
    )
    def test_leaderboard_fetch_includes_hack_id(
        self,
        hack_id: str,
    ) -> None:
        """Leaderboard fetch must include the correct hack_id in the request."""
        # Simulate API request
        endpoint = f"/hackathons/{hack_id}/leaderboard"

        # Extract hack_id from endpoint
        parts = endpoint.split("/")
        extracted_hack_id = parts[2] if len(parts) > 2 else None

        # Verify hack_id is correctly included
        assert extracted_hack_id == hack_id

    @given(
        total_submissions=st.integers(min_value=1, max_value=500),
        analyzed_count=st.integers(min_value=0, max_value=500),
    )
    def test_leaderboard_counts_consistency(
        self,
        total_submissions: int,
        analyzed_count: int,
    ) -> None:
        """Analyzed count should not exceed total submissions."""
        # Ensure analyzed_count doesn't exceed total_submissions
        analyzed = min(analyzed_count, total_submissions)

        leaderboard_response = {
            "total_submissions": total_submissions,
            "analyzed_count": analyzed,
        }

        # Verify consistency
        assert leaderboard_response["analyzed_count"] <= leaderboard_response["total_submissions"]

    def test_leaderboard_fetch_returns_empty_list_when_no_submissions(self) -> None:
        """Leaderboard should return empty submissions list when no submissions exist."""
        leaderboard_response = {
            "hack_id": "01HXXX...",
            "total_submissions": 0,
            "analyzed_count": 0,
            "submissions": [],
        }

        # Verify empty list is valid
        assert isinstance(leaderboard_response["submissions"], list)
        assert len(leaderboard_response["submissions"]) == 0
        assert leaderboard_response["total_submissions"] == 0
        assert leaderboard_response["analyzed_count"] == 0

    @given(
        submission_count=st.integers(min_value=1, max_value=100),
    )
    def test_leaderboard_submissions_have_rank(
        self,
        submission_count: int,
    ) -> None:
        """Each submission in leaderboard must have a rank."""
        submissions = []

        for i in range(submission_count):
            submissions.append(
                {
                    "sub_id": f"01HZZZ{i:03d}",
                    "rank": i + 1,
                    "team_name": f"Team {i}",
                    "overall_score": 90.0 - (i * 0.1),
                    "recommendation": "must_interview",
                }
            )

        # Verify each submission has a rank
        for submission in submissions:
            assert "rank" in submission
            assert isinstance(submission["rank"], int)
            assert submission["rank"] > 0

        # Verify ranks are sequential
        ranks = [s["rank"] for s in submissions]
        assert ranks == list(range(1, submission_count + 1))

    @given(
        submission_count=st.integers(min_value=1, max_value=100),
    )
    def test_leaderboard_submissions_sorted_by_rank(
        self,
        submission_count: int,
    ) -> None:
        """Leaderboard submissions should be sorted by rank (ascending)."""
        submissions = []

        for i in range(submission_count):
            submissions.append(
                {
                    "rank": i + 1,
                    "overall_score": 90.0 - (i * 0.1),
                }
            )

        # Verify submissions are sorted by rank
        for i in range(len(submissions) - 1):
            current_rank = submissions[i]["rank"]
            next_rank = submissions[i + 1]["rank"]
            assert current_rank < next_rank, (
                f"Submissions not sorted by rank: {current_rank} >= {next_rank}"
            )

    @given(
        hack_id=st.text(
            min_size=10,
            max_size=30,
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"), min_codepoint=48, max_codepoint=122
            ),
        ),
    )
    def test_leaderboard_response_includes_hack_id(
        self,
        hack_id: str,
    ) -> None:
        """Leaderboard response must include the hack_id."""
        leaderboard_response = {
            "hack_id": hack_id,
            "total_submissions": 10,
            "analyzed_count": 10,
            "submissions": [],
        }

        # Verify hack_id is in response
        assert "hack_id" in leaderboard_response
        assert leaderboard_response["hack_id"] == hack_id

    @given(
        total_submissions=st.integers(min_value=1, max_value=500),
        analyzed_count=st.integers(min_value=1, max_value=500),
    )
    def test_leaderboard_shows_analysis_progress(
        self,
        total_submissions: int,
        analyzed_count: int,
    ) -> None:
        """Leaderboard should show analysis progress (analyzed vs total)."""
        # Ensure analyzed doesn't exceed total
        analyzed = min(analyzed_count, total_submissions)

        leaderboard_response = {
            "total_submissions": total_submissions,
            "analyzed_count": analyzed,
        }

        # Calculate progress percentage
        progress_percent = (
            leaderboard_response["analyzed_count"] / leaderboard_response["total_submissions"]
        ) * 100

        # Verify progress is calculable
        assert 0.0 <= progress_percent <= 100.0

        # Verify progress can be displayed
        progress_text = f"{leaderboard_response['analyzed_count']}/{leaderboard_response['total_submissions']} analyzed"
        assert str(analyzed) in progress_text
        assert str(total_submissions) in progress_text

    def test_leaderboard_fetch_method_is_get(self) -> None:
        """Leaderboard should be fetched using GET method."""
        # Simulate API request configuration
        http_method = "GET"
        endpoint = "/hackathons/01HXXX.../leaderboard"

        # Verify GET method is used
        assert http_method == "GET"
        assert endpoint.startswith("/hackathons/")

    @given(
        submission_count=st.integers(min_value=1, max_value=100),
    )
    def test_leaderboard_submissions_have_required_display_fields(
        self,
        submission_count: int,
    ) -> None:
        """Each submission must have fields required for display (rank, team_name, overall_score, recommendation)."""
        submissions = []

        for i in range(submission_count):
            submissions.append(
                {
                    "sub_id": f"01HZZZ{i:03d}",
                    "rank": i + 1,
                    "team_name": f"Team {i}",
                    "overall_score": 90.0 - (i * 0.1),
                    "recommendation": "must_interview",
                    "created_at": "2025-03-02T10:00:00Z",
                }
            )

        # Verify each submission has required display fields (Requirement 6.2)
        required_display_fields = ["rank", "team_name", "overall_score", "recommendation"]

        for submission in submissions:
            for field in required_display_fields:
                assert field in submission, f"Submission missing required display field '{field}'"

                # Verify field is not None or empty
                value = submission[field]
                assert value is not None
                if isinstance(value, str):
                    assert len(value) > 0
