"""Integration tests for enhanced AnalysisOrchestrator with intelligence layer."""

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from src.analysis.orchestrator import AnalysisOrchestrator
from src.models.analysis import CommitInfo, RepoData, SourceFile
from src.models.common import AgentName
from src.models.hackathon import RubricConfig, RubricDimension
from src.models.submission import RepoMeta
from tests.fixtures.complete_mock_responses import (AI_DETECTION_RESPONSE,
                                                    BUG_HUNTER_RESPONSE,
                                                    INNOVATION_RESPONSE,
                                                    PERFORMANCE_RESPONSE)

# ============================================================
# HELPER FUNCTIONS
# ============================================================


def setup_mock_bedrock_response(mock_bedrock: MagicMock, response_json_str: str) -> None:
    """Setup mock Bedrock client with complete response.

    Args:
        mock_bedrock: MagicMock instance of BedrockClient
        response_json_str: JSON string response from agent
    """
    mock_bedrock.converse.return_value = {
        "content": response_json_str,
        "usage": {"input_tokens": 1000, "output_tokens": 500, "total_tokens": 1500},
        "latency_ms": 1200,
    }
    mock_bedrock.parse_json_response.return_value = json.loads(response_json_str)


# ============================================================
# FIXTURES
# ============================================================


@pytest.fixture
def sample_repo_data() -> RepoData:
    """Sample repository data for testing."""
    return RepoData(
        repo_url="https://github.com/test-org/test-repo",
        repo_owner="test-org",
        repo_name="test-repo",
        default_branch="main",
        meta=RepoMeta(
            primary_language="Python",
            languages={"Python": 5000, "JavaScript": 1000},
            total_files=25,
            total_lines=6000,
            commit_count=50,
            first_commit_at=datetime(2024, 1, 1, tzinfo=UTC),
            last_commit_at=datetime(2024, 2, 1, tzinfo=UTC),
            development_duration_hours=120.0,
            workflow_run_count=10,
            workflow_success_rate=0.9,
        ),
        source_files=[
            SourceFile(
                path="src/main.py",
                language="Python",
                lines=150,
                content="def main():\n    print('Hello World')\n",
            ),
        ],
        commit_history=[
            CommitInfo(
                hash="abc123",
                short_hash="abc123",
                author="Alice",
                timestamp=datetime(2024, 1, 15, tzinfo=UTC),
                message="Initial commit",
                files_changed=5,
                insertions=100,
                deletions=0,
            ),
            CommitInfo(
                hash="def456",
                short_hash="def456",
                author="Bob",
                timestamp=datetime(2024, 1, 20, tzinfo=UTC),
                message="Add API endpoints",
                files_changed=3,
                insertions=200,
                deletions=10,
            ),
        ],
        readme_content="# Test Project\n\nThis is a test project.",
        file_tree="src/\n  main.py\n",
        workflow_definitions=["name: CI\non: [push]"],
    )


@pytest.fixture
def sample_rubric() -> RubricConfig:
    """Sample rubric configuration."""
    return RubricConfig(
        dimensions=[
            RubricDimension(name="Code Quality", agent=AgentName.BUG_HUNTER, weight=0.3),
            RubricDimension(name="Architecture", agent=AgentName.PERFORMANCE, weight=0.3),
            RubricDimension(name="Innovation", agent=AgentName.INNOVATION, weight=0.3),
            RubricDimension(name="Authenticity", agent=AgentName.AI_DETECTION, weight=0.1),
        ]
    )


# ============================================================
# TEST: Full Analysis Pipeline with Intelligence Layer
# ============================================================


