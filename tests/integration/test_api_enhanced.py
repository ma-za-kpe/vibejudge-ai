"""Integration tests for enhanced API endpoints.

Tests the following enhanced endpoints:
- GET /api/v1/hackathons/{hack_id}/intelligence (organizer dashboard)
- GET /api/v1/submissions/{sub_id}/individual-scorecards (individual scorecards)
- GET /api/v1/submissions/{sub_id}/scorecard (enhanced scorecard with team dynamics)
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.models.common import SubmissionStatus
from src.models.dashboard import (
    CommonIssue,
    HiringIntelligence,
    OrganizerDashboard,
    PrizeRecommendation,
    TechnologyTrends,
    TopPerformer,
)
from src.models.feedback import ActionableFeedback, CodeExample, EffortEstimate, LearningResource
from src.models.strategy import LearningJourney, StrategyAnalysisResult, Tradeoff
from src.models.submission import (
    ScorecardResponse,
    SubmissionResponse,
)
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
# FIXTURES
# ============================================================


@pytest.fixture
def mock_services():
    """Mock all service dependencies."""
    with (
        patch("src.api.dependencies.get_submission_service") as mock_sub_service,
        patch("src.api.dependencies.get_hackathon_service") as mock_hack_service,
        patch("src.api.dependencies.get_organizer_service") as mock_org_service,
        patch("src.api.dependencies.get_organizer_intelligence_service") as mock_intel_service,
    ):
        # Mock organizer service for auth
        org_service = MagicMock()
        org_service.verify_api_key.return_value = "org_123"
        org_service.get_organizer.return_value = MagicMock(
            org_id="org_123",
            email="test@example.com",
            model_dump=lambda: {"org_id": "org_123", "email": "test@example.com"},
        )
        mock_org_service.return_value = org_service

        # Mock hackathon service
        hack_service = MagicMock()
        hack_service.get_hackathon.return_value = MagicMock(
            hack_id="hack_123", org_id="org_123", name="Test Hackathon"
        )
        mock_hack_service.return_value = hack_service

        # Mock submission service
        sub_service = MagicMock()
        mock_sub_service.return_value = sub_service

        # Mock intelligence service
        intel_service = MagicMock()
        mock_intel_service.return_value = intel_service

        yield {
            "submission": sub_service,
            "hackathon": hack_service,
            "organizer": org_service,
            "intelligence": intel_service,
        }


@pytest.fixture
def sample_submission():
    """Sample submission response."""
    return SubmissionResponse(
        sub_id="sub_123",
        hack_id="hack_123",
        team_name="Test Team",
        repo_url="https://github.com/test/repo",
        status=SubmissionStatus.COMPLETED,
        overall_score=85.5,
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-01T00:00:00Z",
    )


@pytest.fixture
def sample_individual_scorecards():
    """Sample individual scorecards."""
    return [
        IndividualScorecard(
            contributor_name="Alice",
            contributor_email="alice@example.com",
            role=ContributorRole.BACKEND,
            expertise_areas=[ExpertiseArea.DATABASE, ExpertiseArea.API],
            commit_count=50,
            lines_added=1000,
            lines_deleted=200,
            files_touched=["src/api.py", "src/db.py"],
            notable_contributions=["Implemented authentication system"],
            strengths=["Strong backend skills", "Good code quality"],
            weaknesses=["Limited frontend experience"],
            growth_areas=["Learn React"],
            work_style=WorkStyle(
                commit_frequency="frequent",
                avg_commit_size=50,
                active_hours=[9, 10, 11, 14, 15, 16],
                late_night_commits=2,
                weekend_commits=5,
            ),
            hiring_signals=HiringSignals(
                recommended_role="Backend Engineer",
                seniority_level="mid",
                salary_range_usd="$80k-$100k",
                must_interview=True,
                sponsor_interest=["TechCorp"],
                rationale="Strong backend skills with production experience",
            ),
        ),
        IndividualScorecard(
            contributor_name="Bob",
            contributor_email="bob@example.com",
            role=ContributorRole.FRONTEND,
            expertise_areas=[ExpertiseArea.UI_UX],
            commit_count=30,
            lines_added=800,
            lines_deleted=100,
            files_touched=["src/components/App.tsx", "src/styles.css"],
            notable_contributions=["Built responsive UI"],
            strengths=["Excellent UI/UX skills"],
            weaknesses=["Limited backend experience"],
            growth_areas=["Learn API design"],
            work_style=WorkStyle(
                commit_frequency="moderate",
                avg_commit_size=40,
                active_hours=[10, 11, 14, 15, 16, 17],
                late_night_commits=1,
                weekend_commits=3,
            ),
            hiring_signals=HiringSignals(
                recommended_role="Frontend Engineer",
                seniority_level="junior",
                salary_range_usd="$60k-$80k",
                must_interview=False,
                sponsor_interest=[],
                rationale="Solid frontend skills, needs more experience",
            ),
        ),
    ]


@pytest.fixture
def sample_organizer_dashboard():
    """Sample organizer dashboard."""
    return OrganizerDashboard(
        hack_id="hack_123",
        hackathon_name="Test Hackathon",
        total_submissions=10,
        top_performers=[
            TopPerformer(
                team_name="Team Alpha",
                sub_id="sub_001",
                overall_score=95.0,
                key_strengths=["Excellent architecture", "Strong testing"],
                sponsor_interest_flags=["TechCorp", "StartupX"],
            ),
            TopPerformer(
                team_name="Team Beta",
                sub_id="sub_002",
                overall_score=92.0,
                key_strengths=["Innovative approach", "Great documentation"],
                sponsor_interest_flags=["StartupX"],
            ),
        ],
        hiring_intelligence=HiringIntelligence(
            backend_candidates=[],
            frontend_candidates=[],
            devops_candidates=[],
            full_stack_candidates=[],
            must_interview=[],
        ),
        technology_trends=TechnologyTrends(
            most_used=[("Python", 8), ("JavaScript", 6), ("TypeScript", 4)],
            emerging=["Rust", "Go"],
            popular_stacks=[("Python + FastAPI + PostgreSQL", 5), ("React + Node.js", 4)],
        ),
        common_issues=[
            CommonIssue(
                issue_type="Missing error handling",
                percentage_affected=60.0,
                workshop_recommendation="Error handling best practices workshop",
                example_teams=["Team Alpha", "Team Beta"],
            ),
            CommonIssue(
                issue_type="Weak test coverage",
                percentage_affected=40.0,
                workshop_recommendation="Testing strategies workshop",
                example_teams=["Team Gamma"],
            ),
        ],
        standout_moments=[
            "Team Alpha implemented real-time collaboration features",
            "Team Beta created excellent API documentation",
        ],
        prize_recommendations=[
            PrizeRecommendation(
                prize_category="Best Team Dynamics",
                recommended_team="Team Alpha",
                sub_id="sub_001",
                justification="Excellent collaboration patterns and balanced workload",
                evidence=["Pair programming detected", "High commit message quality"],
            ),
        ],
        next_hackathon_recommendations=[
            "Offer error handling workshop",
            "Provide testing templates",
        ],
        sponsor_follow_up_actions=[
            "TechCorp: Interview Team Alpha (backend roles)",
            "StartupX: Interview Team Beta (full-stack roles)",
        ],
    )


# ============================================================
# TEST: GET /api/v1/hackathons/{hack_id}/intelligence
# ============================================================


def test_get_organizer_intelligence_success(mock_services, sample_organizer_dashboard):
    """Test successful retrieval of organizer intelligence dashboard."""
    mock_services["intelligence"].generate_dashboard.return_value = sample_organizer_dashboard

    client = TestClient(app)
    response = client.get(
        "/api/v1/hackathons/hack_123/intelligence", headers={"X-API-Key": "test_key"}
    )

    assert response.status_code == 200
    data = response.json()

    # Verify dashboard structure
    assert data["hack_id"] == "hack_123"
    assert data["hackathon_name"] == "Test Hackathon"
    assert data["total_submissions"] == 10

    # Verify top performers
    assert len(data["top_performers"]) == 2
    assert data["top_performers"][0]["team_name"] == "Team Alpha"
    assert data["top_performers"][0]["overall_score"] == 95.0

    # Verify technology trends
    assert len(data["technology_trends"]["most_used"]) == 3
    assert data["technology_trends"]["most_used"][0] == ["Python", 8]

    # Verify common issues
    assert len(data["common_issues"]) == 2
    assert data["common_issues"][0]["issue_type"] == "Missing error handling"
    assert data["common_issues"][0]["percentage_affected"] == 60.0

    # Verify prize recommendations
    assert len(data["prize_recommendations"]) == 1
    assert data["prize_recommendations"][0]["prize_category"] == "Best Team Dynamics"

    # Verify service was called correctly
    mock_services["intelligence"].generate_dashboard.assert_called_once_with("hack_123")


def test_get_organizer_intelligence_hackathon_not_found(mock_services):
    """Test 404 when hackathon not found."""
    mock_services["hackathon"].get_hackathon.return_value = None

    client = TestClient(app)
    response = client.get(
        "/api/v1/hackathons/hack_999/intelligence", headers={"X-API-Key": "test_key"}
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_organizer_intelligence_forbidden(mock_services):
    """Test 403 when organizer doesn't own the hackathon."""
    # Hackathon owned by different organizer
    mock_services["hackathon"].get_hackathon.return_value = MagicMock(
        hack_id="hack_123",
        org_id="org_999",  # Different org
        name="Test Hackathon",
    )

    client = TestClient(app)
    response = client.get(
        "/api/v1/hackathons/hack_123/intelligence", headers={"X-API-Key": "test_key"}
    )

    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower()


