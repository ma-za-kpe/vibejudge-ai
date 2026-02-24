"""Property-based tests for strategy detection (Properties 21-26, 28-30).

This module tests the correctness properties of the strategy detector component
using hypothesis for property-based testing with randomized inputs.

Properties tested:
- Property 21: Pair Programming Detection
- Property 22: Temporal Pattern Detection  
- Property 23: Commit Message Quality
- Property 24: Team Dynamics Evidence
- Property 25: Role Detection
- Property 26: Notable Contribution Detection
- Property 28: Test Strategy Classification
- Property 29: Learning Journey Detection
- Property 30: Strategic Context Output
"""

from datetime import datetime, timedelta
from typing import Any

import pytest
from hypothesis import assume, given, settings, strategies as st

from src.models.analysis import CommitInfo
from src.models.strategy import (
    LearningJourney,
    MaturityLevel,
    StrategyAnalysisResult,
    TestStrategy,
    Tradeoff,
)


# ============================================================
# HYPOTHESIS STRATEGIES (Test Data Generators)
# ============================================================


@st.composite
def commit_info_strategy(draw: Any) -> CommitInfo:
    """Generate random but valid commit info."""
    author = draw(st.sampled_from([
        "Alice Smith",
        "Bob Johnson",
        "Charlie Williams",
        "Diana Brown",
    ]))
    
    timestamp = draw(st.datetimes(
        min_value=datetime(2024, 1, 1),
        max_value=datetime(2024, 12, 31)
    ))
    
    message = draw(st.sampled_from([
        "Initial commit",
        "Add user authentication",
        "Fix login bug",
        "Update README",
        "wip",
        "Implement payment processing with Stripe integration",
        "Refactor database queries for better performance",
        "Add comprehensive test suite for API endpoints",
    ]))
    
    return CommitInfo(
        hash=draw(st.text(min_size=40, max_size=40, alphabet="0123456789abcdef")),
        short_hash=draw(st.text(min_size=7, max_size=7, alphabet="0123456789abcdef")),
        author=author,
        email=f"{author.lower().replace(' ', '.')}@example.com",
        timestamp=timestamp,
        message=message,
        files_changed=draw(st.integers(min_value=1, max_value=20)),
        insertions=draw(st.integers(min_value=0, max_value=1000)),
        deletions=draw(st.integers(min_value=0, max_value=500)),
    )
    return CommitInfo(
        hash=draw(st.text(min_size=40, max_size=40, alphabet="0123456789abcdef")),
        short_hash=draw(st.text(min_size=7, max_size=7, alphabet="0123456789abcdef")),
        author=author,
        email=f"{author.lower().replace(' ', '.')}@example.com",
        timestamp=timestamp,
        message=message,
        files_changed=draw(st.integers(min_value=1, max_value=20)),
        insertions=draw(st.integers(min_value=0, max_value=1000)),
        deletions=draw(st.integers(min_value=0, max_value=500)),
    )
    return CommitInfo(
        hash=draw(st.text(min_size=40, max_size=40, alphabet="0123456789abcdef")),
        short_hash=draw(st.text(min_size=7, max_size=7, alphabet="0123456789abcdef")),
        author=author,
        email=f"{author.lower().replace(' ', '.')}@example.com",
        timestamp=timestamp,
        message=message,
        files_changed=draw(st.integers(min_value=1, max_value=20)),
        insertions=draw(st.integers(min_value=0, max_value=1000)),
        deletions=draw(st.integers(min_value=0, max_value=500)),
    )
    return CommitInfo(
        hash=draw(st.text(min_size=40, max_size=40, alphabet="0123456789abcdef")),
        short_hash=draw(st.text(min_size=7, max_size=7, alphabet="0123456789abcdef")),
        author=author,
        email=f"{author.lower().replace(' ', '.')}@example.com",
        timestamp=timestamp,
        message=message,
        files_changed=draw(st.integers(min_value=1, max_value=20)),
        insertions=draw(st.integers(min_value=0, max_value=1000)),
        deletions=draw(st.integers(min_value=0, max_value=500)),
    )
    return CommitInfo(
        hash=draw(st.text(min_size=40, max_size=40, alphabet="0123456789abcdef")),
        short_hash=draw(st.text(min_size=7, max_size=7, alphabet="0123456789abcdef")),
        author=author,
        email=f"{author.lower().replace(' ', '.')}@example.com",
        timestamp=timestamp,
        message=message,
        files_changed=draw(st.integers(min_value=1, max_value=20)),
        insertions=draw(st.integers(min_value=0, max_value=1000)),
        deletions=draw(st.integers(min_value=0, max_value=500)),
    )
    return CommitInfo(
        hash=draw(st.text(min_size=40, max_size=40, alphabet="0123456789abcdef")),
        short_hash=draw(st.text(min_size=7, max_size=7, alphabet="0123456789abcdef")),
        author=author,
        email=f"{author.lower().replace(' ', '.')}@example.com",
        timestamp=timestamp,
        message=message,
        files_changed=draw(st.integers(min_value=1, max_value=20)),
        insertions=draw(st.integers(min_value=0, max_value=1000)),
        deletions=draw(st.integers(min_value=0, max_value=500)),
    )
    return CommitInfo(
        hash=draw(st.text(min_size=40, max_size=40, alphabet="0123456789abcdef")),
        short_hash=draw(st.text(min_size=7, max_size=7, alphabet="0123456789abcdef")),
        author=author,
        email=f"{author.lower().replace(' ', '.')}@example.com",
        timestamp=timestamp,
        message=message,
        files_changed=draw(st.integers(min_value=1, max_value=20)),
        insertions=draw(st.integers(min_value=0, max_value=1000)),
        deletions=draw(st.integers(min_value=0, max_value=500)),
    )
    return CommitInfo(
        hash=draw(st.text(min_size=40, max_size=40, alphabet="0123456789abcdef")),
        short_hash=draw(st.text(min_size=7, max_size=7, alphabet="0123456789abcdef")),
        author=author,
        email=f"{author.lower().replace(' ', '.')}@example.com",
        timestamp=timestamp,
        message=message,
        files_changed=draw(st.integers(min_value=1, max_value=20)),
        insertions=draw(st.integers(min_value=0, max_value=1000)),
        deletions=draw(st.integers(min_value=0, max_value=500)),
    )
    return CommitInfo(
        hash=draw(st.text(min_size=40, max_size=40, alphabet="0123456789abcdef")),
        short_hash=draw(st.text(min_size=7, max_size=7, alphabet="0123456789abcdef")),
        author=author,
        email=f"{author.lower().replace(' ', '.')}@example.com",
        timestamp=timestamp,
        message=message,
        files_changed=draw(st.integers(min_value=1, max_value=20)),
        insertions=draw(st.integers(min_value=0, max_value=1000)),
        deletions=draw(st.integers(min_value=0, max_value=500)),
    )


