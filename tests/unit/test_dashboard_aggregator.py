"""Unit tests for DashboardAggregator component."""

from datetime import UTC, datetime

import pytest

from src.analysis.dashboard_aggregator import DashboardAggregator
from src.models.common import SubmissionStatus
from src.models.dashboard import (
    HiringIntelligence,
    OrganizerDashboard,
    PrizeRecommendation,
    TechnologyTrends,
    TopPerformer,
)
from src.models.strategy import (
    LearningJourney,
    MaturityLevel,
    StrategyAnalysisResult,
    TestStrategy,
    Tradeoff,
)
from src.models.submission import RepoMeta, SubmissionResponse
from src.models.team_dynamics import (
    CollaborationPattern,
    ContributorRole,
    ExpertiseArea,
    HiringSignals,
    IndividualScorecard,
    TeamAnalysisResult,
    WorkStyle,
)

# ============================================================
# FIXTURES
# ============================================================


@pytest.fixture
def dashboard_aggregator() -> DashboardAggregator:
    """Create DashboardAggregator instance."""
    return DashboardAggregator()


@pytest.fixture
def sample_submission() -> SubmissionResponse:
    """Create sample submission response."""
    return SubmissionResponse(
        sub_id="SUB#001",
        hack_id="HACK#001",
        team_name="Team Alpha",
        repo_url="https://github.com/test/repo",
        status=SubmissionStatus.COMPLETED,
        overall_score=85.0,
        rank=1,
        repo_meta=RepoMeta(
            primary_language="Python",
            languages={"Python": 80.0, "JavaScript": 20.0},
            total_files=50,
            total_lines=5000,
            commit_count=100,
            has_ci=True,
            has_dockerfile=True,
            workflow_run_count=10,
            workflow_success_rate=0.95,
        ),
        strengths=["Excellent test coverage", "Clean architecture", "Good documentation"],
        weaknesses=["Minor security issues", "Performance could be improved"],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
    )


@pytest.fixture
def sample_individual_scorecard() -> IndividualScorecard:
    """Create sample individual scorecard."""
    return IndividualScorecard(
        contributor_name="Alice",
        contributor_email="alice@example.com",
        role=ContributorRole.BACKEND,
        expertise_areas=[ExpertiseArea.API, ExpertiseArea.DATABASE],
        commit_count=50,
        lines_added=2000,
        lines_deleted=500,
        files_touched=["src/api.py", "src/database.py"],
        notable_contributions=["Implemented authentication system"],
        strengths=["Strong backend skills", "Good code quality"],
        weaknesses=["Limited frontend experience"],
        growth_areas=["Learn React", "Improve testing"],
        work_style=WorkStyle(
            commit_frequency="frequent",
            avg_commit_size=100,
            active_hours=[9, 10, 11, 14, 15, 16],
            late_night_commits=2,
            weekend_commits=5,
        ),
        hiring_signals=HiringSignals(
            recommended_role="Backend Engineer",
            seniority_level="mid",
            salary_range_usd="$80k-$100k",
            must_interview=True,
            sponsor_interest=["TechCorp", "StartupXYZ"],
            rationale="Strong backend skills with production experience",
        ),
    )


@pytest.fixture
def sample_team_analysis() -> TeamAnalysisResult:
    """Create sample team analysis result."""
    return TeamAnalysisResult(
        workload_distribution={"Alice": 60.0, "Bob": 40.0},
        collaboration_patterns=[
            CollaborationPattern(
                pattern_type="pair_programming",
                contributors=["Alice", "Bob"],
                evidence="Alternating commits detected",
                positive=True,
            )
        ],
        red_flags=[],
        individual_scorecards=[],
        team_dynamics_grade="A",
        commit_message_quality=0.9,
        panic_push_detected=False,
        duration_ms=1000,
    )


