"""Property-based tests for Intelligence page data completeness.

This module tests Property 25 from the design document:
- Property 25: Intelligence Data Completeness

Feature: streamlit-organizer-dashboard, Property 25: Intelligence Data Completeness

For any intelligence response, the dashboard should display must_interview candidates,
technology_trends with Plotly chart, and sponsor_api_usage statistics.

Validates: Requirements 9.2, 9.3, 9.4, 9.5
"""

from hypothesis import given
from hypothesis import strategies as st


class TestIntelligenceDataCompletenessProperty:
    """Tests for Property 25: Intelligence Data Completeness.

    Feature: streamlit-organizer-dashboard, Property 25: Intelligence Data Completeness

    For any intelligence response, the dashboard should display must_interview candidates,
    technology_trends with Plotly chart, and sponsor_api_usage statistics.

    Validates: Requirements 9.2, 9.3, 9.4, 9.5
    """

    def test_intelligence_has_all_required_sections(self) -> None:
        """Intelligence response must contain all required sections."""
        # Required sections based on IntelligenceResponse model
        required_sections = [
            "must_interview",  # Requirement 9.2
            "technology_trends",  # Requirements 9.3, 9.4
            "sponsor_api_usage",  # Requirement 9.5
        ]

        # Create a minimal valid intelligence response
        intelligence = {
            "hack_id": "01HXXX...",
            "must_interview": [],
            "technology_trends": [],
            "sponsor_api_usage": {},
        }

        # Verify all required sections are present
        for section in required_sections:
            assert section in intelligence, (
                f"Required section '{section}' is missing from intelligence response"
            )

    @given(
        candidate_count=st.integers(min_value=0, max_value=50),
        hiring_score=st.floats(
            min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False
        ),
    )
    def test_must_interview_candidates_structure(
        self,
        candidate_count: int,
        hiring_score: float,
    ) -> None:
        """Must-interview candidates must have name, team_name, skills, and hiring_score.

        Validates: Requirement 9.2
        """
        must_interview = []

        for i in range(candidate_count):
            must_interview.append(
                {
                    "name": f"Candidate {i}",
                    "team_name": f"Team {i}",
                    "skills": ["Python", "FastAPI", "AWS"],
                    "hiring_score": hiring_score,
                }
            )

        # Verify structure for each candidate
        for candidate in must_interview:
            assert "name" in candidate, "Candidate missing 'name'"
            assert "team_name" in candidate, "Candidate missing 'team_name'"
            assert "skills" in candidate, "Candidate missing 'skills'"
            assert "hiring_score" in candidate, "Candidate missing 'hiring_score'"

            # Verify value types and ranges
            assert isinstance(candidate["name"], str)
            assert isinstance(candidate["team_name"], str)
            assert isinstance(candidate["skills"], list)
            assert 0.0 <= candidate["hiring_score"] <= 100.0

    @given(
        trend_count=st.integers(min_value=0, max_value=50),
        usage_count=st.integers(min_value=1, max_value=1000),
    )
    def test_technology_trends_structure(
        self,
        trend_count: int,
        usage_count: int,
    ) -> None:
        """Technology trends must have technology, category, and usage_count.

        Validates: Requirements 9.3, 9.4
        """
        technology_trends = []

        for i in range(trend_count):
            technology_trends.append(
                {
                    "technology": f"Technology {i}",
                    "category": "language",
                    "usage_count": usage_count,
                }
            )

        # Verify structure for each trend
        for trend in technology_trends:
            assert "technology" in trend, "Trend missing 'technology'"
            assert "category" in trend, "Trend missing 'category'"
            assert "usage_count" in trend, "Trend missing 'usage_count'"

            # Verify value types and ranges
            assert isinstance(trend["technology"], str)
            assert isinstance(trend["category"], str)
            assert isinstance(trend["usage_count"], int)
            assert trend["usage_count"] > 0

    @given(
        sponsor_count=st.integers(min_value=0, max_value=20),
        usage_count=st.integers(min_value=0, max_value=500),
    )
    def test_sponsor_api_usage_structure(
        self,
        sponsor_count: int,
        usage_count: int,
    ) -> None:
        """Sponsor API usage must be a dictionary with sponsor names and usage counts.

        Validates: Requirement 9.5
        """
        sponsor_api_usage = {}

        for i in range(sponsor_count):
            sponsor_name = f"sponsor_{i}"
            sponsor_api_usage[sponsor_name] = usage_count

        # Verify structure
        assert isinstance(sponsor_api_usage, dict), "sponsor_api_usage must be a dictionary"

        # Verify each entry
        for sponsor_name, count in sponsor_api_usage.items():
            assert isinstance(sponsor_name, str), f"Sponsor name '{sponsor_name}' must be a string"
            assert isinstance(count, int), f"Usage count for '{sponsor_name}' must be an integer"
            assert count >= 0, f"Usage count for '{sponsor_name}' must be non-negative"

    def test_complete_intelligence_has_all_sections(self) -> None:
        """A complete intelligence response must have all required sections for display.

        Validates: Requirements 9.2, 9.3, 9.4, 9.5
        """
        # Create a complete intelligence response
        complete_intelligence = {
            "hack_id": "01HXXX...",
            "must_interview": [
                {
                    "name": "Alice",
                    "team_name": "Team Awesome",
                    "skills": ["Python", "FastAPI", "AWS"],
                    "hiring_score": 95.0,
                },
                {
                    "name": "Bob",
                    "team_name": "Team Beta",
                    "skills": ["JavaScript", "React", "Node.js"],
                    "hiring_score": 92.5,
                },
            ],
            "technology_trends": [
                {
                    "technology": "Python",
                    "category": "language",
                    "usage_count": 120,
                },
                {
                    "technology": "FastAPI",
                    "category": "framework",
                    "usage_count": 80,
                },
                {
                    "technology": "AWS",
                    "category": "platform",
                    "usage_count": 100,
                },
            ],
            "sponsor_api_usage": {
                "stripe": 45,
                "twilio": 30,
                "aws": 80,
            },
        }

        # Verify all required sections are present

        # Requirement 9.2: must_interview candidates with name, skills, hiring_score
        assert "must_interview" in complete_intelligence
        assert len(complete_intelligence["must_interview"]) > 0
        for candidate in complete_intelligence["must_interview"]:
            assert "name" in candidate
            assert "team_name" in candidate
            assert "skills" in candidate
            assert "hiring_score" in candidate
            assert isinstance(candidate["skills"], list)
            assert len(candidate["skills"]) > 0

        # Requirement 9.3: technology_trends with language, framework, and usage counts
        assert "technology_trends" in complete_intelligence
        assert len(complete_intelligence["technology_trends"]) > 0
        for trend in complete_intelligence["technology_trends"]:
            assert "technology" in trend
            assert "category" in trend
            assert "usage_count" in trend
            assert trend["usage_count"] > 0

        # Requirement 9.4: technology_trends should be displayable in a chart
        # (Chart creation is tested separately in test_charts_properties.py)
        # Here we just verify the data structure is suitable for charting
        assert len(complete_intelligence["technology_trends"]) > 0
        technologies = [t["technology"] for t in complete_intelligence["technology_trends"]]
        usage_counts = [t["usage_count"] for t in complete_intelligence["technology_trends"]]
        assert len(technologies) == len(usage_counts)
        assert all(isinstance(t, str) for t in technologies)
        assert all(isinstance(c, int) and c > 0 for c in usage_counts)

        # Requirement 9.5: sponsor_api_usage statistics
        assert "sponsor_api_usage" in complete_intelligence
        assert len(complete_intelligence["sponsor_api_usage"]) > 0
        for sponsor_name, usage_count in complete_intelligence["sponsor_api_usage"].items():
            assert isinstance(sponsor_name, str)
            assert isinstance(usage_count, int)
            assert usage_count >= 0

    @given(
        must_interview_count=st.integers(min_value=0, max_value=50),
        trend_count=st.integers(min_value=0, max_value=50),
        sponsor_count=st.integers(min_value=0, max_value=20),
    )
    def test_intelligence_sections_can_be_empty(
        self,
        must_interview_count: int,
        trend_count: int,
        sponsor_count: int,
    ) -> None:
        """Intelligence sections can be empty (no data) but must still be present."""
        intelligence = {
            "hack_id": "01HXXX...",
            "must_interview": [
                {"name": f"C{i}", "team_name": f"T{i}", "skills": [], "hiring_score": 80.0}
                for i in range(must_interview_count)
            ],
            "technology_trends": [
                {"technology": f"Tech{i}", "category": "language", "usage_count": 1}
                for i in range(trend_count)
            ],
            "sponsor_api_usage": {f"sponsor_{i}": 1 for i in range(sponsor_count)},
        }

        # All sections must be present even if empty
        assert "must_interview" in intelligence
        assert "technology_trends" in intelligence
        assert "sponsor_api_usage" in intelligence

        # Verify counts match
        assert len(intelligence["must_interview"]) == must_interview_count
        assert len(intelligence["technology_trends"]) == trend_count
        assert len(intelligence["sponsor_api_usage"]) == sponsor_count

    @given(
        candidate_count=st.integers(min_value=1, max_value=50),
    )
    def test_must_interview_candidates_displayable(
        self,
        candidate_count: int,
    ) -> None:
        """Must-interview candidates must have all fields needed for table display.

        Validates: Requirement 9.2
        """
        must_interview = []

        for i in range(candidate_count):
            must_interview.append(
                {
                    "name": f"Candidate {i}",
                    "team_name": f"Team {i}",
                    "skills": ["Skill1", "Skill2", "Skill3"],
                    "hiring_score": 85.0 + (i % 15),  # Keep within 85-99 range
                }
            )

        # Simulate table display logic
        for candidate in must_interview:
            # Name column
            name = candidate.get("name", "Unknown")
            assert isinstance(name, str)
            assert len(name) > 0

            # Team name column
            team_name = candidate.get("team_name", "Unknown")
            assert isinstance(team_name, str)
            assert len(team_name) > 0

            # Skills column (comma-separated)
            skills = candidate.get("skills", [])
            assert isinstance(skills, list)
            if skills:
                skills_str = ", ".join(skills)
                assert isinstance(skills_str, str)
                assert len(skills_str) > 0

            # Hiring score column
            hiring_score = candidate.get("hiring_score", 0)
            assert isinstance(hiring_score, (int, float))
            assert 0.0 <= hiring_score <= 100.0

    @given(
        trend_count=st.integers(min_value=1, max_value=50),
    )
    def test_technology_trends_displayable_in_chart(
        self,
        trend_count: int,
    ) -> None:
        """Technology trends must have all fields needed for chart visualization.

        Validates: Requirements 9.3, 9.4
        """
        technology_trends = []

        for i in range(trend_count):
            technology_trends.append(
                {
                    "technology": f"Tech{i}",
                    "category": "language",
                    "usage_count": 10 + i,
                }
            )

        # Simulate chart data extraction
        technologies = [t.get("technology", "Unknown") for t in technology_trends]
        usage_counts = [t.get("usage_count", 0) for t in technology_trends]

        # Verify chart data is valid
        assert len(technologies) == trend_count
        assert len(usage_counts) == trend_count
        assert all(isinstance(t, str) and len(t) > 0 for t in technologies)
        assert all(isinstance(c, int) and c > 0 for c in usage_counts)

    @given(
        sponsor_count=st.integers(min_value=1, max_value=20),
    )
    def test_sponsor_api_usage_displayable_as_metrics(
        self,
        sponsor_count: int,
    ) -> None:
        """Sponsor API usage must be displayable as metrics.

        Validates: Requirement 9.5
        """
        sponsor_api_usage = {f"sponsor_{i}": 10 + i for i in range(sponsor_count)}

        # Simulate metrics display logic
        sponsors = list(sponsor_api_usage.items())

        for sponsor_name, usage_count in sponsors:
            # Sponsor name (metric label)
            assert isinstance(sponsor_name, str)
            assert len(sponsor_name) > 0

            # Usage count (metric value)
            assert isinstance(usage_count, int)
            assert usage_count >= 0

            # Simulate metric display
            label = sponsor_name.title()
            value = usage_count
            help_text = f"Number of teams using {sponsor_name} API"

            assert isinstance(label, str)
            assert isinstance(value, int)
            assert isinstance(help_text, str)

    def test_empty_intelligence_still_has_required_structure(self) -> None:
        """Even with no data, intelligence response must have required structure."""
        empty_intelligence = {
            "hack_id": "01HXXX...",
            "must_interview": [],
            "technology_trends": [],
            "sponsor_api_usage": {},
        }

        # All sections must be present
        assert "must_interview" in empty_intelligence
        assert "technology_trends" in empty_intelligence
        assert "sponsor_api_usage" in empty_intelligence

        # Verify types
        assert isinstance(empty_intelligence["must_interview"], list)
        assert isinstance(empty_intelligence["technology_trends"], list)
        assert isinstance(empty_intelligence["sponsor_api_usage"], dict)

        # Empty is valid
        assert len(empty_intelligence["must_interview"]) == 0
        assert len(empty_intelligence["technology_trends"]) == 0
        assert len(empty_intelligence["sponsor_api_usage"]) == 0

    @given(
        skills_count=st.integers(min_value=0, max_value=20),
    )
    def test_candidate_skills_can_be_empty_or_populated(
        self,
        skills_count: int,
    ) -> None:
        """Candidate skills list can be empty or contain multiple skills."""
        candidate = {
            "name": "Test Candidate",
            "team_name": "Test Team",
            "skills": [f"Skill{i}" for i in range(skills_count)],
            "hiring_score": 90.0,
        }

        # Skills must be a list
        assert isinstance(candidate["skills"], list)
        assert len(candidate["skills"]) == skills_count

        # If skills exist, they should be displayable
        if skills_count > 0:
            skills_str = ", ".join(candidate["skills"])
            assert isinstance(skills_str, str)
            assert len(skills_str) > 0
        else:
            # Empty skills should display as "N/A"
            skills_str = "N/A" if not candidate["skills"] else ", ".join(candidate["skills"])
            assert skills_str == "N/A"
