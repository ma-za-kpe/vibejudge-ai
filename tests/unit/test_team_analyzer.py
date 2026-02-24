"""Unit tests for TeamAnalyzer component."""

from datetime import UTC, datetime, timedelta

import pytest

from src.analysis.team_analyzer import TeamAnalyzer
from src.models.analysis import CommitInfo, RepoData, SourceFile
from src.models.submission import RepoMeta
from src.models.team_dynamics import (
    CollaborationPattern,
    ContributorRole,
    ExpertiseArea,
    RedFlagSeverity,
)


# ============================================================
# FIXTURES
# ============================================================


@pytest.fixture
def team_analyzer() -> TeamAnalyzer:
    """Create TeamAnalyzer instance."""
    return TeamAnalyzer()


@pytest.fixture
def base_repo_data() -> RepoData:
    """Base repository data with minimal setup."""
    return RepoData(
        repo_url="https://github.com/test/repo",
        repo_owner="test",
        repo_name="repo",
        default_branch="main",
        meta=RepoMeta(
            primary_language="Python",
            languages={"Python": 1000},
            total_files=10,
            total_lines=1000,
            commit_count=10,
            first_commit_at=datetime(2024, 1, 1, tzinfo=UTC),
            last_commit_at=datetime(2024, 1, 10, tzinfo=UTC),
            development_duration_hours=24.0,
            workflow_run_count=0,
            workflow_success_rate=0.0,
        ),
        source_files=[],
        commit_history=[],
    )



def create_commit(
    author: str,
    timestamp: datetime,
    message: str = "Test commit",
    insertions: int = 100,
    deletions: int = 10,
    files_changed: int = 3,
) -> CommitInfo:
    """Helper to create commit info."""
    hash_val = f"{author}_{timestamp.timestamp()}"
    return CommitInfo(
        hash=hash_val,
        short_hash=hash_val[:7],
        author=author,
        timestamp=timestamp,
        message=message,
        files_changed=files_changed,
        insertions=insertions,
        deletions=deletions,
    )


# ============================================================
# TEST: Empty Repository
# ============================================================


def test_analyze_empty_repository(team_analyzer: TeamAnalyzer, base_repo_data: RepoData) -> None:
    """Test analysis of repository with no commits."""
    result = team_analyzer.analyze(base_repo_data)
    
    assert result.workload_distribution == {}
    assert result.collaboration_patterns == []
    assert result.red_flags == []
    assert result.individual_scorecards == []
    assert result.team_dynamics_grade == "F"
    assert result.commit_message_quality == 0.0
    assert result.panic_push_detected is False
    assert result.duration_ms > 0



# ============================================================
# TEST: Workload Distribution
# ============================================================


def test_calculate_workload_distribution_single_contributor(
    team_analyzer: TeamAnalyzer, base_repo_data: RepoData
) -> None:
    """Test workload distribution with single contributor."""
    base_time = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
    base_repo_data.commit_history = [
        create_commit("Alice", base_time + timedelta(hours=i))
        for i in range(10)
    ]
    
    result = team_analyzer.analyze(base_repo_data)
    
    assert result.workload_distribution == {"Alice": 100.0}
    assert len(result.individual_scorecards) == 1
    assert result.individual_scorecards[0].contributor_name == "Alice"


def test_calculate_workload_distribution_balanced_team(
    team_analyzer: TeamAnalyzer, base_repo_data: RepoData
) -> None:
    """Test workload distribution with balanced team."""
    base_time = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
    commits = []
    
    # Alice: 5 commits, Bob: 5 commits
    for i in range(5):
        commits.append(create_commit("Alice", base_time + timedelta(hours=i)))
        commits.append(create_commit("Bob", base_time + timedelta(hours=i, minutes=30)))
    
    base_repo_data.commit_history = commits
    result = team_analyzer.analyze(base_repo_data)
    
    assert result.workload_distribution == {"Alice": 50.0, "Bob": 50.0}
    assert len(result.red_flags) == 0  # No imbalance flags


