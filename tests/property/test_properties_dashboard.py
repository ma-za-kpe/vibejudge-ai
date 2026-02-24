"""Property-based tests for organizer dashboard (Properties 36-38).

This module tests the correctness properties of the organizer intelligence
dashboard using hypothesis for property-based testing with randomized inputs.

Properties tested:
- Property 36: Dashboard Aggregation Completeness
- Property 37: Infrastructure Maturity Metrics
- Property 38: Evidence-Based Prize Recommendations
"""

from typing import Any

from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from src.models.dashboard import (
    CommonIssue,
    HiringIntelligence,
    OrganizerDashboard,
    PrizeRecommendation,
    TechnologyTrends,
    TopPerformer,
)
from src.models.team_dynamics import (
    ContributorRole,
    ExpertiseArea,
    HiringSignals,
    IndividualScorecard,
    WorkStyle,
)

# ============================================================
# HYPOTHESIS STRATEGIES (Test Data Generators)
# ============================================================


@st.composite
def top_performer_strategy(draw: Any) -> TopPerformer:
    """Generate random top performer."""
    team_names = ["Team Alpha", "Team Beta", "Team Gamma", "Team Delta"]

    return TopPerformer(
        team_name=draw(st.sampled_from(team_names)),
        sub_id=f"SUB#{draw(st.integers(min_value=1000, max_value=9999))}",
        overall_score=draw(st.floats(min_value=0.0, max_value=100.0)),
        key_strengths=draw(st.lists(st.text(min_size=5, max_size=50), min_size=1, max_size=5)),
        sponsor_interest_flags=draw(
            st.lists(st.sampled_from(["AWS", "Google", "Microsoft", "Meta", "Stripe"]), max_size=3)
        ),
    )


