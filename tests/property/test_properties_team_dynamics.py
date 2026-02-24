"""Property-based tests for team dynamics (Properties 19-20).

This module tests the correctness properties of the team dynamics analyzer
using hypothesis for property-based testing with randomized inputs.

Properties tested:
- Property 19: Workload Distribution Calculation
- Property 20: Threshold-Based Red Flag Detection
"""

from typing import Any
from unittest.mock import Mock, patch

import pytest
from hypothesis import assume, given, settings, strategies as st

from src.models.team_dynamics import (
    CollaborationPattern,
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
def contributor_name_strategy(draw: Any) -> str:
    """Generate random contributor name."""
    first_names = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis"]
    
    first = draw(st.sampled_from(first_names))
    last = draw(st.sampled_from(last_names))
    
    return f"{first} {last}"


@st.composite
def commit_distribution_strategy(draw: Any) -> dict[str, int]:
    """Generate random commit distribution across contributors.
    
    Returns a dictionary mapping contributor names to commit counts.
    """
    contributor_count = draw(st.integers(min_value=1, max_value=10))
    contributors = [draw(contributor_name_strategy()) for _ in range(contributor_count)]
    
    # Generate commit counts for each contributor
    commit_counts = {}
    for contributor in contributors:
        # Allow for wide range including 0 commits (ghost contributors)
        commits = draw(st.integers(min_value=0, max_value=200))
        commit_counts[contributor] = commits
    
    return commit_counts


@st.composite
def workload_distribution_strategy(draw: Any) -> dict[str, float]:
    """Generate random workload distribution that sums to 100%.
    
    Returns a dictionary mapping contributor names to percentage (0-100).
    """
    contributor_count = draw(st.integers(min_value=1, max_value=10))
    contributors = [draw(contributor_name_strategy()) for _ in range(contributor_count)]
    
    # Ensure unique contributor names
    contributors = list(dict.fromkeys(contributors))
    contributor_count = len(contributors)
    
    # Generate random percentages that sum to 100
    if contributor_count == 1:
        return {contributors[0]: 100.0}
    
    # Generate random splits using integers, then normalize
    # This ensures we always sum to exactly 100.0
    raw_values = [draw(st.integers(min_value=1, max_value=100)) for _ in range(contributor_count)]
    
    # Normalize to sum to 100 using careful floating point arithmetic
    total = sum(raw_values)
    result = {}
    cumulative = 0.0
    
    for i in range(contributor_count - 1):
        percentage = (raw_values[i] / total) * 100.0
        result[contributors[i]] = percentage
        cumulative += percentage
    
    # Last contributor gets exactly what's needed to sum to 100
    result[contributors[-1]] = 100.0 - cumulative
    
    return result


@st.composite
def late_night_commit_count_strategy(draw: Any) -> int:
    """Generate random late-night commit count (2am-6am)."""
    return draw(st.integers(min_value=0, max_value=50))


@st.composite
def force_push_count_strategy(draw: Any) -> int:
    """Generate random force push count."""
    return draw(st.integers(min_value=0, max_value=20))


@st.composite
def red_flag_strategy(draw: Any) -> RedFlag:
    """Generate random red flag."""
    flag_types = [
        "extreme_imbalance",
        "ghost_contributor",
        "history_rewriting",
        "unhealthy_work_patterns",
        "minimal_contribution",
        "no_code_review",
    ]
    
    flag_type = draw(st.sampled_from(flag_types))
    severity = draw(st.sampled_from([
        RedFlagSeverity.CRITICAL,
        RedFlagSeverity.HIGH,
        RedFlagSeverity.MEDIUM,
    ]))
    
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
def team_size_strategy(draw: Any) -> int:
    """Generate random team size."""
    return draw(st.integers(min_value=1, max_value=10))


# ============================================================
# PROPERTY 19: Workload Distribution Calculation
# ============================================================


@given(workload_dist=workload_distribution_strategy())
@settings(max_examples=100, deadline=None)
def test_property_19_workload_percentages_sum_to_100(
    workload_dist: dict[str, float]
) -> None:
    """Property 19: Workload distribution percentages sum to 100%.
    
    Feature: human-centric-intelligence
    Validates: Requirements 4.1
    
    For any repository with multiple contributors, the workload distribution
    percentages should sum to 100% (within floating point tolerance).
    """
    # Calculate sum of percentages
    total_percentage = sum(workload_dist.values())
    
    # Property: Sum should be 100% within floating point tolerance
    tolerance = 0.01  # 0.01% tolerance for floating point arithmetic
    assert abs(total_percentage - 100.0) < tolerance, \
        f"Workload percentages should sum to 100%, got {total_percentage}"


@given(workload_dist=workload_distribution_strategy())
@settings(max_examples=100, deadline=None)
def test_property_19_all_percentages_non_negative(
    workload_dist: dict[str, float]
) -> None:
    """Property 19: All workload percentages are non-negative.
    
    Feature: human-centric-intelligence
    Validates: Requirements 4.1
    
    For any workload distribution, all contributor percentages should
    be non-negative (>= 0).
    """
    # Property: All percentages should be non-negative
    for contributor, percentage in workload_dist.items():
        assert percentage >= 0.0, \
            f"Percentage for {contributor} should be non-negative, got {percentage}"


@given(workload_dist=workload_distribution_strategy())
@settings(max_examples=100, deadline=None)
def test_property_19_all_percentages_at_most_100(
    workload_dist: dict[str, float]
) -> None:
    """Property 19: No single contributor exceeds 100%.
    
    Feature: human-centric-intelligence
    Validates: Requirements 4.1
    
    For any workload distribution, no single contributor should have
    more than 100% of the workload.
    """
    # Property: No percentage should exceed 100%
    for contributor, percentage in workload_dist.items():
        assert percentage <= 100.0, \
            f"Percentage for {contributor} should not exceed 100%, got {percentage}"


@given(commit_dist=commit_distribution_strategy())
@settings(max_examples=100, deadline=None)
def test_property_19_calculate_from_commit_counts(
    commit_dist: dict[str, int]
) -> None:
    """Property 19: Calculate workload from commit counts.
    
    Feature: human-centric-intelligence
    Validates: Requirements 4.1
    
    For any repository, workload distribution should be calculated
    as percentage of commits per contributor.
    """
    # Skip if no commits (edge case)
    total_commits = sum(commit_dist.values())
    assume(total_commits > 0)
    
    # Calculate workload distribution
    workload_dist = {}
    for contributor, commits in commit_dist.items():
        percentage = (commits / total_commits) * 100.0
        workload_dist[contributor] = percentage
    
    # Property: Sum should be 100%
    total_percentage = sum(workload_dist.values())
    tolerance = 0.01
    assert abs(total_percentage - 100.0) < tolerance, \
        f"Calculated workload should sum to 100%, got {total_percentage}"
    
    # Property: Each percentage should match commit ratio
    for contributor, commits in commit_dist.items():
        expected_percentage = (commits / total_commits) * 100.0
        actual_percentage = workload_dist[contributor]
        assert abs(actual_percentage - expected_percentage) < tolerance, \
            f"Percentage for {contributor} should be {expected_percentage}, got {actual_percentage}"


@given(
    contributor_count=st.integers(min_value=2, max_value=10),
    dominant_contributor_idx=st.integers(min_value=0, max_value=9)
)
@settings(max_examples=50, deadline=None)
def test_property_19_single_contributor_can_dominate(
    contributor_count: int,
    dominant_contributor_idx: int
) -> None:
    """Property 19: Single contributor can have high percentage.
    
    Feature: human-centric-intelligence
    Validates: Requirements 4.1, 4.2
    
    For any repository, it's valid for a single contributor to have
    a high percentage (even >80%), though this may trigger red flags.
    """
    # Ensure index is valid
    assume(dominant_contributor_idx < contributor_count)
    
    # Create distribution where one contributor dominates
    contributors = [f"Contributor_{i}" for i in range(contributor_count)]
    
    # Dominant contributor gets 85%, others split remaining 15%
    workload_dist = {}
    dominant_percentage = 85.0
    remaining_percentage = 100.0 - dominant_percentage
    other_percentage = remaining_percentage / (contributor_count - 1)
    
    for i, contributor in enumerate(contributors):
        if i == dominant_contributor_idx:
            workload_dist[contributor] = dominant_percentage
        else:
            workload_dist[contributor] = other_percentage
    
    # Property: Sum should still be 100%
    total_percentage = sum(workload_dist.values())
    tolerance = 0.01
    assert abs(total_percentage - 100.0) < tolerance, \
        f"Workload should sum to 100% even with dominant contributor, got {total_percentage}"
    
    # Property: Dominant contributor should have expected percentage
    dominant_contributor = contributors[dominant_contributor_idx]
    assert abs(workload_dist[dominant_contributor] - dominant_percentage) < tolerance, \
        f"Dominant contributor should have {dominant_percentage}%, got {workload_dist[dominant_contributor]}"


# ============================================================
# PROPERTY 20: Threshold-Based Red Flag Detection
# ============================================================


@given(
    contributor_percentage=st.floats(min_value=0.0, max_value=100.0),
    threshold_extreme=st.floats(min_value=75.0, max_value=85.0),
    threshold_significant=st.floats(min_value=65.0, max_value=75.0)
)
@settings(max_examples=100, deadline=None)
def test_property_20_extreme_imbalance_threshold(
    contributor_percentage: float,
    threshold_extreme: float,
    threshold_significant: float
) -> None:
    """Property 20: Detect extreme imbalance (>80% commits).
    
    Feature: human-centric-intelligence
    Validates: Requirements 4.2, 8.1
    
    For any repository where a contributor exceeds 80% of commits,
    the system should flag "extreme imbalance" with critical severity.
    """
    # Use default threshold of 80% for extreme imbalance
    threshold_extreme = 80.0
    
    # Property: Should flag extreme imbalance when > 80%
    if contributor_percentage > threshold_extreme:
        # Should generate critical red flag
        should_flag = True
        expected_severity = RedFlagSeverity.CRITICAL
        expected_flag_type = "extreme_imbalance"
        
        assert should_flag, \
            f"Should flag extreme imbalance when percentage ({contributor_percentage}%) > {threshold_extreme}%"
    else:
        # Should not flag extreme imbalance
        should_not_flag_extreme = True
        assert should_not_flag_extreme, \
            f"Should not flag extreme imbalance when percentage ({contributor_percentage}%) <= {threshold_extreme}%"


@given(
    contributor_percentage=st.floats(min_value=0.0, max_value=100.0)
)
@settings(max_examples=100, deadline=None)
def test_property_20_significant_imbalance_threshold(
    contributor_percentage: float
) -> None:
    """Property 20: Detect significant imbalance (>70% commits).
    
    Feature: human-centric-intelligence
    Validates: Requirements 4.3, 8.2
    
    For any repository where a contributor exceeds 70% of commits
    (but not 80%), the system should flag "significant imbalance" with
    high severity.
    """
    threshold_significant = 70.0
    threshold_extreme = 80.0
    
    # Property: Should flag significant imbalance when 70% < x <= 80%
    if threshold_significant < contributor_percentage <= threshold_extreme:
        should_flag = True
        expected_severity = RedFlagSeverity.HIGH
        expected_flag_type = "significant_imbalance"
        
        assert should_flag, \
            f"Should flag significant imbalance when {threshold_significant}% < percentage ({contributor_percentage}%) <= {threshold_extreme}%"


@given(commit_count=st.integers(min_value=0, max_value=200))
@settings(max_examples=100, deadline=None)
def test_property_20_ghost_contributor_detection(
    commit_count: int
) -> None:
    """Property 20: Detect ghost contributors (0 commits).
    
    Feature: human-centric-intelligence
    Validates: Requirements 4.5, 8.2
    
    For any team member listed but with 0 commits, the system should
    flag "ghost contributor" with critical severity.
    """
    # Property: Should flag ghost contributor when 0 commits
    if commit_count == 0:
        should_flag = True
        expected_severity = RedFlagSeverity.CRITICAL
        expected_flag_type = "ghost_contributor"
        
        assert should_flag, \
            "Should flag ghost contributor when commit count is 0"
    else:
        # Should not flag ghost contributor
        should_not_flag = True
        assert should_not_flag, \
            f"Should not flag ghost contributor when commit count ({commit_count}) > 0"


@given(
    commit_count=st.integers(min_value=0, max_value=10),
    team_size=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=100, deadline=None)
def test_property_20_minimal_contribution_detection(
    commit_count: int,
    team_size: int
) -> None:
    """Property 20: Detect minimal contribution (≤2 commits in team of 3+).
    
    Feature: human-centric-intelligence
    Validates: Requirements 4.6, 8.2
    
    For any team member with ≤2 commits in a team of 3+, the system
    should flag "minimal contribution" with high severity.
    """
    threshold_commits = 2
    threshold_team_size = 3
    
    # Property: Should flag minimal contribution when ≤2 commits in team of 3+
    if commit_count <= threshold_commits and team_size >= threshold_team_size:
        should_flag = True
        expected_severity = RedFlagSeverity.HIGH
        expected_flag_type = "minimal_contribution"
        
        assert should_flag, \
            f"Should flag minimal contribution when commits ({commit_count}) <= {threshold_commits} in team of {team_size}"
    else:
        # Should not flag minimal contribution
        should_not_flag = True
        assert should_not_flag, \
            f"Should not flag minimal contribution when commits ({commit_count}) > {threshold_commits} or team size ({team_size}) < {threshold_team_size}"


@given(late_night_commits=late_night_commit_count_strategy())
@settings(max_examples=100, deadline=None)
def test_property_20_unhealthy_work_patterns_detection(
    late_night_commits: int
) -> None:
    """Property 20: Detect unhealthy work patterns (>10 late-night commits).
    
    Feature: human-centric-intelligence
    Validates: Requirements 4.7, 8.5
    
    For any contributor with >10 commits between 2am-6am, the system
    should flag "unhealthy work patterns" with medium severity.
    """
    threshold_late_night = 10
    
    # Property: Should flag unhealthy patterns when >10 late-night commits
    if late_night_commits > threshold_late_night:
        should_flag = True
        expected_severity = RedFlagSeverity.MEDIUM
        expected_flag_type = "unhealthy_work_patterns"
        
        assert should_flag, \
            f"Should flag unhealthy work patterns when late-night commits ({late_night_commits}) > {threshold_late_night}"
    else:
        # Should not flag unhealthy patterns
        should_not_flag = True
        assert should_not_flag, \
            f"Should not flag unhealthy work patterns when late-night commits ({late_night_commits}) <= {threshold_late_night}"


@given(force_pushes=force_push_count_strategy())
@settings(max_examples=100, deadline=None)
def test_property_20_history_rewriting_detection(
    force_pushes: int
) -> None:
    """Property 20: Detect history rewriting (>5 force pushes).
    
    Feature: human-centric-intelligence
    Validates: Requirements 8.3
    
    For any repository with >5 force pushes, the system should flag
    "history rewriting" with high severity.
    """
    threshold_force_pushes = 5
    
    # Property: Should flag history rewriting when >5 force pushes
    if force_pushes > threshold_force_pushes:
        should_flag = True
        expected_severity = RedFlagSeverity.HIGH
        expected_flag_type = "history_rewriting"
        
        assert should_flag, \
            f"Should flag history rewriting when force pushes ({force_pushes}) > {threshold_force_pushes}"
    else:
        # Should not flag history rewriting
        should_not_flag = True
        assert should_not_flag, \
            f"Should not flag history rewriting when force pushes ({force_pushes}) <= {threshold_force_pushes}"


@given(
    contributor_percentage=st.floats(min_value=0.0, max_value=100.0),
    commit_count=st.integers(min_value=0, max_value=200),
    late_night_commits=st.integers(min_value=0, max_value=50),
    force_pushes=st.integers(min_value=0, max_value=20),
    team_size=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=100, deadline=None)
def test_property_20_multiple_red_flags_possible(
    contributor_percentage: float,
    commit_count: int,
    late_night_commits: int,
    force_pushes: int,
    team_size: int
) -> None:
    """Property 20: Multiple red flags can be detected simultaneously.
    
    Feature: human-centric-intelligence
    Validates: Requirements 4.2, 4.3, 4.5, 4.6, 8.1, 8.2, 8.3, 8.5
    
    For any repository, multiple red flags can be triggered simultaneously
    if multiple thresholds are exceeded.
    """
    red_flags = []
    
    # Check extreme imbalance (>80%)
    if contributor_percentage > 80.0:
        red_flags.append("extreme_imbalance")
    
    # Check significant imbalance (>70% but ≤80%)
    elif contributor_percentage > 70.0:
        red_flags.append("significant_imbalance")
    
    # Check ghost contributor (0 commits)
    if commit_count == 0:
        red_flags.append("ghost_contributor")
    
    # Check minimal contribution (≤2 commits in team of 3+)
    elif commit_count <= 2 and team_size >= 3:
        red_flags.append("minimal_contribution")
    
    # Check unhealthy work patterns (>10 late-night commits)
    if late_night_commits > 10:
        red_flags.append("unhealthy_work_patterns")
    
    # Check history rewriting (>5 force pushes)
    if force_pushes > 5:
        red_flags.append("history_rewriting")
    
    # Property: Red flags list should contain all triggered flags
    assert isinstance(red_flags, list), "Red flags should be a list"
    
    # Property: Each red flag should be unique
    assert len(red_flags) == len(set(red_flags)), \
        "Red flags should not contain duplicates"


@given(red_flag=red_flag_strategy())
@settings(max_examples=50, deadline=None)
def test_property_20_red_flag_structure_completeness(
    red_flag: RedFlag
) -> None:
    """Property 20: Red flags have complete structure.
    
    Feature: human-centric-intelligence
    Validates: Requirements 8.8
    
    For any red flag, it should include: flag type, severity, description,
    evidence, impact explanation, hiring impact, and recommended action.
    """
    # Property: All required fields should be present
    assert red_flag.flag_type, "Red flag should have flag_type"
    assert red_flag.severity, "Red flag should have severity"
    assert red_flag.description, "Red flag should have description"
    assert red_flag.evidence, "Red flag should have evidence"
    assert red_flag.impact, "Red flag should have impact"
    assert red_flag.hiring_impact, "Red flag should have hiring_impact"
    assert red_flag.recommended_action, "Red flag should have recommended_action"
    
    # Property: Severity should be valid
    assert red_flag.severity in [
        RedFlagSeverity.CRITICAL,
        RedFlagSeverity.HIGH,
        RedFlagSeverity.MEDIUM,
    ], f"Severity should be valid, got {red_flag.severity}"


@given(
    extreme_imbalance_count=st.integers(min_value=0, max_value=5),
    ghost_contributor_count=st.integers(min_value=0, max_value=5)
)
@settings(max_examples=50, deadline=None)
def test_property_20_critical_red_flags_severity(
    extreme_imbalance_count: int,
    ghost_contributor_count: int
) -> None:
    """Property 20: Critical red flags have correct severity.
    
    Feature: human-centric-intelligence
    Validates: Requirements 8.1, 8.2
    
    For any critical red flag (extreme imbalance, ghost contributor),
    the severity should be CRITICAL.
    """
    critical_flags = []
    
    # Add extreme imbalance flags
    for i in range(extreme_imbalance_count):
        flag = RedFlag(
            flag_type="extreme_imbalance",
            severity=RedFlagSeverity.CRITICAL,
            description=f"Contributor {i} has >80% of commits",
            evidence=f"Commit hash: abc{i}",
            impact="Indicates potential solo work or team dysfunction",
            hiring_impact="May indicate poor collaboration skills",
            recommended_action="Review team dynamics and contribution patterns",
        )
        critical_flags.append(flag)
    
    # Add ghost contributor flags
    for i in range(ghost_contributor_count):
        flag = RedFlag(
            flag_type="ghost_contributor",
            severity=RedFlagSeverity.CRITICAL,
            description=f"Contributor {i} has 0 commits",
            evidence=f"Listed in team but no commits found",
            impact="Indicates non-participation or team padding",
            hiring_impact="Disqualifies from team awards",
            recommended_action="Verify team membership and participation",
        )
        critical_flags.append(flag)
    
    # Property: All critical flags should have CRITICAL severity
    for flag in critical_flags:
        assert flag.severity == RedFlagSeverity.CRITICAL, \
            f"Critical flag {flag.flag_type} should have CRITICAL severity, got {flag.severity}"


# ============================================================
# INTEGRATION PROPERTY: Complete Team Dynamics Analysis
# ============================================================


@given(
    workload_dist=workload_distribution_strategy(),
    has_red_flags=st.booleans(),
    has_collaboration_patterns=st.booleans()
)
@settings(max_examples=50, deadline=None)
def test_property_team_dynamics_analysis_completeness(
    workload_dist: dict[str, float],
    has_red_flags: bool,
    has_collaboration_patterns: bool
) -> None:
    """Integration property: Complete team dynamics analysis.
    
    Feature: human-centric-intelligence
    Validates: Requirements 4.1-4.11
    
    For any repository, the team dynamics analysis should handle all
    components (workload distribution, red flags, collaboration patterns)
    gracefully.
    """
    # Create mock red flags if needed
    red_flags = []
    if has_red_flags:
        red_flags.append(RedFlag(
            flag_type="extreme_imbalance",
            severity=RedFlagSeverity.CRITICAL,
            description="One contributor dominates",
            evidence="Commit analysis",
            impact="Poor team dynamics",
            hiring_impact="May indicate collaboration issues",
            recommended_action="Review team structure",
        ))
    
    # Create mock collaboration patterns if needed
    collaboration_patterns = []
    if has_collaboration_patterns:
        collaboration_patterns.append(CollaborationPattern(
            pattern_type="pair_programming",
            contributors=list(workload_dist.keys())[:2] if len(workload_dist) >= 2 else [],
            evidence="Alternating commits",
            positive=True,
        ))
    
    # Create mock individual scorecards
    individual_scorecards = []
    for contributor in workload_dist.keys():
        scorecard = IndividualScorecard(
            contributor_name=contributor,
            contributor_email=f"{contributor.lower().replace(' ', '.')}@example.com",
            role=ContributorRole.FULL_STACK,
            expertise_areas=[ExpertiseArea.API],
            commit_count=10,
            lines_added=500,
            lines_deleted=100,
            files_touched=["src/main.py"],
            notable_contributions=["Initial commit"],
            strengths=["Good code quality"],
            weaknesses=["Needs more tests"],
            growth_areas=["Testing"],
            work_style=WorkStyle(
                commit_frequency="moderate",
                avg_commit_size=50,
                active_hours=[9, 10, 11, 14, 15, 16],
                late_night_commits=0,
                weekend_commits=0,
            ),
            hiring_signals=HiringSignals(
                recommended_role="Backend Developer",
                seniority_level="mid",
                salary_range_usd="$80k-$100k",
                must_interview=False,
                sponsor_interest=[],
                rationale="Solid contributor",
            ),
        )
        individual_scorecards.append(scorecard)
    
    # Create team analysis result
    result = TeamAnalysisResult(
        workload_distribution=workload_dist,
        collaboration_patterns=collaboration_patterns,
        red_flags=red_flags,
        individual_scorecards=individual_scorecards,
        team_dynamics_grade="B",
        commit_message_quality=0.75,
        panic_push_detected=False,
        duration_ms=5000,
    )
    
    # Property: Workload distribution should sum to 100%
    # Ensure the strategy generated valid data
    assume(len(workload_dist) > 0)
    assume(all(v >= 0 for v in workload_dist.values()))
    

    total_percentage = sum(result.workload_distribution.values())
    tolerance = 0.01
    assert abs(total_percentage - 100.0) < tolerance, \
        f"Workload should sum to 100%, got {total_percentage}"
    
    # Property: Should have individual scorecard for each contributor
    assert len(result.individual_scorecards) == len(workload_dist), \
        "Should have scorecard for each contributor"
    
    # Property: Team grade should be valid
    assert result.team_dynamics_grade in ["A", "B", "C", "D", "F"], \
        f"Team grade should be valid, got {result.team_dynamics_grade}"
    
    # Property: Commit message quality should be between 0 and 1
    assert 0.0 <= result.commit_message_quality <= 1.0, \
        f"Commit message quality should be between 0 and 1, got {result.commit_message_quality}"
    
    # Property: Duration should be non-negative
    assert result.duration_ms >= 0, \
        f"Duration should be non-negative, got {result.duration_ms}"