def test_calculate_workload_distribution_extreme_imbalance(
    team_analyzer: TeamAnalyzer, base_repo_data: RepoData
) -> None:
    """Test workload distribution with extreme imbalance (>80%)."""
    base_time = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
    commits = []
    
    # Alice: 9 commits (90%), Bob: 1 commit (10%)
    for i in range(9):
        commits.append(create_commit("Alice", base_time + timedelta(hours=i)))
    commits.append(create_commit("Bob", base_time + timedelta(hours=10)))
    
    base_repo_data.commit_history = commits
    result = team_analyzer.analyze(base_repo_data)
    
    assert result.workload_distribution["Alice"] == 90.0
    assert result.workload_distribution["Bob"] == 10.0
    
    # Should have extreme imbalance red flag
    extreme_flags = [f for f in result.red_flags if f.flag_type == "extreme_imbalance"]
    assert len(extreme_flags) == 1
    assert extreme_flags[0].severity == RedFlagSeverity.CRITICAL



# ============================================================
# TEST: Red Flag Detection
# ============================================================


def test_detect_ghost_contributor(
    team_analyzer: TeamAnalyzer, base_repo_data: RepoData
) -> None:
    """Test detection of ghost contributor (0 commits)."""
    base_time = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
    base_repo_data.commit_history = [
        create_commit("Alice", base_time + timedelta(hours=i))
        for i in range(5)
    ]
    
    result = team_analyzer.analyze(base_repo_data)
    
    # No ghost contributors since we only have Alice
    ghost_flags = [f for f in result.red_flags if f.flag_type == "ghost_contributor"]
    assert len(ghost_flags) == 0


def test_detect_minimal_contribution(
    team_analyzer: TeamAnalyzer, base_repo_data: RepoData
) -> None:
    """Test detection of minimal contribution (≤2 commits in team of 3+)."""
    base_time = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
    commits = []
    
    # Alice: 10 commits, Bob: 8 commits, Charlie: 2 commits (minimal)
    for i in range(10):
        commits.append(create_commit("Alice", base_time + timedelta(hours=i)))
    for i in range(8):
        commits.append(create_commit("Bob", base_time + timedelta(hours=i, minutes=15)))
    for i in range(2):
        commits.append(create_commit("Charlie", base_time + timedelta(hours=i, minutes=30)))
    
    base_repo_data.commit_history = commits
    result = team_analyzer.analyze(base_repo_data)
    
    # Should have minimal contribution flag for Charlie
    minimal_flags = [f for f in result.red_flags if f.flag_type == "minimal_contribution"]
    assert len(minimal_flags) == 1
    assert "Charlie" in minimal_flags[0].description
    assert minimal_flags[0].severity == RedFlagSeverity.HIGH


def test_detect_unhealthy_work_patterns(
    team_analyzer: TeamAnalyzer, base_repo_data: RepoData
) -> None:
    """Test detection of unhealthy work patterns (>10 late-night commits)."""
    base_time = datetime(2024, 1, 1, 3, 0, tzinfo=UTC)  # 3 AM
    commits = []
    
    # Alice: 15 commits between 2am-6am
    for i in range(15):
        commits.append(create_commit("Alice", base_time + timedelta(hours=i * 0.2)))
    
    base_repo_data.commit_history = commits
    result = team_analyzer.analyze(base_repo_data)
    
    # Should have unhealthy work pattern flag
    unhealthy_flags = [f for f in result.red_flags if f.flag_type == "unhealthy_work_patterns"]
    assert len(unhealthy_flags) == 1
    assert unhealthy_flags[0].severity == RedFlagSeverity.MEDIUM
    assert "Alice" in unhealthy_flags[0].description



# ============================================================
# TEST: Collaboration Patterns
# ============================================================