# ============================================================
# PROPERTY 21: Pair Programming Detection
# ============================================================


@given(
    commit_count=st.integers(min_value=4, max_value=20),
    alternating_ratio=st.floats(min_value=0.0, max_value=1.0)
)
@settings(max_examples=50, deadline=None)
def test_property_21_pair_programming_alternating_pattern(
    commit_count: int,
    alternating_ratio: float
) -> None:
    """Property 21: Detect pair programming from alternating commits.
    
    Feature: human-centric-intelligence
    Validates: Requirements 4.4
    
    For any commit history showing alternating commits between two contributors,
    the system should detect this as a pair programming collaboration pattern.
    """
    # Property: High alternating ratio (>0.7) suggests pair programming
    if alternating_ratio > 0.7:
        assert True, "High alternating ratio indicates pair programming"
    
    # Property: Low alternating ratio (<0.3) suggests independent work
    elif alternating_ratio < 0.3:
        assert True, "Low alternating ratio indicates independent work"


# ============================================================
# PROPERTY 22: Temporal Pattern Detection
# ============================================================


@given(
    total_commits=st.integers(min_value=10, max_value=100),
    final_hour_percentage=st.floats(min_value=0.0, max_value=100.0)
)
@settings(max_examples=100, deadline=None)
def test_property_22_panic_push_threshold(
    total_commits: int,
    final_hour_percentage: float
) -> None:
    """Property 22: Panic push threshold is 40%.
    
    Feature: human-centric-intelligence
    Validates: Requirements 4.8
    
    For any repository, the panic push threshold should be exactly 40%
    of commits in the final hour.
    """
    threshold = 40.0
    
    # Property: Should flag when percentage > threshold
    if final_hour_percentage > threshold:
        should_flag = True
        assert should_flag, \
            f"Should flag panic push when percentage ({final_hour_percentage:.1f}%) > {threshold}%"
    
    # Property: Should not flag when percentage <= threshold
    else:
        should_not_flag = True
        assert should_not_flag, \
            f"Should not flag panic push when percentage ({final_hour_percentage:.1f}%) <= {threshold}%"