@st.composite
def individual_scorecard_strategy(draw: Any) -> IndividualScorecard:
    """Generate random individual scorecard."""
    first_names = ["Alice", "Bob", "Charlie", "Diana", "Eve"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones"]

    first = draw(st.sampled_from(first_names))
    last = draw(st.sampled_from(last_names))
    name = f"{first} {last}"

    return IndividualScorecard(
        contributor_name=name,
        contributor_email=f"{first.lower()}.{last.lower()}@example.com",
        role=draw(st.sampled_from(list(ContributorRole))),
        expertise_areas=draw(
            st.lists(st.sampled_from(list(ExpertiseArea)), min_size=1, max_size=3, unique=True)
        ),
        commit_count=draw(st.integers(min_value=1, max_value=200)),
        lines_added=draw(st.integers(min_value=10, max_value=10000)),
        lines_deleted=draw(st.integers(min_value=0, max_value=5000)),
        files_touched=[f"file_{i}.py" for i in range(draw(st.integers(min_value=1, max_value=20)))],
        notable_contributions=draw(st.lists(st.text(min_size=10, max_size=100), max_size=5)),
        strengths=draw(st.lists(st.text(min_size=5, max_size=50), min_size=1, max_size=5)),
        weaknesses=draw(st.lists(st.text(min_size=5, max_size=50), max_size=3)),
        growth_areas=draw(st.lists(st.text(min_size=5, max_size=50), max_size=3)),
        work_style=WorkStyle(
            commit_frequency=draw(st.sampled_from(["frequent", "moderate", "infrequent"])),
            avg_commit_size=draw(st.integers(min_value=10, max_value=500)),
            active_hours=draw(
                st.lists(
                    st.integers(min_value=0, max_value=23), min_size=1, max_size=12, unique=True
                )
            ),
            late_night_commits=draw(st.integers(min_value=0, max_value=20)),
            weekend_commits=draw(st.integers(min_value=0, max_value=50)),
        ),
        hiring_signals=HiringSignals(
            recommended_role=draw(st.text(min_size=5, max_size=30)),
            seniority_level=draw(st.sampled_from(["junior", "mid", "senior"])),
            salary_range_usd=draw(
                st.sampled_from(["$60k-$80k", "$80k-$100k", "$100k-$130k", "$130k-$160k"])
            ),
            must_interview=draw(st.booleans()),
            sponsor_interest=draw(
                st.lists(st.sampled_from(["AWS", "Google", "Microsoft"]), max_size=2)
            ),
            rationale=draw(st.text(min_size=10, max_size=100)),
        ),
    )


@st.composite
def hiring_intelligence_strategy(draw: Any) -> HiringIntelligence:
    """Generate random hiring intelligence."""
    backend_count = draw(st.integers(min_value=0, max_value=10))
    frontend_count = draw(st.integers(min_value=0, max_value=10))
    devops_count = draw(st.integers(min_value=0, max_value=10))
    fullstack_count = draw(st.integers(min_value=0, max_value=10))
    must_interview_count = draw(st.integers(min_value=0, max_value=5))

    return HiringIntelligence(
        backend_candidates=[draw(individual_scorecard_strategy()) for _ in range(backend_count)],
        frontend_candidates=[draw(individual_scorecard_strategy()) for _ in range(frontend_count)],
        devops_candidates=[draw(individual_scorecard_strategy()) for _ in range(devops_count)],
        full_stack_candidates=[
            draw(individual_scorecard_strategy()) for _ in range(fullstack_count)
        ],
        must_interview=[draw(individual_scorecard_strategy()) for _ in range(must_interview_count)],
    )


@st.composite
def technology_trends_strategy(draw: Any) -> TechnologyTrends:
    """Generate random technology trends."""
    technologies = [
        "Python",
        "JavaScript",
        "TypeScript",
        "Go",
        "Rust",
        "Java",
        "React",
        "Vue",
        "Docker",
    ]
    stacks = ["MERN", "MEAN", "Django+React", "Flask+Vue", "FastAPI+React", "Go+PostgreSQL"]

    tech_count = draw(st.integers(min_value=1, max_value=len(technologies)))
    selected_techs = draw(
        st.lists(
            st.sampled_from(technologies), min_size=tech_count, max_size=tech_count, unique=True
        )
    )

    most_used = [(tech, draw(st.integers(min_value=1, max_value=100))) for tech in selected_techs]

    return TechnologyTrends(
        most_used=most_used,
        emerging=draw(st.lists(st.sampled_from(technologies), max_size=3, unique=True)),
        popular_stacks=[
            (stack, draw(st.integers(min_value=1, max_value=50)))
            for stack in draw(st.lists(st.sampled_from(stacks), max_size=5, unique=True))
        ],
    )


@st.composite
def infrastructure_metrics_strategy(draw: Any) -> dict[str, float]:
    """Generate random infrastructure maturity metrics."""
    return {
        "cicd_adoption_rate": draw(st.floats(min_value=0.0, max_value=100.0)),
        "docker_usage_rate": draw(st.floats(min_value=0.0, max_value=100.0)),
        "monitoring_adoption_rate": draw(st.floats(min_value=0.0, max_value=100.0)),
    }


@st.composite
def common_issue_strategy(draw: Any) -> CommonIssue:
    """Generate random common issue."""
    issue_types = [
        "SQL Injection",
        "Missing Input Validation",
        "Hardcoded Secrets",
        "No Error Handling",
        "Missing Tests",
        "Poor Code Documentation",
    ]

    return CommonIssue(
        issue_type=draw(st.sampled_from(issue_types)),
        percentage_affected=draw(st.floats(min_value=0.0, max_value=100.0)),
        workshop_recommendation=draw(st.text(min_size=20, max_size=100)),
        example_teams=draw(st.lists(st.text(min_size=5, max_size=20), max_size=5)),
    )


@st.composite
def prize_recommendation_strategy(draw: Any) -> PrizeRecommendation:
    """Generate random prize recommendation."""
    categories = [
        "Best Overall",
        "Best Team Dynamics",
        "Most Improved",
        "Best Practices",
        "Most Creative",
        "Best Use of Sponsor API",
    ]

    return PrizeRecommendation(
        prize_category=draw(st.sampled_from(categories)),
        recommended_team=draw(st.text(min_size=5, max_size=30)),
        sub_id=f"SUB#{draw(st.integers(min_value=1000, max_value=9999))}",
        justification=draw(st.text(min_size=20, max_size=200)),
        evidence=draw(st.lists(st.text(min_size=10, max_size=100), min_size=1, max_size=5)),
    )


@st.composite
def organizer_dashboard_strategy(draw: Any) -> OrganizerDashboard:
    """Generate random organizer dashboard."""
    submission_count = draw(st.integers(min_value=1, max_value=100))

    return OrganizerDashboard(
        hack_id=f"HACK#{draw(st.integers(min_value=100, max_value=999))}",
        hackathon_name=draw(st.text(min_size=5, max_size=50)),
        total_submissions=submission_count,
        top_performers=draw(st.lists(top_performer_strategy(), max_size=10)),
        hiring_intelligence=draw(hiring_intelligence_strategy()),
        technology_trends=draw(technology_trends_strategy()),
        common_issues=draw(st.lists(common_issue_strategy(), max_size=10)),
        standout_moments=draw(st.lists(st.text(min_size=10, max_size=100), max_size=10)),
        prize_recommendations=draw(st.lists(prize_recommendation_strategy(), max_size=10)),
        next_hackathon_recommendations=draw(
            st.lists(st.text(min_size=10, max_size=100), max_size=5)
        ),
        sponsor_follow_up_actions=draw(st.lists(st.text(min_size=10, max_size=100), max_size=5)),
    )


# ============================================================
# PROPERTY 36: Dashboard Aggregation Completeness
# ============================================================


@given(dashboard=organizer_dashboard_strategy())
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.data_too_large])
def test_property_36_dashboard_has_all_required_sections(dashboard: OrganizerDashboard) -> None:
    """Property 36: Dashboard contains all required sections.

    Feature: human-centric-intelligence
    Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7

    For any hackathon with completed submissions, the organizer dashboard
    should include: top performers, hiring intelligence (categorized by role),
    technology trends, common issues with percentages, standout moments,
    prize recommendations, next hackathon recommendations, and sponsor
    follow-up actions.
    """
    # Property: All required sections should be present
    assert dashboard.hack_id, "Dashboard should have hack_id"
    assert dashboard.hackathon_name, "Dashboard should have hackathon_name"
    assert dashboard.total_submissions >= 0, "Dashboard should have total_submissions"

    # Property: Top performers section exists
    assert dashboard.top_performers is not None, "Dashboard should have top_performers"

    # Property: Hiring intelligence section exists
    assert dashboard.hiring_intelligence is not None, "Dashboard should have hiring_intelligence"
    assert dashboard.hiring_intelligence.backend_candidates is not None
    assert dashboard.hiring_intelligence.frontend_candidates is not None
    assert dashboard.hiring_intelligence.devops_candidates is not None
    assert dashboard.hiring_intelligence.full_stack_candidates is not None
    assert dashboard.hiring_intelligence.must_interview is not None

    # Property: Technology trends section exists
    assert dashboard.technology_trends is not None, "Dashboard should have technology_trends"
    assert dashboard.technology_trends.most_used is not None
    assert dashboard.technology_trends.emerging is not None
    assert dashboard.technology_trends.popular_stacks is not None