@pytest.fixture
def sample_strategy_analysis() -> StrategyAnalysisResult:
    """Create sample strategy analysis result."""
    return StrategyAnalysisResult(
        test_strategy=TestStrategy.UNIT_FOCUSED,
        critical_path_focus=True,
        tradeoffs=[
            Tradeoff(
                tradeoff_type="speed_vs_security",
                decision="Prioritized speed for demo",
                rationale="Hackathon time constraints",
                impact_on_score="Minor deduction in security score",
            )
        ],
        learning_journey=LearningJourney(
            technology="React",
            evidence=["First React commit", "Learning hooks"],
            progression="Beginner to intermediate",
            impressive=True,
        ),
        maturity_level=MaturityLevel.MID,
        strategic_context="Team showed good prioritization",
        duration_ms=500,
    )


# ============================================================
# TEST: Empty Dashboard
# ============================================================


def test_generate_dashboard_empty_submissions(
    dashboard_aggregator: DashboardAggregator,
) -> None:
    """Test dashboard generation with no submissions."""
    dashboard = dashboard_aggregator.generate_dashboard(
        hack_id="HACK#001",
        hackathon_name="Test Hackathon",
        submissions=[],
        team_analyses={},
        strategy_analyses={},
    )

    assert isinstance(dashboard, OrganizerDashboard)
    assert dashboard.hack_id == "HACK#001"
    assert dashboard.hackathon_name == "Test Hackathon"
    assert dashboard.total_submissions == 0
    assert dashboard.top_performers == []
    assert len(dashboard.hiring_intelligence.must_interview) == 0


# ============================================================
# TEST: Top Performers Aggregation
# ============================================================


def test_aggregate_top_performers_single_submission(
    dashboard_aggregator: DashboardAggregator,
    sample_submission: SubmissionResponse,
) -> None:
    """Test top performers aggregation with single submission."""
    result = dashboard_aggregator._aggregate_top_performers([sample_submission])

    assert len(result) == 1
    assert isinstance(result[0], TopPerformer)
    assert result[0].team_name == "Team Alpha"
    assert result[0].sub_id == "SUB#001"
    assert result[0].overall_score == 85.0
    assert len(result[0].key_strengths) <= 3
    assert "ci_cd_sophistication" in result[0].sponsor_interest_flags
    assert "containerization" in result[0].sponsor_interest_flags


def test_aggregate_top_performers_multiple_submissions(
    dashboard_aggregator: DashboardAggregator,
) -> None:
    """Test top performers aggregation with multiple submissions."""
    submissions = [
        SubmissionResponse(
            sub_id=f"SUB#{i:03d}",
            hack_id="HACK#001",
            team_name=f"Team {i}",
            repo_url=f"https://github.com/test/repo{i}",
            status=SubmissionStatus.COMPLETED,
            overall_score=float(100 - i * 5),
            rank=i,
            strengths=[f"Strength {i}"],
            weaknesses=[],
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        )
        for i in range(15)
    ]

    result = dashboard_aggregator._aggregate_top_performers(submissions)

    # Should return top 10
    assert len(result) == 10
    # Should be sorted by score descending
    assert result[0].overall_score == 100.0
    assert result[9].overall_score == 55.0


def test_aggregate_top_performers_with_sponsor_flags(
    dashboard_aggregator: DashboardAggregator,
) -> None:
    """Test sponsor interest flag detection."""
    submission = SubmissionResponse(
        sub_id="SUB#001",
        hack_id="HACK#001",
        team_name="Team Alpha",
        repo_url="https://github.com/test/repo",
        status=SubmissionStatus.COMPLETED,
        overall_score=90.0,
        repo_meta=RepoMeta(
            primary_language="Python",
            has_ci=True,
            has_dockerfile=True,
            workflow_success_rate=0.95,
        ),
        strengths=[],
        weaknesses=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
    )

    result = dashboard_aggregator._aggregate_top_performers([submission])

    assert "ci_cd_sophistication" in result[0].sponsor_interest_flags
    assert "containerization" in result[0].sponsor_interest_flags
    assert "high_quality_automation" in result[0].sponsor_interest_flags


# ============================================================
# TEST: Hiring Intelligence
# ============================================================