@pytest.mark.asyncio
async def test_analyze_submission_with_intelligence_layer(
    sample_repo_data: RepoData,
    sample_rubric: RubricConfig,
) -> None:
    """Test full analysis pipeline including team dynamics, strategy, and feedback."""
    with patch("src.analysis.orchestrator.BedrockClient") as mock_bedrock_cls:
        # Setup mock Bedrock client
        mock_bedrock = MagicMock()
        mock_bedrock_cls.return_value = mock_bedrock

        # Setup mock Bedrock client with complete response
        setup_mock_bedrock_response(mock_bedrock, BUG_HUNTER_RESPONSE)

        orchestrator = AnalysisOrchestrator(bedrock_client=mock_bedrock)

        # Mock intelligence components
        with (
            patch.object(orchestrator.team_analyzer, "analyze") as mock_team,
            patch.object(orchestrator.strategy_detector, "analyze") as mock_strategy,
            patch.object(
                orchestrator.brand_voice_transformer, "transform_findings"
            ) as mock_feedback,
        ):
            # Setup mock returns
            mock_team.return_value = MagicMock(
                team_dynamics_grade="A",
                red_flags=[],
                individual_scorecards=[],
                duration_ms=100,
            )
            mock_strategy.return_value = MagicMock(
                test_strategy="unit_focused",
                maturity_level="senior",
                tradeoffs=[],
                duration_ms=100,
            )
            mock_feedback.return_value = []

            # Run analysis
            result = await orchestrator.analyze_submission(
                repo_data=sample_repo_data,
                hackathon_name="Test Hackathon",
                team_name="Test Team",
                hack_id="HACK#123",
                sub_id="SUB#456",
                rubric=sample_rubric,
                agents_enabled=[AgentName.BUG_HUNTER],
            )

            # Verify intelligence layer was invoked
            mock_team.assert_called_once()
            mock_strategy.assert_called_once()
            mock_feedback.assert_called_once()

            # Verify result structure
            assert "team_analysis" in result
            assert "strategy_analysis" in result
            assert "actionable_feedback" in result
            assert result["team_analysis"].team_dynamics_grade == "A"
            assert result["strategy_analysis"].test_strategy == "unit_focused"


@pytest.mark.asyncio
async def test_analyze_submission_with_cicd_parsing(
    sample_repo_data: RepoData,
    sample_rubric: RubricConfig,
) -> None:
    """Test analysis with CI/CD log parsing."""
    with (
        patch("src.analysis.orchestrator.BedrockClient") as mock_bedrock_cls,
        patch("src.analysis.orchestrator.ActionsAnalyzer") as mock_actions_cls,
    ):
        # Setup mocks with complete Pydantic-compliant data
        mock_bedrock = MagicMock()
        mock_bedrock_cls.return_value = mock_bedrock
        setup_mock_bedrock_response(mock_bedrock, BUG_HUNTER_RESPONSE)

        mock_actions = MagicMock()
        mock_actions_cls.return_value = mock_actions
        mock_actions.analyze.return_value = {
            "linter_findings": [{"file": "src/main.py", "line": 10, "message": "Line too long"}],
            "test_results": {"total": 10, "passed": 9, "failed": 1},
        }

        orchestrator = AnalysisOrchestrator(bedrock_client=mock_bedrock)

        # Run analysis with GitHub token
        result = await orchestrator.analyze_submission(
            repo_data=sample_repo_data,
            hackathon_name="Test Hackathon",
            team_name="Test Team",
            hack_id="HACK#123",
            sub_id="SUB#456",
            rubric=sample_rubric,
            agents_enabled=[AgentName.BUG_HUNTER],
            github_token="ghp_test_token",
        )

        # Verify CI/CD analyzer was called
        mock_actions.analyze.assert_called_once_with("test-org", "test-repo")
        mock_actions.close.assert_called_once()

        # Verify findings were captured
        assert result["cicd_findings_count"] == 1


@pytest.mark.asyncio
async def test_analyze_submission_cicd_parsing_failure(
    sample_repo_data: RepoData,
    sample_rubric: RubricConfig,
) -> None:
    """Test analysis continues gracefully when CI/CD parsing fails."""
    with (
        patch("src.analysis.orchestrator.BedrockClient") as mock_bedrock_cls,
        patch("src.analysis.actions_analyzer.ActionsAnalyzer") as mock_actions_cls,
    ):
        mock_bedrock = MagicMock()
        mock_bedrock_cls.return_value = mock_bedrock
        setup_mock_bedrock_response(mock_bedrock, BUG_HUNTER_RESPONSE)

        mock_actions = MagicMock()
        mock_actions_cls.return_value = mock_actions
        mock_actions.analyze.side_effect = Exception("API rate limit exceeded")

        orchestrator = AnalysisOrchestrator(bedrock_client=mock_bedrock)

        result = await orchestrator.analyze_submission(
            repo_data=sample_repo_data,
            hackathon_name="Test Hackathon",
            team_name="Test Team",
            hack_id="HACK#123",
            sub_id="SUB#456",
            rubric=sample_rubric,
            agents_enabled=[AgentName.BUG_HUNTER],
            github_token="ghp_test_token",
        )

        assert result["overall_score"] > 0
        assert result["cicd_findings_count"] == 0

        component_perf = result["component_performance"]
        actions_records = [r for r in component_perf if r.component_name == "actions_analyzer"]
        assert len(actions_records) == 1
        assert actions_records[0].success is False