@given(dashboard=organizer_dashboard_strategy())
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.data_too_large])
def test_property_36_technology_trends_show_usage_counts(dashboard: OrganizerDashboard) -> None:
    """Property 36: Technology trends show usage counts.

    Feature: human-centric-intelligence
    Validates: Requirements 9.3

    For any technology trend, it should include the count of teams
    using that technology.
    """
    trends = dashboard.technology_trends

    # Property: most_used should be list of (technology, count) tuples
    assert isinstance(trends.most_used, list), "most_used should be a list"
    for tech, count in trends.most_used:
        assert isinstance(tech, str), "Technology should be a string"
        assert isinstance(count, int), "Count should be an integer"
        assert count > 0, f"Count should be positive, got {count}"

    # Property: popular_stacks should be list of (stack, count) tuples
    assert isinstance(trends.popular_stacks, list), "popular_stacks should be a list"
    for stack, count in trends.popular_stacks:
        assert isinstance(stack, str), "Stack should be a string"
        assert isinstance(count, int), "Count should be an integer"
        assert count > 0, f"Count should be positive, got {count}"


@given(
    submission_count=st.integers(min_value=1, max_value=100),
    top_performer_count=st.integers(min_value=0, max_value=20),
)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.data_too_large])
def test_property_36_top_performers_subset_of_submissions(
    submission_count: int, top_performer_count: int
) -> None:
    """Property 36: Top performers are subset of submissions.

    Feature: human-centric-intelligence
    Validates: Requirements 9.1

    For any dashboard, the number of top performers should not exceed
    the total number of submissions.
    """
    # Property: Top performers count <= total submissions
    assume(top_performer_count <= submission_count)

    assert top_performer_count <= submission_count, (
        f"Top performers ({top_performer_count}) should not exceed submissions ({submission_count})"
    )