def test_generate_hiring_intelligence_empty(
    dashboard_aggregator: DashboardAggregator,
) -> None:
    """Test hiring intelligence with no scorecards."""
    result = dashboard_aggregator._generate_hiring_intelligence([])

    assert isinstance(result, HiringIntelligence)
    assert len(result.backend_candidates) == 0
    assert len(result.frontend_candidates) == 0
    assert len(result.devops_candidates) == 0
    assert len(result.full_stack_candidates) == 0
    assert len(result.must_interview) == 0


def test_generate_hiring_intelligence_by_role(
    dashboard_aggregator: DashboardAggregator,
    sample_individual_scorecard: IndividualScorecard,
) -> None:
    """Test hiring intelligence categorization by role."""
    scorecards = [
        sample_individual_scorecard,
        IndividualScorecard(
            contributor_name="Bob",
            contributor_email="bob@example.com",
            role=ContributorRole.FRONTEND,
            expertise_areas=[ExpertiseArea.UI_UX],
            commit_count=30,
            lines_added=1000,
            lines_deleted=200,
            files_touched=["src/App.tsx"],
            notable_contributions=[],
            strengths=["React expert"],
            weaknesses=[],
            growth_areas=[],
            work_style=WorkStyle(
                commit_frequency="moderate",
                avg_commit_size=50,
                active_hours=[10, 11, 12],
                late_night_commits=0,
                weekend_commits=0,
            ),
            hiring_signals=HiringSignals(
                recommended_role="Frontend Engineer",
                seniority_level="junior",
                salary_range_usd="$60k-$80k",
                must_interview=False,
                sponsor_interest=[],
                rationale="Good frontend skills",
            ),
        ),
    ]

    result = dashboard_aggregator._generate_hiring_intelligence(scorecards)

    assert len(result.backend_candidates) == 1
    assert result.backend_candidates[0].contributor_name == "Alice"
    assert len(result.frontend_candidates) == 1
    assert result.frontend_candidates[0].contributor_name == "Bob"


def test_generate_hiring_intelligence_must_interview(
    dashboard_aggregator: DashboardAggregator,
    sample_individual_scorecard: IndividualScorecard,
) -> None:
    """Test must-interview flag filtering."""
    result = dashboard_aggregator._generate_hiring_intelligence([sample_individual_scorecard])

    assert len(result.must_interview) == 1
    assert result.must_interview[0].contributor_name == "Alice"


def test_generate_hiring_intelligence_seniority_sorting(
    dashboard_aggregator: DashboardAggregator,
) -> None:
    """Test candidates are sorted by seniority (senior first)."""
    scorecards = []
    for i, level in enumerate(["junior", "senior", "mid"]):
        scorecards.append(
            IndividualScorecard(
                contributor_name=f"Dev{i}",
                contributor_email=f"dev{i}@example.com",
                role=ContributorRole.BACKEND,
                expertise_areas=[],
                commit_count=10,
                lines_added=100,
                lines_deleted=10,
                files_touched=[],
                notable_contributions=[],
                strengths=[],
                weaknesses=[],
                growth_areas=[],
                work_style=WorkStyle(
                    commit_frequency="moderate",
                    avg_commit_size=50,
                    active_hours=[],
                    late_night_commits=0,
                    weekend_commits=0,
                ),
                hiring_signals=HiringSignals(
                    recommended_role="Backend Engineer",
                    seniority_level=level,
                    salary_range_usd="$80k-$100k",
                    must_interview=False,
                    sponsor_interest=[],
                    rationale="Test",
                ),
            )
        )

    result = dashboard_aggregator._generate_hiring_intelligence(scorecards)

    assert result.backend_candidates[0].hiring_signals.seniority_level == "senior"
    assert result.backend_candidates[1].hiring_signals.seniority_level == "mid"
    assert result.backend_candidates[2].hiring_signals.seniority_level == "junior"


# ============================================================
# TEST: Technology Trends
# ============================================================


def test_analyze_technology_trends_empty(
    dashboard_aggregator: DashboardAggregator,
) -> None:
    """Test technology trends with no submissions."""
    result = dashboard_aggregator._analyze_technology_trends([])

    assert isinstance(result, TechnologyTrends)
    assert len(result.most_used) == 0
    assert len(result.emerging) == 0
    assert len(result.popular_stacks) == 0