def test_detect_pair_programming_pattern(
    team_analyzer: TeamAnalyzer, base_repo_data: RepoData
) -> None:
    """Test detection of pair programming (alternating commits)."""
    base_time = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
    commits = []
    
    # Alternating pattern: Alice, Bob, Alice, Bob
    for i in range(4):
        author = "Alice" if i % 2 == 0 else "Bob"
        commits.append(create_commit(author, base_time + timedelta(hours=i)))
    
    base_repo_data.commit_history = commits
    result = team_analyzer.analyze(base_repo_data)
    
    # Should detect pair programming pattern
    pair_patterns = [p for p in result.collaboration_patterns if p.pattern_type == "pair_programming"]
    assert len(pair_patterns) >= 1
    assert pair_patterns[0].positive is True
    assert set(pair_patterns[0].contributors) == {"Alice", "Bob"}


def test_detect_code_review_pattern(
    team_analyzer: TeamAnalyzer, base_repo_data: RepoData
) -> None:
    """Test detection of code review patterns from commit messages."""
    base_time = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
    commits = [
        create_commit("Alice", base_time, "Add feature reviewed by Bob"),
        create_commit("Alice", base_time + timedelta(hours=1), "Fix bug reviewed by Bob"),
        create_commit("Bob", base_time + timedelta(hours=2), "Update docs reviewed by Alice"),
    ]
    
    base_repo_data.commit_history = commits
    result = team_analyzer.analyze(base_repo_data)
    
    # Should detect code review pattern
    review_patterns = [p for p in result.collaboration_patterns if p.pattern_type == "code_review"]
    assert len(review_patterns) >= 1
    assert review_patterns[0].positive is True


def test_detect_merge_commits_pattern(
    team_analyzer: TeamAnalyzer, base_repo_data: RepoData
) -> None:
    """Test detection of PR-based workflow from merge commits."""
    base_time = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
    commits = []
    
    # Regular commits + merge commits
    for i in range(5):
        commits.append(create_commit("Alice", base_time + timedelta(hours=i), f"Merge pull request #{i}"))
    
    base_repo_data.commit_history = commits
    result = team_analyzer.analyze(base_repo_data)
    
    # Should detect code review pattern from merge commits
    review_patterns = [p for p in result.collaboration_patterns if p.pattern_type == "code_review"]
    assert len(review_patterns) >= 1



# ============================================================
# TEST: Commit Timing Analysis
# ============================================================


def test_analyze_commit_timing_late_night(
    team_analyzer: TeamAnalyzer, base_repo_data: RepoData
) -> None:
    """Test detection of late-night commits (2am-6am)."""
    commits = []
    
    # 5 commits at 3 AM
    for i in range(5):
        commits.append(create_commit("Alice", datetime(2024, 1, 1, 3, i * 10, tzinfo=UTC)))
    
    base_repo_data.commit_history = commits
    result = team_analyzer.analyze(base_repo_data)
    
    # Should not trigger unhealthy pattern flag (need >10)
    unhealthy_flags = [f for f in result.red_flags if f.flag_type == "unhealthy_work_patterns"]
    assert len(unhealthy_flags) == 0


def test_analyze_commit_timing_panic_push(
    team_analyzer: TeamAnalyzer, base_repo_data: RepoData
) -> None:
    """Test detection of panic push (>40% commits in final hour)."""
    base_time = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
    commits = []
    
    # 10 total commits: 3 early, 7 in final hour (70%)
    for i in range(3):
        commits.append(create_commit("Alice", base_time + timedelta(hours=i)))
    
    final_hour_start = base_time + timedelta(hours=9)
    for i in range(7):
        commits.append(create_commit("Alice", final_hour_start + timedelta(minutes=i * 5)))
    
    base_repo_data.commit_history = commits
    result = team_analyzer.analyze(base_repo_data)
    
    # Should detect panic push
    assert result.panic_push_detected is True