def test_get_organizer_intelligence_no_auth(mock_services):
    """Test 401 when no API key provided."""
    client = TestClient(app)
    response = client.get("/api/v1/hackathons/hack_123/intelligence")

    assert response.status_code == 401


def test_get_organizer_intelligence_service_error(mock_services):
    """Test 500 when intelligence service fails."""
    mock_services["intelligence"].generate_dashboard.side_effect = Exception("Database error")

    client = TestClient(app)
    response = client.get(
        "/api/v1/hackathons/hack_123/intelligence", headers={"X-API-Key": "test_key"}
    )

    assert response.status_code == 500
    assert "failed to generate" in response.json()["detail"].lower()


def test_get_organizer_intelligence_no_submissions(mock_services):
    """Test dashboard with no submissions."""
    empty_dashboard = OrganizerDashboard(
        hack_id="hack_123",
        hackathon_name="Test Hackathon",
        total_submissions=0,
        top_performers=[],
        hiring_intelligence=HiringIntelligence(
            backend_candidates=[],
            frontend_candidates=[],
            devops_candidates=[],
            full_stack_candidates=[],
            must_interview=[],
        ),
        technology_trends=TechnologyTrends(
            most_used=[],
            emerging=[],
            popular_stacks=[],
        ),
        common_issues=[],
        standout_moments=[],
        prize_recommendations=[],
        next_hackathon_recommendations=[],
        sponsor_follow_up_actions=[],
    )
    mock_services["intelligence"].generate_dashboard.return_value = empty_dashboard

    client = TestClient(app)
    response = client.get(
        "/api/v1/hackathons/hack_123/intelligence", headers={"X-API-Key": "test_key"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_submissions"] == 0
    assert data["top_performers"] == []


# ============================================================
# TEST: GET /api/v1/submissions/{sub_id}/individual-scorecards
# ============================================================


def test_get_individual_scorecards_success(
    mock_services, sample_submission, sample_individual_scorecards
):
    """Test successful retrieval of individual scorecards."""
    mock_services["submission"].get_submission.return_value = sample_submission
    mock_services[
        "submission"
    ].get_individual_scorecards.return_value = sample_individual_scorecards

    client = TestClient(app)
    response = client.get(
        "/api/v1/submissions/sub_123/individual-scorecards", headers={"X-API-Key": "test_key"}
    )

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert data["sub_id"] == "sub_123"
    assert data["hack_id"] == "hack_123"
    assert data["team_name"] == "Test Team"
    assert data["total_count"] == 2

    # Verify scorecards
    assert len(data["scorecards"]) == 2

    # Verify Alice's scorecard
    alice = data["scorecards"][0]
    assert alice["contributor_name"] == "Alice"
    assert alice["role"] == "backend"
    assert alice["commit_count"] == 50
    assert "database" in alice["expertise_areas"]
    assert alice["hiring_signals"]["must_interview"] is True

    # Verify Bob's scorecard
    bob = data["scorecards"][1]
    assert bob["contributor_name"] == "Bob"
    assert bob["role"] == "frontend"
    assert bob["commit_count"] == 30
    assert bob["hiring_signals"]["must_interview"] is False


def test_get_individual_scorecards_submission_not_found(mock_services):
    """Test 404 when submission not found."""
    mock_services["submission"].get_submission.return_value = None

    client = TestClient(app)
    response = client.get(
        "/api/v1/submissions/sub_999/individual-scorecards", headers={"X-API-Key": "test_key"}
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_individual_scorecards_forbidden(mock_services, sample_submission):
    """Test 403 when organizer doesn't own the hackathon."""
    mock_services["submission"].get_submission.return_value = sample_submission

    # Hackathon owned by different organizer
    mock_services["hackathon"].get_hackathon.return_value = MagicMock(
        hack_id="hack_123",
        org_id="org_999",  # Different org
        name="Test Hackathon",
    )

    client = TestClient(app)
    response = client.get(
        "/api/v1/submissions/sub_123/individual-scorecards", headers={"X-API-Key": "test_key"}
    )

    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower()


def test_get_individual_scorecards_empty(mock_services, sample_submission):
    """Test successful response with empty scorecards."""
    mock_services["submission"].get_submission.return_value = sample_submission
    mock_services["submission"].get_individual_scorecards.return_value = []

    client = TestClient(app)
    response = client.get(
        "/api/v1/submissions/sub_123/individual-scorecards", headers={"X-API-Key": "test_key"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 0
    assert data["scorecards"] == []


# ============================================================
# TEST: GET /api/v1/submissions/{sub_id}/scorecard (Enhanced)
# ============================================================


def test_get_enhanced_scorecard_success(mock_services):
    """Test successful retrieval of enhanced scorecard with team dynamics."""
    # Create enhanced scorecard with team dynamics, strategy, and feedback
    enhanced_scorecard = ScorecardResponse(
        sub_id="sub_123",
        hack_id="hack_123",
        team_name="Test Team",
        repo_url="https://github.com/test/repo",
        overall_score=85.5,
        agent_scores={},
        team_analysis=TeamAnalysisResult(
            workload_distribution={"Alice": 60.0, "Bob": 40.0},
            collaboration_patterns=[
                CollaborationPattern(
                    pattern_type="pair_programming",
                    contributors=["Alice", "Bob"],
                    evidence="Alternating commits on same files",
                    positive=True,
                )
            ],
            red_flags=[],
            individual_scorecards=[],
            team_dynamics_grade="A",
            commit_message_quality=0.85,
            panic_push_detected=False,
            duration_ms=150,
        ),
        strategy_analysis=StrategyAnalysisResult(
            test_strategy="unit_focused",
            critical_path_focus=True,
            tradeoffs=[
                Tradeoff(
                    tradeoff_type="speed_vs_security",
                    decision="Prioritized speed for demo",
                    rationale="Hackathon time constraints",
                    impact_on_score="Minor deduction on security score",
                )
            ],
            learning_journey=LearningJourney(
                technology="FastAPI",
                evidence=["First FastAPI commit", "Learning async patterns"],
                progression="Rapid improvement in API design",
                impressive=True,
            ),
            maturity_level="mid",
            strategic_context="Team showed good prioritization for hackathon scope",
            duration_ms=120,
        ),
        actionable_feedback=[
            ActionableFeedback(
                priority=1,
                finding="SQL injection vulnerability in user input",
                acknowledgment="Great job implementing the authentication system!",
                context="This is a common issue in hackathons when moving fast",
                code_example=CodeExample(
                    vulnerable_code='query = f"SELECT * FROM users WHERE id = {user_id}"',
                    fixed_code='query = "SELECT * FROM users WHERE id = ?" params = (user_id,)',
                    explanation="Use parameterized queries to prevent SQL injection",
                ),
                why_vulnerable="Allows attackers to inject malicious SQL",
                why_fixed="Parameterized queries escape user input safely",
                testing_instructions="Try entering `1 OR 1=1` as user_id",
                learning_resources=[
                    LearningResource(
                        title="OWASP SQL Injection Guide",
                        url="https://owasp.org/www-community/attacks/SQL_Injection",
                        resource_type="guide",
                    )
                ],
                effort_estimate=EffortEstimate(
                    minutes=15,
                    difficulty="Easy",
                ),
                business_impact="Critical: Could expose all user data",
            )
        ],
    )

    mock_services["submission"].get_submission_scorecard.return_value = enhanced_scorecard

    client = TestClient(app)
    response = client.get("/api/v1/submissions/sub_123/scorecard")

    assert response.status_code == 200
    data = response.json()

    # Verify basic fields
    assert data["sub_id"] == "sub_123"
    assert data["overall_score"] == 85.5

    # Verify team analysis
    assert data["team_analysis"] is not None
    assert data["team_analysis"]["team_dynamics_grade"] == "A"
    assert data["team_analysis"]["workload_distribution"]["Alice"] == 60.0
    assert len(data["team_analysis"]["collaboration_patterns"]) == 1

    # Verify strategy analysis
    assert data["strategy_analysis"] is not None
    assert data["strategy_analysis"]["test_strategy"] == "unit_focused"
    assert data["strategy_analysis"]["maturity_level"] == "mid"
    assert data["strategy_analysis"]["learning_journey"]["impressive"] is True

    # Verify actionable feedback
    assert len(data["actionable_feedback"]) == 1
    feedback = data["actionable_feedback"][0]
    assert feedback["priority"] == 1
    assert "SQL injection" in feedback["finding"]
    assert feedback["code_example"] is not None
    assert feedback["effort_estimate"]["minutes"] == 15


def test_get_enhanced_scorecard_not_found(mock_services):
    """Test 404 when scorecard not found."""
    mock_services["submission"].get_submission_scorecard.return_value = None

    client = TestClient(app)
    response = client.get("/api/v1/submissions/sub_999/scorecard")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_enhanced_scorecard_with_red_flags(mock_services):
    """Test scorecard with red flags in team analysis."""
    scorecard_with_red_flags = ScorecardResponse(
        sub_id="sub_123",
        hack_id="hack_123",
        team_name="Test Team",
        repo_url="https://github.com/test/repo",
        overall_score=65.0,
        agent_scores={},
        team_analysis=TeamAnalysisResult(
            workload_distribution={"Alice": 95.0, "Bob": 5.0},
            collaboration_patterns=[],
            red_flags=[
                RedFlag(
                    flag_type="extreme_imbalance",
                    severity=RedFlagSeverity.CRITICAL,
                    description="One contributor did 95% of the work",
                    evidence="Alice: 95 commits, Bob: 5 commits",
                    impact="Indicates poor team collaboration",
                    hiring_impact="Disqualifies from team awards",
                    recommended_action="Review team dynamics and contribution patterns",
                ),
                RedFlag(
                    flag_type="minimal_contribution",
                    severity=RedFlagSeverity.HIGH,
                    description="Bob has minimal contributions",
                    evidence="Only 5 commits in 2-person team",
                    impact="Questions team member engagement",
                    hiring_impact="Bob may not be suitable for team roles",
                    recommended_action="Interview separately to understand circumstances",
                ),
            ],
            individual_scorecards=[],
            team_dynamics_grade="D",
            commit_message_quality=0.70,
            panic_push_detected=True,
            duration_ms=150,
        ),
        strategy_analysis=None,
        actionable_feedback=[],
    )

    mock_services["submission"].get_submission_scorecard.return_value = scorecard_with_red_flags

    client = TestClient(app)
    response = client.get("/api/v1/submissions/sub_123/scorecard")

    assert response.status_code == 200
    data = response.json()

    # Verify red flags
    assert len(data["team_analysis"]["red_flags"]) == 2
    assert data["team_analysis"]["red_flags"][0]["severity"] == "critical"
    assert data["team_analysis"]["red_flags"][0]["flag_type"] == "extreme_imbalance"
    assert data["team_analysis"]["team_dynamics_grade"] == "D"
    assert data["team_analysis"]["panic_push_detected"] is True


def test_get_enhanced_scorecard_minimal_intelligence(mock_services):
    """Test scorecard with minimal intelligence layer (analysis failed)."""
    minimal_scorecard = ScorecardResponse(
        sub_id="sub_123",
        hack_id="hack_123",
        team_name="Test Team",
        repo_url="https://github.com/test/repo",
        overall_score=75.0,
        agent_scores={},
        team_analysis=None,  # Analysis failed
        strategy_analysis=None,  # Analysis failed
        actionable_feedback=[],  # No feedback generated
    )

    mock_services["submission"].get_submission_scorecard.return_value = minimal_scorecard

    client = TestClient(app)
    response = client.get("/api/v1/submissions/sub_123/scorecard")

    assert response.status_code == 200
    data = response.json()

    # Verify graceful degradation
    assert data["overall_score"] == 75.0
    assert data["team_analysis"] is None
    assert data["strategy_analysis"] is None
    assert data["actionable_feedback"] == []


# ============================================================
# TEST: Cross-Endpoint Integration
# ============================================================


def test_intelligence_dashboard_aggregates_individual_scorecards(
    mock_services, sample_organizer_dashboard
):
    """Test that intelligence dashboard includes aggregated hiring intelligence."""
    # Add hiring intelligence to dashboard
    sample_organizer_dashboard.hiring_intelligence = HiringIntelligence(
        backend_candidates=[
            IndividualScorecard(
                contributor_name="Alice",
                contributor_email="alice@example.com",
                role=ContributorRole.BACKEND,
                expertise_areas=[ExpertiseArea.DATABASE],
                commit_count=50,
                lines_added=1000,
                lines_deleted=200,
                files_touched=["src/api.py"],
                notable_contributions=["Auth system"],
                strengths=["Strong backend"],
                weaknesses=["Limited frontend"],
                growth_areas=["Learn React"],
                work_style=WorkStyle(
                    commit_frequency="frequent",
                    avg_commit_size=50,
                    active_hours=[9, 10, 11],
                    late_night_commits=0,
                    weekend_commits=0,
                ),
                hiring_signals=HiringSignals(
                    recommended_role="Backend Engineer",
                    seniority_level="mid",
                    salary_range_usd="$80k-$100k",
                    must_interview=True,
                    sponsor_interest=["TechCorp"],
                    rationale="Strong backend skills",
                ),
            )
        ],
        frontend_candidates=[],
        devops_candidates=[],
        full_stack_candidates=[],
        must_interview=[],
    )

    mock_services["intelligence"].generate_dashboard.return_value = sample_organizer_dashboard

    client = TestClient(app)
    response = client.get(
        "/api/v1/hackathons/hack_123/intelligence", headers={"X-API-Key": "test_key"}
    )

    assert response.status_code == 200
    data = response.json()

    # Verify hiring intelligence is included
    assert "hiring_intelligence" in data
    assert len(data["hiring_intelligence"]["backend_candidates"]) == 1
    assert data["hiring_intelligence"]["backend_candidates"][0]["contributor_name"] == "Alice"


def test_scorecard_feedback_references_strategy_context(mock_services):
    """Test that actionable feedback considers strategic context."""
    scorecard = ScorecardResponse(
        sub_id="sub_123",
        hack_id="hack_123",
        team_name="Test Team",
        repo_url="https://github.com/test/repo",
        overall_score=80.0,
        agent_scores={},
        team_analysis=None,
        strategy_analysis=StrategyAnalysisResult(
            test_strategy="demo_first",
            critical_path_focus=False,
            tradeoffs=[
                Tradeoff(
                    tradeoff_type="speed_vs_security",
                    decision="Prioritized demo polish over security",
                    rationale="Hackathon presentation focus",
                    impact_on_score="Security score adjusted for context",
                )
            ],
            learning_journey=None,
            maturity_level="junior",
            strategic_context="Demo-first approach appropriate for hackathon",
            duration_ms=100,
        ),
        actionable_feedback=[
            ActionableFeedback(
                priority=2,
                finding="Missing input validation",
                acknowledgment="Great demo! The UI is polished.",
                context="Given your demo-first strategy, this is understandable",
                code_example=None,
                why_vulnerable="Could allow invalid data",
                why_fixed="Validation ensures data integrity",
                testing_instructions="Test with edge cases",
                learning_resources=[],
                effort_estimate=EffortEstimate(minutes=30, difficulty="Moderate"),
                business_impact="Medium: Could cause data issues in production",
            )
        ],
    )

    mock_services["submission"].get_submission_scorecard.return_value = scorecard

    client = TestClient(app)
    response = client.get("/api/v1/submissions/sub_123/scorecard")

    assert response.status_code == 200
    data = response.json()

    # Verify feedback acknowledges strategy
    feedback = data["actionable_feedback"][0]
    assert "demo-first strategy" in feedback["context"].lower()
    assert data["strategy_analysis"]["test_strategy"] == "demo_first"