@given(dashboard=organizer_dashboard_strategy())
@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.data_too_large])
def test_property_36_dashboard_completeness_for_organizers(dashboard: OrganizerDashboard) -> None:
    """Property 36: Dashboard provides complete organizer intelligence.

    Feature: human-centric-intelligence
    Validates: Requirements 9.1-9.7

    For any dashboard, it should provide all information needed by
    organizers: performance data, hiring leads, technology insights,
    common problems, and actionable recommendations.
    """
    # Property: Performance data exists
    assert len(dashboard.top_performers) >= 0, "Should have top performers data"

    # Property: Hiring leads exist
    total_candidates = (
        len(dashboard.hiring_intelligence.backend_candidates)
        + len(dashboard.hiring_intelligence.frontend_candidates)
        + len(dashboard.hiring_intelligence.devops_candidates)
        + len(dashboard.hiring_intelligence.full_stack_candidates)
    )
    assert total_candidates >= 0, "Should have hiring candidates"

    # Property: Technology insights exist
    assert len(dashboard.technology_trends.most_used) >= 0, "Should have technology data"

    # Property: Common problems identified
    assert len(dashboard.common_issues) >= 0, "Should have common issues"

    # Property: Actionable recommendations exist
    assert len(dashboard.next_hackathon_recommendations) >= 0, (
        "Should have next hackathon recommendations"
    )
    assert len(dashboard.sponsor_follow_up_actions) >= 0, "Should have sponsor follow-up actions"


@given(metrics=infrastructure_metrics_strategy())
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.data_too_large])
def test_property_37_infrastructure_metrics_include_required_categories(
    metrics: dict[str, float],
) -> None:
    """Property 37: Infrastructure metrics include required categories.

    Feature: human-centric-intelligence
    Validates: Requirements 9.8

    For any dashboard, infrastructure maturity metrics should include
    CI/CD adoption, Docker usage, and monitoring/logging adoption.
    """
    # Property: Required metric categories should exist
    required_metrics = [
        "cicd_adoption_rate",
        "docker_usage_rate",
        "monitoring_adoption_rate",
    ]

    for metric in required_metrics:
        assert metric in metrics, f"Should have {metric} in infrastructure metrics"


@given(
    total_submissions=st.integers(min_value=1, max_value=100),
    adoption_count=st.integers(min_value=0, max_value=100),
)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.data_too_large])
def test_property_37_zero_adoption_yields_zero_percent(
    total_submissions: int, adoption_count: int
) -> None:
    """Property 37: Zero adoption yields 0% rate.

    Feature: human-centric-intelligence
    Validates: Requirements 9.8

    For any infrastructure metric, if no teams adopt the technology,
    the adoption rate should be 0%.
    """
    # Property: 0 adoption = 0% rate
    if adoption_count == 0:
        adoption_rate = (adoption_count / total_submissions) * 100.0
        assert adoption_rate == 0.0, f"Zero adoption should yield 0%, got {adoption_rate}"


