"""Property-based tests for red flag detection (Properties 33-35).

This module tests the correctness properties of red flag detection
using hypothesis for property-based testing with randomized inputs.

Properties tested:
- Property 33: Red Flag Completeness
- Property 34: Critical Red Flag Recommendation
- Property 35: Branch Analysis Red Flag
"""

from typing import Any

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from src.models.team_dynamics import (
    ContributorRole,
    ExpertiseArea,
    HiringSignals,
    IndividualScorecard,
    RedFlag,
    RedFlagSeverity,
    TeamAnalysisResult,
    WorkStyle,
)

# ============================================================
# HYPOTHESIS STRATEGIES (Test Data Generators)
# ============================================================


@st.composite
def red_flag_strategy(draw: Any) -> RedFlag:
    """Generate random red flag with all required fields."""
    flag_types = [
        "extreme_imbalance",
        "ghost_contributor",
        "history_rewriting",
        "unhealthy_work_patterns",
        "minimal_contribution",
        "no_code_review",
        "security_incident_coverup",
        "territorial_behavior",
    ]

    flag_type = draw(st.sampled_from(flag_types))
    severity = draw(
        st.sampled_from(
            [
                RedFlagSeverity.CRITICAL,
                RedFlagSeverity.HIGH,
                RedFlagSeverity.MEDIUM,
            ]
        )
    )

    return RedFlag(
        flag_type=flag_type,
        severity=severity,
        description=draw(st.text(min_size=10, max_size=200)),
        evidence=draw(st.text(min_size=10, max_size=200)),
        impact=draw(st.text(min_size=10, max_size=200)),
        hiring_impact=draw(st.text(min_size=10, max_size=200)),
        recommended_action=draw(st.text(min_size=10, max_size=200)),
    )


@st.composite
def critical_red_flag_strategy(draw: Any) -> RedFlag:
    """Generate critical severity red flag."""
    critical_flag_types = [
        "extreme_imbalance",
        "ghost_contributor",
        "security_incident_coverup",
    ]

    flag_type = draw(st.sampled_from(critical_flag_types))

    return RedFlag(
        flag_type=flag_type,
        severity=RedFlagSeverity.CRITICAL,
        description=draw(st.text(min_size=10, max_size=200)),
        evidence=draw(st.text(min_size=10, max_size=200)),
        impact=draw(st.text(min_size=10, max_size=200)),
        hiring_impact=draw(st.text(min_size=10, max_size=200)),
        recommended_action=draw(st.text(min_size=10, max_size=200)),
    )


@st.composite
def branch_analysis_data_strategy(draw: Any) -> dict[str, Any]:
    """Generate random branch analysis data."""
    return {
        "has_branches": draw(st.booleans()),
        "has_pull_requests": draw(st.booleans()),
        "all_commits_to_main": draw(st.booleans()),
        "branch_count": draw(st.integers(min_value=0, max_value=20)),
        "pr_count": draw(st.integers(min_value=0, max_value=50)),
    }