@pytest.mark.asyncio
async def test_analyze_submission_team_analysis_failure(
    sample_repo_data: RepoData,
    sample_rubric: RubricConfig,
) -> None:
    """Test analysis continues gracefully when team analysis fails."""
    with patch("src.analysis.orchestrator.BedrockClient") as mock_bedrock_cls:
        mock_bedrock = MagicMock()
        mock_bedrock_cls.return_value = mock_bedrock
        setup_mock_bedrock_response(mock_bedrock, BUG_HUNTER_RESPONSE)

        orchestrator = AnalysisOrchestrator(bedrock_client=mock_bedrock)

        with patch.object(orchestrator.team_analyzer, "analyze") as mock_team:
            mock_team.side_effect = Exception("Team analysis error")

            result = await orchestrator.analyze_submission(
                repo_data=sample_repo_data,
                hackathon_name="Test Hackathon",
                team_name="Test Team",
                hack_id="HACK#123",
                sub_id="SUB#456",
                rubric=sample_rubric,
                agents_enabled=[AgentName.BUG_HUNTER],
            )

            assert result["overall_score"] > 0
            assert result["team_analysis"] is None

            component_perf = result["component_performance"]
            team_records = [r for r in component_perf if r.component_name == "team_analyzer"]
            assert len(team_records) == 1
            assert team_records[0].success is False


@pytest.mark.asyncio
async def test_component_performance_tracking(
    sample_repo_data: RepoData,
    sample_rubric: RubricConfig,
) -> None:
    """Test that component performance is tracked for all intelligence components."""
    with patch("src.analysis.orchestrator.BedrockClient") as mock_bedrock_cls:
        mock_bedrock = MagicMock()
        mock_bedrock_cls.return_value = mock_bedrock
        setup_mock_bedrock_response(mock_bedrock, BUG_HUNTER_RESPONSE)

        orchestrator = AnalysisOrchestrator(bedrock_client=mock_bedrock)

        result = await orchestrator.analyze_submission(
            repo_data=sample_repo_data,
            hackathon_name="Test Hackathon",
            team_name="Test Team",
            hack_id="HACK#123",
            sub_id="SUB#456",
            rubric=sample_rubric,
            agents_enabled=[AgentName.BUG_HUNTER],
        )

        component_perf = result["component_performance"]
        component_names = [r.component_name for r in component_perf]

        assert "team_analyzer" in component_names
        assert "strategy_detector" in component_names
        assert "brand_voice_transformer" in component_names

        for record in component_perf:
            assert hasattr(record, "component_name")
            assert hasattr(record, "duration_ms")
            assert hasattr(record, "findings_count")
            assert hasattr(record, "success")
            assert record.duration_ms > 0