def test_analyze_technology_trends_languages(
    dashboard_aggregator: DashboardAggregator,
) -> None:
    """Test technology trends language detection."""
    submissions = [
        SubmissionResponse(
            sub_id=f"SUB#{i:03d}",
            hack_id="HACK#001",
            team_name=f"Team {i}",
            repo_url=f"https://github.com/test/repo{i}",
            status=SubmissionStatus.COMPLETED,
            overall_score=80.0,
            repo_meta=RepoMeta(
                primary_language="Python" if i < 5 else "JavaScript",
                languages={"Python": 100.0} if i < 5 else {"JavaScript": 100.0},
            ),
            strengths=[],
            weaknesses=[],
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        )
        for i in range(10)
    ]

    result = dashboard_aggregator._analyze_technology_trends(submissions)

    assert len(result.most_used) > 0
    assert ("Python", 5) in result.most_used
    assert ("JavaScript", 5) in result.most_used


# ============================================================
# TEST: Common Issues
# ============================================================


def test_identify_common_issues_empty(
    dashboard_aggregator: DashboardAggregator,
) -> None:
    """Test common issues identification with no submissions."""
    result = dashboard_aggregator._identify_common_issues([], {})

    assert isinstance(result, list)
    assert len(result) == 0


def test_identify_common_issues_from_weaknesses(
    dashboard_aggregator: DashboardAggregator,
) -> None:
    """Test common issues identification from submission weaknesses."""
    submissions = [
        SubmissionResponse(
            sub_id=f"SUB#{i:03d}",
            hack_id="HACK#001",
            team_name=f"Team {i}",
            repo_url=f"https://github.com/test/repo{i}",
            status=SubmissionStatus.COMPLETED,
            overall_score=80.0,
            strengths=[],
            weaknesses=["Insufficient test coverage", "Poor documentation"],
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        )
        for i in range(5)
    ]

    result = dashboard_aggregator._identify_common_issues(submissions, {})

    assert len(result) > 0
    issue_types = [issue.issue_type for issue in result]
    assert "insufficient_testing" in issue_types
    assert "poor_documentation" in issue_types


def test_identify_common_issues_threshold(
    dashboard_aggregator: DashboardAggregator,
) -> None:
    """Test common issues includes issues affecting >=20% of teams."""
    submissions = []
    for i in range(10):
        weaknesses = ["Security vulnerability"] if i < 2 else []
        submissions.append(
            SubmissionResponse(
                sub_id=f"SUB#{i:03d}",
                hack_id="HACK#001",
                team_name=f"Team {i}",
                repo_url=f"https://github.com/test/repo{i}",
                status=SubmissionStatus.COMPLETED,
                overall_score=80.0,
                strengths=[],
                weaknesses=weaknesses,
                created_at=datetime(2024, 1, 1, tzinfo=UTC),
                updated_at=datetime(2024, 1, 2, tzinfo=UTC),
            )
        )

    result = dashboard_aggregator._identify_common_issues(submissions, {})

    # 2/10 = 20%, should be included (threshold is >=20%)
    issue_types = [issue.issue_type for issue in result]
    assert "security_vulnerabilities" in issue_types
    assert result[0].percentage_affected == 20.0


# ============================================================
# TEST: Prize Recommendations
# ============================================================


def test_generate_prize_recommendations_empty(
    dashboard_aggregator: DashboardAggregator,
) -> None:
    """Test prize recommendations with no submissions."""
    result = dashboard_aggregator._generate_prize_recommendations([], {}, {})

    assert isinstance(result, list)
    assert len(result) == 0


def test_find_best_team_dynamics(
    dashboard_aggregator: DashboardAggregator,
    sample_submission: SubmissionResponse,
    sample_team_analysis: TeamAnalysisResult,
) -> None:
    """Test finding team with best dynamics."""
    team_analyses = {"SUB#001": sample_team_analysis}

    result = dashboard_aggregator._find_best_team_dynamics([sample_submission], team_analyses)

    assert result is not None
    assert isinstance(result, PrizeRecommendation)
    assert result.prize_category == "Best Team Dynamics"
    assert result.recommended_team == "Team Alpha"
    assert result.sub_id == "SUB#001"