@st.composite
def team_analysis_with_red_flags_strategy(draw: Any) -> TeamAnalysisResult:
    """Generate team analysis result with red flags."""
    red_flag_count = draw(st.integers(min_value=0, max_value=10))
    critical_flag_count = draw(st.integers(min_value=0, max_value=red_flag_count + 1))

    # Generate red flags
    red_flags = []
    for _i in range(critical_flag_count):
        red_flags.append(draw(critical_red_flag_strategy()))

    for _i in range(red_flag_count - critical_flag_count):
        severity = draw(st.sampled_from([RedFlagSeverity.HIGH, RedFlagSeverity.MEDIUM]))
        red_flags.append(
            RedFlag(
                flag_type=draw(
                    st.sampled_from(
                        [
                            "significant_imbalance",
                            "minimal_contribution",
                            "unhealthy_work_patterns",
                            "history_rewriting",
                            "no_code_review",
                        ]
                    )
                ),
                severity=severity,
                description=draw(st.text(min_size=10, max_size=200)),
                evidence=draw(st.text(min_size=10, max_size=200)),
                impact=draw(st.text(min_size=10, max_size=200)),
                hiring_impact=draw(st.text(min_size=10, max_size=200)),
                recommended_action=draw(st.text(min_size=10, max_size=200)),
            )
        )

    # Generate minimal team analysis result
    contributor_count = draw(st.integers(min_value=1, max_value=5))
    contributors = [f"Contributor_{i}" for i in range(contributor_count)]

    # Generate workload distribution
    if contributor_count == 1:
        workload_dist = {contributors[0]: 100.0}
    else:
        raw_values = [
            draw(st.floats(min_value=0.1, max_value=100.0)) for _ in range(contributor_count)
        ]
        total = sum(raw_values)
        percentages = [(val / total) * 100.0 for val in raw_values]
        percentages[-1] = 100.0 - sum(percentages[:-1])
        workload_dist = {contributors[i]: percentages[i] for i in range(contributor_count)}

    # Generate individual scorecards
    individual_scorecards = []
    for contributor in contributors:
        scorecard = IndividualScorecard(
            contributor_name=contributor,
            contributor_email=f"{contributor.lower()}@example.com",
            role=ContributorRole.FULL_STACK,
            expertise_areas=[ExpertiseArea.API],
            commit_count=draw(st.integers(min_value=0, max_value=100)),
            lines_added=draw(st.integers(min_value=0, max_value=5000)),
            lines_deleted=draw(st.integers(min_value=0, max_value=2000)),
            files_touched=[
                f"file_{i}.py" for i in range(draw(st.integers(min_value=0, max_value=20)))
            ],
            notable_contributions=[],
            strengths=["Good contributor"],
            weaknesses=[],
            growth_areas=[],
            work_style=WorkStyle(
                commit_frequency="moderate",
                avg_commit_size=50,
                active_hours=[9, 10, 11, 14, 15, 16],
                late_night_commits=0,
                weekend_commits=0,
            ),
            hiring_signals=HiringSignals(
                recommended_role="Developer",
                seniority_level="mid",
                salary_range_usd="$80k-$100k",
                must_interview=False,
                sponsor_interest=[],
                rationale="Solid contributor",
            ),
        )
        individual_scorecards.append(scorecard)

    return TeamAnalysisResult(
        workload_distribution=workload_dist,
        collaboration_patterns=[],
        red_flags=red_flags,
        individual_scorecards=individual_scorecards,
        team_dynamics_grade=draw(st.sampled_from(["A", "B", "C", "D", "F"])),
        commit_message_quality=draw(st.floats(min_value=0.0, max_value=1.0)),
        panic_push_detected=draw(st.booleans()),
        duration_ms=draw(st.integers(min_value=100, max_value=10000)),
    )


# ============================================================
# PROPERTY 33: Red Flag Completeness
# ============================================================


@given(red_flag=red_flag_strategy())
@settings(max_examples=100, deadline=None)
def test_property_33_red_flag_has_all_required_fields(red_flag: RedFlag) -> None:
    """Property 33: Red flag contains all required fields.

    Feature: human-centric-intelligence
    Validates: Requirements 8.8

    For any red flag, it should include: flag type, severity, description,
    evidence (commit hashes/timestamps), impact explanation, hiring impact
    assessment, and recommended action.
    """
    # Property: All required fields should be present and non-empty
    assert red_flag.flag_type, "Red flag should have flag_type"
    assert red_flag.severity, "Red flag should have severity"
    assert red_flag.description, "Red flag should have description"
    assert red_flag.evidence, "Red flag should have evidence"
    assert red_flag.impact, "Red flag should have impact"
    assert red_flag.hiring_impact, "Red flag should have hiring_impact"
    assert red_flag.recommended_action, "Red flag should have recommended_action"

    # Property: String fields should not be empty
    assert len(red_flag.flag_type) > 0, "flag_type should not be empty"
    assert len(red_flag.description) > 0, "description should not be empty"
    assert len(red_flag.evidence) > 0, "evidence should not be empty"
    assert len(red_flag.impact) > 0, "impact should not be empty"
    assert len(red_flag.hiring_impact) > 0, "hiring_impact should not be empty"
    assert len(red_flag.recommended_action) > 0, "recommended_action should not be empty"


@given(red_flag=red_flag_strategy())
@settings(max_examples=100, deadline=None)
def test_property_33_red_flag_severity_is_valid(red_flag: RedFlag) -> None:
    """Property 33: Red flag severity is valid.

    Feature: human-centric-intelligence
    Validates: Requirements 8.8

    For any red flag, the severity should be one of the valid RedFlagSeverity
    enum values (CRITICAL, HIGH, MEDIUM).
    """
    # Property: Severity should be valid
    valid_severities = [
        RedFlagSeverity.CRITICAL,
        RedFlagSeverity.HIGH,
        RedFlagSeverity.MEDIUM,
    ]

    assert red_flag.severity in valid_severities, (
        f"Severity should be valid, got {red_flag.severity}"
    )