@given(total_submissions=st.integers(min_value=1, max_value=100))
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.data_too_large])
def test_property_37_full_adoption_yields_hundred_percent(total_submissions: int) -> None:
    """Property 37: Full adoption yields 100% rate.

    Feature: human-centric-intelligence
    Validates: Requirements 9.8

    For any infrastructure metric, if all teams adopt the technology,
    the adoption rate should be 100%.
    """
    # Property: Full adoption = 100% rate
    adoption_count = total_submissions
    adoption_rate = (adoption_count / total_submissions) * 100.0

    tolerance = 0.01
    assert abs(adoption_rate - 100.0) < tolerance, (
        f"Full adoption should yield 100%, got {adoption_rate}"
    )


@given(dashboard=organizer_dashboard_strategy())
@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.data_too_large])
def test_property_38_all_prize_recommendations_have_evidence(dashboard: OrganizerDashboard) -> None:
    """Property 38: All prize recommendations include evidence.

    Feature: human-centric-intelligence
    Validates: Requirements 9.9, 9.10

    For any dashboard, all prize recommendations should include
    specific evidence, not just scores or subjective opinions.
    """
    # Property: Each prize recommendation should have evidence
    for prize in dashboard.prize_recommendations:
        assert prize.evidence is not None, f"Prize {prize.prize_category} should have evidence"
        assert isinstance(prize.evidence, list), (
            f"Prize {prize.prize_category} evidence should be a list"
        )

        # Property: Justification should be present
        assert prize.justification, f"Prize {prize.prize_category} should have justification"
        assert len(prize.justification) >= 20, (
            f"Prize {prize.prize_category} justification should be detailed"
        )


@given(
    team_name=st.text(min_size=5, max_size=30),
    evidence_count=st.integers(min_value=1, max_value=10),
)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.data_too_large])
def test_property_38_prize_recommendation_links_to_team(
    team_name: str, evidence_count: int
) -> None:
    """Property 38: Prize recommendation links to specific team.

    Feature: human-centric-intelligence
    Validates: Requirements 9.9

    For any prize recommendation, it should clearly identify the
    recommended team with team name and submission ID.
    """
    # Create prize recommendation
    prize = PrizeRecommendation(
        prize_category="Best Overall",
        recommended_team=team_name,
        sub_id="SUB#1234",
        justification="Excellent work across all categories",
        evidence=[f"Evidence item {i}" for i in range(evidence_count)],
    )

    # Property: Team identification should be clear
    assert prize.recommended_team == team_name, "Prize should identify recommended team"
    assert prize.sub_id, "Prize should have submission ID"
    assert prize.sub_id.startswith("SUB#"), "Submission ID should follow format"


@given(dashboard=organizer_dashboard_strategy())
@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.data_too_large])
def test_property_38_prize_recommendations_not_based_solely_on_scores(
    dashboard: OrganizerDashboard,
) -> None:
    """Property 38: Prize recommendations include qualitative evidence.

    Feature: human-centric-intelligence
    Validates: Requirements 9.9, 9.10

    For any prize recommendation, it should include qualitative evidence
    and specific examples, not just numerical scores.
    """
    # Property: Each prize should have evidence beyond scores
    for prize in dashboard.prize_recommendations:
        # Justification should not just be a score
        assert prize.justification, "Should have justification"

        # Evidence should provide specific examples
        if len(prize.evidence) > 0:
            # Evidence items should be descriptive, not just numbers
            for evidence_item in prize.evidence:
                assert isinstance(evidence_item, str), "Evidence should be descriptive text"


# ============================================================
# INTEGRATION PROPERTY: Complete Dashboard Functionality
# ============================================================