def test_find_best_learning_journey(
    dashboard_aggregator: DashboardAggregator,
    sample_submission: SubmissionResponse,
    sample_strategy_analysis: StrategyAnalysisResult,
) -> None:
    """Test finding team with best learning journey."""
    strategy_analyses = {"SUB#001": sample_strategy_analysis}

    result = dashboard_aggregator._find_best_learning_journey(
        [sample_submission], strategy_analyses
    )

    assert result is not None
    assert isinstance(result, PrizeRecommendation)
    assert result.prize_category == "Most Improved / Best Learning Journey"
    assert result.recommended_team == "Team Alpha"
    assert "React" in result.justification


def test_find_best_cicd(
    dashboard_aggregator: DashboardAggregator,
    sample_submission: SubmissionResponse,
) -> None:
    """Test finding team with best CI/CD practices."""
    result = dashboard_aggregator._find_best_cicd([sample_submission])

    assert result is not None
    assert isinstance(result, PrizeRecommendation)
    assert result.prize_category == "Best CI/CD Practices"
    assert result.recommended_team == "Team Alpha"


# ============================================================
# TEST: Helper Methods
# ============================================================


def test_categorize_weakness(
    dashboard_aggregator: DashboardAggregator,
) -> None:
    """Test weakness categorization."""
    assert (
        dashboard_aggregator._categorize_weakness("Insufficient test coverage")
        == "insufficient_testing"
    )
    assert (
        dashboard_aggregator._categorize_weakness("SQL injection vulnerability")
        == "security_vulnerabilities"
    )
    assert dashboard_aggregator._categorize_weakness("Missing README") == "poor_documentation"
    assert dashboard_aggregator._categorize_weakness("No error handling") == "weak_error_handling"
    assert dashboard_aggregator._categorize_weakness("Slow performance") == "performance_issues"
    assert dashboard_aggregator._categorize_weakness("Code smells") == "general_code_quality"


def test_recommend_workshop(
    dashboard_aggregator: DashboardAggregator,
) -> None:
    """Test workshop recommendation based on issue type."""
    result = dashboard_aggregator._recommend_workshop("insufficient_testing")
    assert "Test-Driven Development" in result

    result = dashboard_aggregator._recommend_workshop("security_vulnerabilities")
    assert "Secure Coding" in result

    result = dashboard_aggregator._recommend_workshop("unknown_issue")
    assert "Software Engineering Best Practices" in result


# ============================================================
# TEST: Full Dashboard Generation
# ============================================================


def test_generate_dashboard_complete(
    dashboard_aggregator: DashboardAggregator,
    sample_submission: SubmissionResponse,
    sample_individual_scorecard: IndividualScorecard,
    sample_team_analysis: TeamAnalysisResult,
    sample_strategy_analysis: StrategyAnalysisResult,
) -> None:
    """Test complete dashboard generation with all components."""
    sample_team_analysis.individual_scorecards = [sample_individual_scorecard]
    team_analyses = {"SUB#001": sample_team_analysis}
    strategy_analyses = {"SUB#001": sample_strategy_analysis}

    dashboard = dashboard_aggregator.generate_dashboard(
        hack_id="HACK#001",
        hackathon_name="Test Hackathon",
        submissions=[sample_submission],
        team_analyses=team_analyses,
        strategy_analyses=strategy_analyses,
    )

    assert isinstance(dashboard, OrganizerDashboard)
    assert dashboard.hack_id == "HACK#001"
    assert dashboard.hackathon_name == "Test Hackathon"
    assert dashboard.total_submissions == 1
    assert len(dashboard.top_performers) == 1
    assert len(dashboard.hiring_intelligence.must_interview) == 1
    assert len(dashboard.prize_recommendations) > 0
    assert len(dashboard.standout_moments) > 0
    assert len(dashboard.next_hackathon_recommendations) > 0
    assert len(dashboard.sponsor_follow_up_actions) > 0