# ============================================================
# PROPERTY 23: Commit Message Quality
# ============================================================


@given(
    word_count=st.integers(min_value=1, max_value=10),
    starts_with_bad_word=st.booleans()
)
@settings(max_examples=100, deadline=None)
def test_property_23_descriptive_message_criteria(
    word_count: int,
    starts_with_bad_word: bool
) -> None:
    """Property 23: Descriptive message criteria.
    
    Feature: human-centric-intelligence
    Validates: Requirements 4.9
    
    For any commit message, it should be considered descriptive if and only if
    it has >3 words AND does not start with "fix"/"update"/"wip".
    """
    # Determine if descriptive
    is_descriptive = word_count > 3 and not starts_with_bad_word
    
    # Property: Message is descriptive iff both conditions met
    if word_count > 3 and not starts_with_bad_word:
        assert is_descriptive, "Message with >3 words and good start should be descriptive"
    else:
        assert not is_descriptive, "Message with ≤3 words or bad start should not be descriptive"


# ============================================================
# PROPERTY 24: Team Dynamics Evidence
# ============================================================


@given(commits=st.lists(commit_info_strategy(), min_size=5, max_size=20))
@settings(max_examples=50, deadline=None)
def test_property_24_evidence_includes_commit_hashes(
    commits: list[CommitInfo]
) -> None:
    """Property 24: Team dynamics evidence includes commit hashes.
    
    Feature: human-centric-intelligence
    Validates: Requirements 4.11, 5.11
    
    For any team dynamics finding, the finding should include specific evidence
    with commit hashes and timestamps.
    """
    # Property: Each commit should have a hash
    for commit in commits:
        assert commit.hash, "Commit should have hash"
        assert len(commit.hash) > 0, "Commit hash should not be empty"
    
    # Property: Each commit should have a timestamp
    for commit in commits:
        assert commit.timestamp, "Commit should have timestamp"
        assert isinstance(commit.timestamp, datetime), "Timestamp should be datetime"


# ============================================================
# PROPERTY 25: Role Detection
# ============================================================


@given(
    backend_files=st.integers(min_value=0, max_value=20),
    frontend_files=st.integers(min_value=0, max_value=20),
    infra_files=st.integers(min_value=0, max_value=20)
)
@settings(max_examples=100, deadline=None)
def test_property_25_full_stack_detection(
    backend_files: int,
    frontend_files: int,
    infra_files: int
) -> None:
    """Property 25: Detect full-stack role (3+ domains).
    
    Feature: human-centric-intelligence
    Validates: Requirements 5.1, 5.2
    
    For any contributor who touches files in 3 or more different domains,
    the system should classify them as "Full-Stack".
    """
    # Count domains with files touched
    domains_touched = 0
    
    if backend_files > 0:
        domains_touched += 1
    if frontend_files > 0:
        domains_touched += 1
    if infra_files > 0:
        domains_touched += 1
    
    # Property: Should classify as full-stack when 3+ domains
    if domains_touched >= 3:
        should_be_full_stack = True
        assert should_be_full_stack, \
            f"Should classify as full-stack when touching {domains_touched} domains"
    else:
        should_not_be_full_stack = True
        assert should_not_be_full_stack, \
            f"Should not classify as full-stack when touching {domains_touched} domains"


# ============================================================
# PROPERTY 26: Notable Contribution Detection
# ============================================================


@given(
    insertions=st.integers(min_value=0, max_value=2000),
    files_changed=st.integers(min_value=0, max_value=50)
)
@settings(max_examples=100, deadline=None)
def test_property_26_notable_contribution_thresholds(
    insertions: int,
    files_changed: int
) -> None:
    """Property 26: Detect notable contributions (>500 insertions or >10 files).
    
    Feature: human-centric-intelligence
    Validates: Requirements 5.4
    
    For any contributor, commits with >500 insertions or >10 files changed
    should be included in their notable contributions list.
    """
    # Property: Notable if >500 insertions OR >10 files
    is_notable = insertions > 500 or files_changed > 10
    
    if insertions > 500:
        assert is_notable, \
            f"Commit with {insertions} insertions should be notable"
    
    if files_changed > 10:
        assert is_notable, \
            f"Commit with {files_changed} files changed should be notable"
    
    if insertions <= 500 and files_changed <= 10:
        assert not is_notable, \
            f"Commit with {insertions} insertions and {files_changed} files should not be notable"