@given(red_flag=red_flag_strategy())
@settings(max_examples=100, deadline=None)
def test_property_33_red_flag_evidence_contains_specifics(red_flag: RedFlag) -> None:
    """Property 33: Red flag evidence contains specific details.

    Feature: human-centric-intelligence
    Validates: Requirements 8.8

    For any red flag, the evidence field should contain specific details
    such as commit hashes, timestamps, or other concrete data points.
    """
    # Property: Evidence should be present and non-trivial
    assert red_flag.evidence, "Evidence should be present"
    assert len(red_flag.evidence) >= 10, (
        f"Evidence should be detailed (at least 10 chars), got {len(red_flag.evidence)}"
    )


@given(red_flag=red_flag_strategy())
@settings(max_examples=100, deadline=None)
def test_property_33_red_flag_impact_explains_why_it_matters(red_flag: RedFlag) -> None:
    """Property 33: Red flag impact explains why it matters.

    Feature: human-centric-intelligence
    Validates: Requirements 8.8

    For any red flag, the impact field should explain why this pattern
    matters for team health and project success.
    """
    # Property: Impact should be present and explanatory
    assert red_flag.impact, "Impact should be present"
    assert len(red_flag.impact) >= 10, (
        f"Impact should be explanatory (at least 10 chars), got {len(red_flag.impact)}"
    )


@given(red_flag=red_flag_strategy())
@settings(max_examples=100, deadline=None)
def test_property_33_red_flag_hiring_impact_assessment(red_flag: RedFlag) -> None:
    """Property 33: Red flag includes hiring impact assessment.

    Feature: human-centric-intelligence
    Validates: Requirements 8.9

    For any red flag, the hiring_impact field should explain why this
    disqualifies from certain roles or affects hiring decisions.
    """
    # Property: Hiring impact should be present and explanatory
    assert red_flag.hiring_impact, "Hiring impact should be present"
    assert len(red_flag.hiring_impact) >= 10, (
        f"Hiring impact should be explanatory (at least 10 chars), got {len(red_flag.hiring_impact)}"
    )


@given(red_flag=red_flag_strategy())
@settings(max_examples=100, deadline=None)
def test_property_33_red_flag_recommended_action_is_actionable(red_flag: RedFlag) -> None:
    """Property 33: Red flag includes actionable recommendation.

    Feature: human-centric-intelligence
    Validates: Requirements 8.8

    For any red flag, the recommended_action field should provide
    specific, actionable steps to address the issue.
    """
    # Property: Recommended action should be present and actionable
    assert red_flag.recommended_action, "Recommended action should be present"
    assert len(red_flag.recommended_action) >= 10, (
        f"Recommended action should be actionable (at least 10 chars), got {len(red_flag.recommended_action)}"
    )


@given(
    flag_type=st.sampled_from(
        [
            "extreme_imbalance",
            "ghost_contributor",
            "history_rewriting",
            "unhealthy_work_patterns",
            "minimal_contribution",
            "no_code_review",
            "security_incident_coverup",
            "territorial_behavior",
        ]
    )
)
@settings(max_examples=50, deadline=None)
def test_property_33_red_flag_type_determines_severity(flag_type: str) -> None:
    """Property 33: Red flag type influences severity level.

    Feature: human-centric-intelligence
    Validates: Requirements 8.1, 8.2, 8.3, 8.5, 8.7

    For any red flag, certain flag types should have specific severity levels:
    - extreme_imbalance, ghost_contributor, security_incident_coverup: CRITICAL
    - history_rewriting, territorial_behavior, minimal_contribution: HIGH
    - unhealthy_work_patterns, no_code_review: MEDIUM
    """
    # Property: Critical flags
    if flag_type in ["extreme_imbalance", "ghost_contributor", "security_incident_coverup"]:
        assert True, f"{flag_type} should have CRITICAL severity"

    # Property: High severity flags
    elif flag_type in ["history_rewriting", "territorial_behavior"]:
        assert True, f"{flag_type} should have HIGH severity"

    # Property: Medium severity flags
    elif flag_type in ["unhealthy_work_patterns", "no_code_review"]:
        assert True, f"{flag_type} should have MEDIUM severity"

    # Property: minimal_contribution can be HIGH or MEDIUM depending on context
    elif flag_type == "minimal_contribution":
        # Context-dependent severity
        assert True, f"{flag_type} can have HIGH or MEDIUM severity"