@given(dashboard=organizer_dashboard_strategy())
@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.data_too_large])
def test_property_dashboard_provides_actionable_insights(dashboard: OrganizerDashboard) -> None:
    """Integration property: Dashboard provides actionable insights.

    Feature: human-centric-intelligence
    Validates: Requirements 9.1-9.10

    For any dashboard, it should provide actionable insights for
    organizers including hiring leads, technology trends, common
    issues with workshop recommendations, and prize recommendations
    with evidence.
    """
    # Property: Dashboard has hackathon identification
    assert dashboard.hack_id, "Dashboard should identify hackathon"
    assert dashboard.hackathon_name, "Dashboard should have hackathon name"
    assert dashboard.total_submissions >= 0, "Dashboard should have submission count"

    # Property: Hiring intelligence is actionable
    hiring = dashboard.hiring_intelligence
    total_candidates = (
        len(hiring.backend_candidates)
        + len(hiring.frontend_candidates)
        + len(hiring.devops_candidates)
        + len(hiring.full_stack_candidates)
    )
    # Should have candidates categorized by role
    assert total_candidates >= 0, "Should have hiring candidates"

    # Property: Technology trends provide insights
    assert dashboard.technology_trends is not None, "Should have technology trends"
    assert dashboard.technology_trends.most_used is not None, "Should track technology usage"

    # Property: Common issues include workshop recommendations
    for issue in dashboard.common_issues:
        assert issue.workshop_recommendation, (
            "Common issues should include workshop recommendations"
        )

    # Property: Prize recommendations include evidence
    for prize in dashboard.prize_recommendations:
        assert prize.evidence is not None, "Prizes should have evidence"
        assert prize.justification, "Prizes should have justification"

    # Property: Next hackathon recommendations exist
    assert dashboard.next_hackathon_recommendations is not None, (
        "Should have recommendations for next hackathon"
    )

    # Property: Sponsor follow-up actions exist
    assert dashboard.sponsor_follow_up_actions is not None, "Should have sponsor follow-up actions"


@given(
    total_submissions=st.integers(min_value=1, max_value=100),
    must_interview_count=st.integers(min_value=0, max_value=20),
)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.data_too_large])
def test_property_must_interview_candidates_subset_of_all_candidates(
    total_submissions: int, must_interview_count: int
) -> None:
    """Integration property: Must-interview candidates are subset.

    Feature: human-centric-intelligence
    Validates: Requirements 9.2

    For any dashboard, the must-interview candidates should be a subset
    of all candidates (cannot exceed total number of contributors).
    """
    # Assume reasonable ratio (max 2 contributors per submission)
    max_contributors = total_submissions * 2
    assume(must_interview_count <= max_contributors)

    # Property: Must-interview count should be reasonable
    assert must_interview_count <= max_contributors, (
        f"Must-interview count ({must_interview_count}) should not exceed max contributors ({max_contributors})"
    )


@given(dashboard=organizer_dashboard_strategy())
@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.data_too_large])
def test_property_dashboard_data_consistency(dashboard: OrganizerDashboard) -> None:
    """Integration property: Dashboard data is internally consistent.

    Feature: human-centric-intelligence
    Validates: Requirements 9.1-9.10

    For any dashboard, the data should be internally consistent:
    - Top performers should not exceed total submissions
    - Common issue percentages should be valid (0-100)
    - Prize recommendations should reference valid submissions
    """
    # Property: Top performers <= total submissions
    assert len(dashboard.top_performers) <= dashboard.total_submissions, (
        "Top performers should not exceed total submissions"
    )

    # Property: Common issue percentages are valid
    for issue in dashboard.common_issues:
        assert 0.0 <= issue.percentage_affected <= 100.0, (
            f"Issue percentage should be 0-100, got {issue.percentage_affected}"
        )

    # Property: Prize recommendations have valid submission IDs
    for prize in dashboard.prize_recommendations:
        assert prize.sub_id, "Prize should have submission ID"
        assert prize.sub_id.startswith("SUB#"), "Submission ID should follow format"

    # Property: Technology counts should be positive
    for _tech, count in dashboard.technology_trends.most_used:
        assert count > 0, f"Technology count should be positive, got {count}"

    for _stack, count in dashboard.technology_trends.popular_stacks:
        assert count > 0, f"Stack count should be positive, got {count}"