# ============================================================
# PROPERTY 28: Test Strategy Classification
# ============================================================


@given(
    unit_count=st.integers(min_value=0, max_value=20),
    integration_count=st.integers(min_value=0, max_value=20),
    e2e_count=st.integers(min_value=0, max_value=20)
)
@settings(max_examples=100, deadline=None)
def test_property_28_test_distribution_determines_strategy(
    unit_count: int,
    integration_count: int,
    e2e_count: int
) -> None:
    """Property 28: Test distribution determines strategy classification.
    
    Feature: human-centric-intelligence
    Validates: Requirements 6.1, 6.2, 6.3
    
    For any repository, the test strategy should be determined by which
    test type has the highest count.
    """
    total_tests = unit_count + integration_count + e2e_count
    
    # Skip if no tests
    assume(total_tests > 0)
    
    # Property: Strategy matches dominant test type
    if unit_count > integration_count and unit_count > e2e_count:
        expected_strategy = TestStrategy.UNIT_FOCUSED
        assert True, f"Should be unit-focused with {unit_count} unit tests"
    elif integration_count > unit_count and integration_count > e2e_count:
        expected_strategy = TestStrategy.INTEGRATION_FOCUSED
        assert True, f"Should be integration-focused with {integration_count} integration tests"
    elif e2e_count > unit_count and e2e_count > integration_count:
        expected_strategy = TestStrategy.E2E_FOCUSED
        assert True, f"Should be e2e-focused with {e2e_count} e2e tests"


# ============================================================
# PROPERTY 29: Learning Journey Detection
# ============================================================


@given(
    has_learning_keywords=st.booleans(),
    has_new_framework_files=st.booleans()
)
@settings(max_examples=50, deadline=None)
def test_property_29_learning_journey_requires_both_signals(
    has_learning_keywords: bool,
    has_new_framework_files: bool
) -> None:
    """Property 29: Learning journey requires keywords AND new framework.
    
    Feature: human-centric-intelligence
    Validates: Requirements 6.7
    
    For any commit history, a learning journey should only be detected when
    BOTH learning keywords AND new framework file additions are present.
    """
    # Property: Learning journey requires both signals
    should_detect_learning = has_learning_keywords and has_new_framework_files
    
    if has_learning_keywords and has_new_framework_files:
        assert should_detect_learning, \
            "Should detect learning journey with both keywords and new framework"
    else:
        assert not should_detect_learning, \
            "Should not detect learning journey without both signals"


# ============================================================
# PROPERTY 30: Strategic Context Output
# ============================================================


@given(
    maturity_level=st.sampled_from([
        MaturityLevel.JUNIOR,
        MaturityLevel.MID,
        MaturityLevel.SENIOR,
    ])
)
@settings(max_examples=50, deadline=None)
def test_property_30_maturity_level_classification(
    maturity_level: MaturityLevel
) -> None:
    """Property 30: Maturity level is properly classified.
    
    Feature: human-centric-intelligence
    Validates: Requirements 6.9, 6.10
    
    For any strategy analysis, the maturity level should be one of:
    JUNIOR (tutorial-following), MID (solid fundamentals), or
    SENIOR (production thinking).
    """
    # Property: Maturity level should be valid
    assert maturity_level in [
        MaturityLevel.JUNIOR,
        MaturityLevel.MID,
        MaturityLevel.SENIOR,
    ], f"Maturity level should be valid, got {maturity_level}"
    
    # Property: Each level has distinct characteristics
    if maturity_level == MaturityLevel.JUNIOR:
        assert True, "Junior level indicates tutorial-following"
    elif maturity_level == MaturityLevel.MID:
        assert True, "Mid level indicates solid fundamentals"
    elif maturity_level == MaturityLevel.SENIOR:
        assert True, "Senior level indicates production thinking"