def test_analyze_commit_timing_normal_pattern(
    team_analyzer: TeamAnalyzer, base_repo_data: RepoData
) -> None:
    """Test normal commit timing pattern."""
    base_time = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
    commits = []
    
    # Evenly distributed commits during normal hours
    for i in range(10):
        commits.append(create_commit("Alice", base_time + timedelta(hours=i)))
    
    base_repo_data.commit_history = commits
    result = team_analyzer.analyze(base_repo_data)
    
    # Should not detect panic push
    assert result.panic_push_detected is False



# ============================================================
# TEST: Individual Scorecards
# ============================================================


def test_generate_individual_scorecard_basic(
    team_analyzer: TeamAnalyzer, base_repo_data: RepoData
) -> None:
    """Test generation of basic individual scorecard."""
    base_time = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
    base_repo_data.commit_history = [
        create_commit("Alice", base_time + timedelta(hours=i), insertions=100, deletions=10)
        for i in range(10)
    ]
    base_repo_data.source_files = [
        SourceFile(path="src/main.py", content="", lines=100, language="Python"),
    ]
    
    result = team_analyzer.analyze(base_repo_data)
    
    assert len(result.individual_scorecards) == 1
    scorecard = result.individual_scorecards[0]
    
    assert scorecard.contributor_name == "Alice"
    assert scorecard.commit_count == 10
    assert scorecard.lines_added == 1000  # 10 commits * 100 insertions
    assert scorecard.lines_deleted == 100  # 10 commits * 10 deletions
    assert scorecard.role in ContributorRole
    assert isinstance(scorecard.expertise_areas, list)
    assert isinstance(scorecard.strengths, list)
    assert isinstance(scorecard.weaknesses, list)


def test_detect_role_backend(
    team_analyzer: TeamAnalyzer, base_repo_data: RepoData
) -> None:
    """Test detection of backend role from file patterns."""
    base_time = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
    base_repo_data.commit_history = [
        create_commit("Alice", base_time)
    ]
    base_repo_data.source_files = [
        SourceFile(path="src/api.py", content="", lines=100, language="Python"),
        SourceFile(path="src/database.py", content="", lines=100, language="Python"),
        SourceFile(path="src/models.py", content="", lines=100, language="Python"),
    ]
    
    result = team_analyzer.analyze(base_repo_data)
    
    scorecard = result.individual_scorecards[0]
    assert scorecard.role == ContributorRole.BACKEND


def test_detect_role_frontend(
    team_analyzer: TeamAnalyzer, base_repo_data: RepoData
) -> None:
    """Test detection of frontend role from file patterns."""
    base_time = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
    base_repo_data.commit_history = [
        create_commit("Alice", base_time)
    ]
    base_repo_data.source_files = [
        SourceFile(path="src/App.tsx", content="", lines=100, language="TypeScript"),
        SourceFile(path="src/components/Button.tsx", content="", lines=50, language="TypeScript"),
        SourceFile(path="src/styles.css", content="", lines=50, language="CSS"),
    ]
    
    result = team_analyzer.analyze(base_repo_data)
    
    scorecard = result.individual_scorecards[0]
    assert scorecard.role == ContributorRole.FRONTEND



# ============================================================
# TEST: Expertise Detection
# ============================================================


def test_detect_expertise_database(
    team_analyzer: TeamAnalyzer, base_repo_data: RepoData
) -> None:
    """Test detection of database expertise."""
    base_time = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
    base_repo_data.commit_history = [
        create_commit("Alice", base_time, "Add database migration")
    ]
    base_repo_data.source_files = [
        SourceFile(path="migrations/001_schema.sql", content="", lines=100, language="SQL"),
        SourceFile(path="src/database.py", content="", lines=100, language="Python"),
    ]
    
    result = team_analyzer.analyze(base_repo_data)
    
    scorecard = result.individual_scorecards[0]
    assert ExpertiseArea.DATABASE in scorecard.expertise_areas