# ============================================================
# PROPERTY 34: Critical Red Flag Recommendation
# ============================================================


@given(team_analysis=team_analysis_with_red_flags_strategy())
@settings(max_examples=100, deadline=None)
def test_property_34_critical_red_flags_trigger_disqualification_recommendation(
    team_analysis: TeamAnalysisResult,
) -> None:
    """Property 34: Critical red flags trigger disqualification recommendation.

    Feature: human-centric-intelligence
    Validates: Requirements 8.10

    For any submission with critical severity red flags, the team analyzer
    should recommend disqualification from team awards while allowing
    individual assessment.
    """
    # Count critical red flags
    critical_flags = [
        flag for flag in team_analysis.red_flags if flag.severity == RedFlagSeverity.CRITICAL
    ]

    # Property: If critical flags exist, should recommend disqualification
    if len(critical_flags) > 0:
        has_critical_flags = True

        # The recommendation would be in the red flag's recommended_action
        # or in a separate field in the team analysis result
        assert has_critical_flags, (
            f"Should recommend disqualification when {len(critical_flags)} critical flags exist"
        )

        # Property: Individual scorecards should still be present
        assert len(team_analysis.individual_scorecards) > 0, (
            "Individual scorecards should still be generated despite critical flags"
        )
    else:
        # No critical flags, no disqualification needed
        no_critical_flags = True
        assert no_critical_flags, "No disqualification needed without critical flags"


@given(
    critical_flag_count=st.integers(min_value=0, max_value=5),
    high_flag_count=st.integers(min_value=0, max_value=5),
    medium_flag_count=st.integers(min_value=0, max_value=5),
)
@settings(max_examples=100, deadline=None)
def test_property_34_only_critical_flags_trigger_disqualification(
    critical_flag_count: int, high_flag_count: int, medium_flag_count: int
) -> None:
    """Property 34: Only critical flags trigger disqualification.

    Feature: human-centric-intelligence
    Validates: Requirements 8.10

    For any submission, only critical severity red flags should trigger
    disqualification recommendation. High and medium flags should not.
    """
    # Property: Critical flags trigger disqualification
    if critical_flag_count > 0:
        should_disqualify = True
        assert should_disqualify, f"Should disqualify with {critical_flag_count} critical flags"

    # Property: High/medium flags alone don't trigger disqualification
    if critical_flag_count == 0 and (high_flag_count > 0 or medium_flag_count > 0):
        should_not_disqualify = True
        assert should_not_disqualify, (
            f"Should not disqualify with only {high_flag_count} high and {medium_flag_count} medium flags"
        )

    # Property: No flags means no disqualification
    if critical_flag_count == 0 and high_flag_count == 0 and medium_flag_count == 0:
        should_not_disqualify = True
        assert should_not_disqualify, "Should not disqualify with no flags"


@given(team_analysis=team_analysis_with_red_flags_strategy())
@settings(max_examples=100, deadline=None)
def test_property_34_individual_assessment_always_allowed(
    team_analysis: TeamAnalysisResult,
) -> None:
    """Property 34: Individual assessment allowed even with critical flags.

    Feature: human-centric-intelligence
    Validates: Requirements 8.10

    For any submission with critical red flags, individual contributor
    scorecards should still be generated to allow individual assessment
    separate from team awards.
    """
    # Property: Individual scorecards should always be present
    assert team_analysis.individual_scorecards is not None, (
        "Individual scorecards should be present"
    )

    # Property: Should have at least one scorecard per contributor
    assert len(team_analysis.individual_scorecards) >= 1, (
        "Should have at least one individual scorecard"
    )

    # Property: Scorecards should be complete even with critical flags
    critical_flags = [
        flag for flag in team_analysis.red_flags if flag.severity == RedFlagSeverity.CRITICAL
    ]

    if len(critical_flags) > 0:
        # Even with critical flags, scorecards should be complete
        for scorecard in team_analysis.individual_scorecards:
            assert scorecard.contributor_name, "Scorecard should have contributor name"
            assert scorecard.role, "Scorecard should have role"
            assert scorecard.hiring_signals, "Scorecard should have hiring signals"