@pytest.mark.asyncio
async def test_static_context_passed_to_agents(
    sample_repo_data: RepoData,
    sample_rubric: RubricConfig,
) -> None:
    """Test that static findings from CI/CD are passed to agents as context."""
    with (
        patch("src.analysis.orchestrator.BedrockClient") as mock_bedrock_cls,
        patch("src.analysis.actions_analyzer.ActionsAnalyzer") as mock_actions_cls,
    ):
        mock_bedrock = MagicMock()
        mock_bedrock_cls.return_value = mock_bedrock
        setup_mock_bedrock_response(mock_bedrock, BUG_HUNTER_RESPONSE)

        analyze_calls = []

        def track_analyze(*args, **kwargs):
            from src.models.scores import (BugHunterResponse, BugHunterScores,
                                           CIObservations)

            analyze_calls.append(kwargs)
            # Return proper BugHunterResponse instead of MagicMock
            response = BugHunterResponse(
                agent="bug_hunter",
                prompt_version="v1",
                overall_score=8.5,
                summary="Test summary",
                confidence=0.9,
                scores=BugHunterScores(
                    code_quality=8.5,
                    security=9.0,
                    test_coverage=7.0,
                    error_handling=8.0,
                    dependency_hygiene=8.5,
                ),
                evidence=[],
                ci_observations=CIObservations(),
            )
            return (
                response,
                {"input_tokens": 1000, "output_tokens": 500, "latency_ms": 1200},
            )

        mock_actions = MagicMock()
        mock_actions_cls.return_value = mock_actions
        mock_actions.analyze.return_value = {
            "linter_findings": [
                {"file": "src/main.py", "line": 10, "message": "Line too long"},
                {"file": "src/api.py", "line": 25, "message": "Unused import"},
            ],
            "test_results": None,
        }

        orchestrator = AnalysisOrchestrator(bedrock_client=mock_bedrock)

        for agent in orchestrator.agents.values():
            agent.analyze = track_analyze

        await orchestrator.analyze_submission(
            repo_data=sample_repo_data,
            hackathon_name="Test Hackathon",
            team_name="Test Team",
            hack_id="HACK#123",
            sub_id="SUB#456",
            rubric=sample_rubric,
            agents_enabled=[AgentName.BUG_HUNTER],
            github_token="ghp_test_token",
        )

        assert len(analyze_calls) == 1
        assert "static_context" in analyze_calls[0]
        static_ctx = analyze_calls[0]["static_context"]
        assert static_ctx["findings_count"] == 2
        assert len(static_ctx["findings"]) == 2
        static_ctx = analyze_calls[0]["static_context"]
        assert static_ctx["findings_count"] == 2
        assert len(static_ctx["findings"]) == 2


@pytest.mark.asyncio
async def test_multiple_agents_with_intelligence_layer(
    sample_repo_data: RepoData,
    sample_rubric: RubricConfig,
) -> None:
    """Test analysis with multiple agents and full intelligence layer."""
    with patch("src.analysis.orchestrator.BedrockClient") as mock_bedrock_cls:
        mock_bedrock = MagicMock()
        mock_bedrock_cls.return_value = mock_bedrock
        # Mock responses for each agent type using side_effect
        mock_bedrock.converse.side_effect = [
            {
                "content": BUG_HUNTER_RESPONSE,
                "usage": {"input_tokens": 1000, "output_tokens": 500, "total_tokens": 1500},
                "latency_ms": 1200,
            },
            {
                "content": PERFORMANCE_RESPONSE,
                "usage": {"input_tokens": 1000, "output_tokens": 500, "total_tokens": 1500},
                "latency_ms": 1200,
            },
            {
                "content": INNOVATION_RESPONSE,
                "usage": {"input_tokens": 1000, "output_tokens": 500, "total_tokens": 1500},
                "latency_ms": 1200,
            },
            {
                "content": AI_DETECTION_RESPONSE,
                "usage": {"input_tokens": 1000, "output_tokens": 500, "total_tokens": 1500},
                "latency_ms": 1200,
            },
        ]

        # Mock parse_json_response to return parsed JSON for each agent
        mock_bedrock.parse_json_response.side_effect = [
            json.loads(BUG_HUNTER_RESPONSE),
            json.loads(PERFORMANCE_RESPONSE),
            json.loads(INNOVATION_RESPONSE),
            json.loads(AI_DETECTION_RESPONSE),
        ]

        orchestrator = AnalysisOrchestrator(bedrock_client=mock_bedrock)

        result = await orchestrator.analyze_submission(
            repo_data=sample_repo_data,
            hackathon_name="Test Hackathon",
            team_name="Test Team",
            hack_id="HACK#123",
            sub_id="SUB#456",
            rubric=sample_rubric,
            agents_enabled=[
                AgentName.BUG_HUNTER,
                AgentName.PERFORMANCE,
                AgentName.INNOVATION,
                AgentName.AI_DETECTION,
            ],
        )

        assert len(result["agent_responses"]) == 4
        assert AgentName.BUG_HUNTER in result["agent_responses"]
        assert AgentName.PERFORMANCE in result["agent_responses"]
        assert AgentName.INNOVATION in result["agent_responses"]
        assert AgentName.AI_DETECTION in result["agent_responses"]

        assert result["team_analysis"] is not None
        assert result["strategy_analysis"] is not None
        assert isinstance(result["actionable_feedback"], list)

        cost_records = result["cost_records"]
        assert len(cost_records) == 4