def test_detect_expertise_security(
    team_analyzer: TeamAnalyzer, base_repo_data: RepoData
) -> None:
    """Test detection of security expertise."""
    base_time = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
    base_repo_data.commit_history = [
        create_commit("Alice", base_time, "Fix security vulnerability in auth")
    ]
    base_repo_data.source_files = [
        SourceFile(path="src/auth.py", content="", lines=100, language="Python"),
        SourceFile(path="src/security.py", content="", lines=100, language="Python"),
    ]
    
    result = team_analyzer.analyze(base_repo_data)
    
    scorecard = result.individual_scorecards[0]
    assert ExpertiseArea.SECURITY in scorecard.expertise_areas


def test_detect_expertise_testing(
    team_analyzer: TeamAnalyzer, base_repo_data: RepoData
) -> None:
    """Test detection of testing expertise."""
    base_time = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
    base_repo_data.commit_history = [
        create_commit("Alice", base_time, "Add unit tests for API")
    ]
    base_repo_data.source_files = [
        SourceFile(path="tests/test_api.py", content="", lines=100, language="Python"),
        SourceFile(path="tests/test_models.py", content="", lines=100, language="Python"),
    ]
    
    result = team_analyzer.analyze(base_repo_data)
    
    scorecard = result.individual_scorecards[0]
    assert ExpertiseArea.TESTING in scorecard.expertise_areas



# ============================================================
# TEST: Commit Message Quality
# ============================================================


def test_calculate_commit_message_quality_high(
    team_analyzer: TeamAnalyzer, base_repo_data: RepoData
) -> None:
    """Test calculation of high commit message quality."""
    base_time = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
    base_repo_data.commit_history = [
        create_commit("Alice", base_time, "Implement user authentication with JWT tokens"),
        create_commit("Alice", base_time + timedelta(hours=1), "Add comprehensive test coverage for API endpoints"),
        create_commit("Alice", base_time + timedelta(hours=2), "Refactor database connection pooling for better performance"),
    ]
    
    result = team_analyzer.analyze(base_repo_data)
    
    # All messages are descriptive (>3 words, not starting with fix/update/wip)
    assert result.commit_message_quality == 1.0


def test_calculate_commit_message_quality_low(
    team_analyzer: TeamAnalyzer, base_repo_data: RepoData
) -> None:
    """Test calculation of low commit message quality."""
    base_time = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
    base_repo_data.commit_history = [
        create_commit("Alice", base_time, "fix"),
        create_commit("Alice", base_time + timedelta(hours=1), "update"),
        create_commit("Alice", base_time + timedelta(hours=2), "wip"),
    ]
    
    result = team_analyzer.analyze(base_repo_data)
    
    # No messages are descriptive
    assert result.commit_message_quality == 0.0


def test_calculate_commit_message_quality_mixed(
    team_analyzer: TeamAnalyzer, base_repo_data: RepoData
) -> None:
    """Test calculation of mixed commit message quality."""
    base_time = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
    base_repo_data.commit_history = [
        create_commit("Alice", base_time, "Implement user authentication system"),
        create_commit("Alice", base_time + timedelta(hours=1), "fix bug"),
        create_commit("Alice", base_time + timedelta(hours=2), "Add database migration for users table"),
        create_commit("Alice", base_time + timedelta(hours=3), "update"),
    ]
    
    result = team_analyzer.analyze(base_repo_data)
    
    # 2 out of 4 messages are descriptive
    assert result.commit_message_quality == 0.5



# ============================================================
# TEST: Team Grade Calculation
# ============================================================