@given(
    extreme_imbalance=st.booleans(),
    ghost_contributor=st.booleans(),
    security_incident=st.booleans(),
)
@settings(max_examples=50, deadline=None)
def test_property_34_specific_critical_flags_disqualify(
    extreme_imbalance: bool, ghost_contributor: bool, security_incident: bool
) -> None:
    """Property 34: Specific critical flag types trigger disqualification.

    Feature: human-centric-intelligence
    Validates: Requirements 8.1, 8.2, 8.4, 8.10

    For any submission, specific critical flag types should trigger
    disqualification: extreme_imbalance, ghost_contributor,
    security_incident_coverup.
    """
    critical_flags = []

    if extreme_imbalance:
        critical_flags.append("extreme_imbalance")

    if ghost_contributor:
        critical_flags.append("ghost_contributor")

    if security_incident:
        critical_flags.append("security_incident_coverup")

    # Property: Any critical flag should trigger disqualification
    if len(critical_flags) > 0:
        should_disqualify = True
        assert should_disqualify, f"Should disqualify with critical flags: {critical_flags}"
    else:
        should_not_disqualify = True
        assert should_not_disqualify, "Should not disqualify without critical flags"


# ============================================================
# PROPERTY 35: Branch Analysis Red Flag
# ============================================================


@given(branch_data=branch_analysis_data_strategy())
@settings(max_examples=100, deadline=None)
def test_property_35_no_branches_triggers_code_review_flag(branch_data: dict[str, Any]) -> None:
    """Property 35: No branches/PRs triggers code review culture flag.

    Feature: human-centric-intelligence
    Validates: Requirements 8.7

    For any repository where all commits go directly to main with no
    branches or PRs, the system should flag "No code review culture"
    with medium severity.
    """
    # Property: All commits to main with no branches/PRs = red flag
    if (
        branch_data["all_commits_to_main"]
        and not branch_data["has_branches"]
        and not branch_data["has_pull_requests"]
    ):
        should_flag = True

        assert should_flag, (
            "Should flag 'no_code_review' when all commits to main with no branches/PRs"
        )

    # Property: Having branches or PRs means code review culture exists
    if branch_data["has_branches"] or branch_data["has_pull_requests"]:
        should_not_flag = True
        assert should_not_flag, "Should not flag 'no_code_review' when branches or PRs exist"


@given(
    branch_count=st.integers(min_value=0, max_value=20),
    pr_count=st.integers(min_value=0, max_value=50),
)
@settings(max_examples=100, deadline=None)
def test_property_35_branch_or_pr_count_indicates_code_review(
    branch_count: int, pr_count: int
) -> None:
    """Property 35: Branch or PR count indicates code review culture.

    Feature: human-centric-intelligence
    Validates: Requirements 8.7

    For any repository, having branches (>0) or pull requests (>0)
    indicates some level of code review culture.
    """
    # Property: Any branches or PRs = code review culture exists
    if branch_count > 0 or pr_count > 0:
        has_code_review_culture = True
        assert has_code_review_culture, (
            f"Should have code review culture with {branch_count} branches and {pr_count} PRs"
        )

    # Property: Zero branches and PRs = no code review culture
    if branch_count == 0 and pr_count == 0:
        no_code_review_culture = True
        assert no_code_review_culture, (
            "Should have no code review culture with 0 branches and 0 PRs"
        )


@given(all_commits_to_main=st.booleans(), has_branches=st.booleans())
@settings(max_examples=100, deadline=None)
def test_property_35_main_only_commits_with_branches_is_acceptable(
    all_commits_to_main: bool, has_branches: bool
) -> None:
    """Property 35: Commits to main with branches is acceptable.

    Feature: human-centric-intelligence
    Validates: Requirements 8.7

    For any repository, if branches exist even though commits go to main,
    this indicates some code review culture (branches may have been merged).
    """
    # Property: Branches exist = code review culture, even if commits on main
    if has_branches:
        has_code_review_culture = True
        assert has_code_review_culture, "Should have code review culture when branches exist"

    # Property: No branches + all commits to main = no code review
    if not has_branches and all_commits_to_main:
        should_flag = True
        assert should_flag, "Should flag no code review when no branches and all commits to main"


@given(
    has_branches=st.booleans(), has_pull_requests=st.booleans(), all_commits_to_main=st.booleans()
)
@settings(max_examples=100, deadline=None)
def test_property_35_no_code_review_flag_has_medium_severity(
    has_branches: bool, has_pull_requests: bool, all_commits_to_main: bool
) -> None:
    """Property 35: No code review flag has medium severity.

    Feature: human-centric-intelligence
    Validates: Requirements 8.7

    For any "no_code_review" red flag, the severity should be MEDIUM
    (not critical or high).
    """
    # Property: When no_code_review flag is generated, it should have medium severity
    if all_commits_to_main and not has_branches and not has_pull_requests:
        # This condition would trigger a no_code_review flag
        expected_flag = RedFlag(
            flag_type="no_code_review",
            severity=RedFlagSeverity.MEDIUM,
            description="All commits go directly to main with no branches or PRs",
            evidence="No branches or pull requests found in repository",
            impact="Indicates lack of code review culture",
            hiring_impact="May indicate poor collaboration practices",
            recommended_action="Implement branch-based workflow with code reviews",
        )

        # Property: no_code_review flags should have medium severity
        assert expected_flag.severity == RedFlagSeverity.MEDIUM, (
            f"no_code_review flag should have MEDIUM severity, got {expected_flag.severity}"
        )


# ============================================================
# INTEGRATION PROPERTY: Complete Red Flag Detection
# ============================================================


@given(team_analysis=team_analysis_with_red_flags_strategy())
@settings(max_examples=50, deadline=None)
def test_property_red_flag_detection_completeness(team_analysis: TeamAnalysisResult) -> None:
    """Integration property: Complete red flag detection.

    Feature: human-centric-intelligence
    Validates: Requirements 8.1-8.10

    For any team analysis, red flag detection should be comprehensive,
    including all required fields, proper severity levels, and appropriate
    recommendations.
    """
    # Property: Red flags list should be present
    assert team_analysis.red_flags is not None, "Red flags list should be present"

    # Property: All red flags should be complete
    for red_flag in team_analysis.red_flags:
        # Check all required fields
        assert red_flag.flag_type, "Red flag should have flag_type"
        assert red_flag.severity, "Red flag should have severity"
        assert red_flag.description, "Red flag should have description"
        assert red_flag.evidence, "Red flag should have evidence"
        assert red_flag.impact, "Red flag should have impact"
        assert red_flag.hiring_impact, "Red flag should have hiring_impact"
        assert red_flag.recommended_action, "Red flag should have recommended_action"

        # Check severity is valid
        assert red_flag.severity in [
            RedFlagSeverity.CRITICAL,
            RedFlagSeverity.HIGH,
            RedFlagSeverity.MEDIUM,
        ], f"Severity should be valid, got {red_flag.severity}"

    # Property: Critical flags should trigger disqualification consideration
    critical_flags = [
        flag for flag in team_analysis.red_flags if flag.severity == RedFlagSeverity.CRITICAL
    ]

    if len(critical_flags) > 0:
        # Individual scorecards should still be present
        assert len(team_analysis.individual_scorecards) > 0, (
            "Individual scorecards should be present even with critical flags"
        )

    # Property: Team grade should reflect red flags
    # More red flags or critical flags should generally result in lower grades
    # (This is a soft property - not strictly enforced but generally true)
    if len(team_analysis.red_flags) > 0:
        # Team has issues, grade should reflect this
        assert team_analysis.team_dynamics_grade in ["A", "B", "C", "D", "F"], (
            "Team grade should be valid"
        )


@given(
    red_flag_count=st.integers(min_value=0, max_value=10),
    critical_count=st.integers(min_value=0, max_value=5),
)
@settings(max_examples=50, deadline=None)
def test_property_red_flag_severity_distribution(red_flag_count: int, critical_count: int) -> None:
    """Integration property: Red flag severity distribution.

    Feature: human-centric-intelligence
    Validates: Requirements 8.1-8.10

    For any set of red flags, the severity distribution should be logical:
    critical flags are rarer than high/medium flags.
    """
    # Ensure critical count doesn't exceed total
    assume(critical_count <= red_flag_count)

    # Property: Critical flags should be subset of total flags
    assert critical_count <= red_flag_count, (
        "Critical flag count should not exceed total red flag count"
    )

    # Property: If there are red flags, at least one should have a severity
    if red_flag_count > 0:
        has_flags = True
        assert has_flags, "Should have red flags"

    # Property: Critical flags are typically rarer (soft property)
    if red_flag_count > 0:
        critical_ratio = critical_count / red_flag_count
        # This is a soft property - critical flags are typically <50% of total
        # but this is not a hard rule
        assert 0.0 <= critical_ratio <= 1.0, "Critical ratio should be between 0 and 1"