def test_calculate_team_grade_excellent(
    team_analyzer: TeamAnalyzer, base_repo_data: RepoData
) -> None:
    """Test calculation of excellent team grade (A)."""
    base_time = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
    commits = []
    
    # Balanced team: Alice 50%, Bob 50%
    for i in range(5):
        commits.append(create_commit("Alice", base_time + timedelta(hours=i), 
                                    "Implement comprehensive user authentication system"))
        commits.append(create_commit("Bob", base_time + timedelta(hours=i, minutes=30),
                                    "Add detailed API documentation and examples"))
    
    base_repo_data.commit_history = commits
    result = team_analyzer.analyze(base_repo_data)
    
    # Should get A grade: balanced workload, good messages, no red flags
    assert result.team_dynamics_grade in ["A", "B"]


def test_calculate_team_grade_poor(
    team_analyzer: TeamAnalyzer, base_repo_data: RepoData
) -> None:
    """Test calculation of poor team grade (F)."""
    base_time = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
    commits = []
    
    # Extreme imbalance: Alice 95%, Bob 5%
    for i in range(19):
        commits.append(create_commit("Alice", base_time + timedelta(hours=i), "fix"))
    commits.append(create_commit("Bob", base_time + timedelta(hours=20), "update"))
    
    base_repo_data.commit_history = commits
    result = team_analyzer.analyze(base_repo_data)
    
    # Should get low grade: extreme imbalance, poor messages
    assert result.team_dynamics_grade in ["D", "F"]


# ============================================================
# TEST: Work Style Analysis
# ============================================================


def test_analyze_work_style_frequent_commits(
    team_analyzer: TeamAnalyzer, base_repo_data: RepoData
) -> None:
    """Test work style analysis with frequent commits."""
    base_time = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
    base_repo_data.commit_history = [
        create_commit("Alice", base_time + timedelta(hours=i))
        for i in range(25)
    ]
    
    result = team_analyzer.analyze(base_repo_data)
    
    scorecard = result.individual_scorecards[0]
    assert scorecard.work_style.commit_frequency == "frequent"


def test_analyze_work_style_infrequent_commits(
    team_analyzer: TeamAnalyzer, base_repo_data: RepoData
) -> None:
    """Test work style analysis with infrequent commits."""
    base_time = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
    base_repo_data.commit_history = [
        create_commit("Alice", base_time + timedelta(hours=i))
        for i in range(3)
    ]
    
    result = team_analyzer.analyze(base_repo_data)
    
    scorecard = result.individual_scorecards[0]
    assert scorecard.work_style.commit_frequency == "infrequent"


# ============================================================
# TEST: Hiring Signals
# ============================================================


def test_generate_hiring_signals_senior(
    team_analyzer: TeamAnalyzer, base_repo_data: RepoData
) -> None:
    """Test generation of senior-level hiring signals."""
    base_time = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
    base_repo_data.commit_history = [
        create_commit("Alice", base_time + timedelta(hours=i), 
                     "Implement comprehensive feature with tests", 
                     insertions=200, deletions=20)
        for i in range(35)
    ]
    base_repo_data.source_files = [
        SourceFile(path="src/main.py", content="", lines=100, language="Python"),
    ]
    
    result = team_analyzer.analyze(base_repo_data)
    
    scorecard = result.individual_scorecards[0]
    assert scorecard.hiring_signals.seniority_level == "senior"
    assert scorecard.hiring_signals.must_interview is True


def test_generate_hiring_signals_junior(
    team_analyzer: TeamAnalyzer, base_repo_data: RepoData
) -> None:
    """Test generation of junior-level hiring signals."""
    base_time = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
    base_repo_data.commit_history = [
        create_commit("Alice", base_time + timedelta(hours=i), "fix", 
                     insertions=50, deletions=5)
        for i in range(5)
    ]
    base_repo_data.source_files = [
        SourceFile(path="src/main.py", content="", lines=100, language="Python"),
    ]
    
    result = team_analyzer.analyze(base_repo_data)
    
    scorecard = result.individual_scorecards[0]
    assert scorecard.hiring_signals.seniority_level == "junior"
