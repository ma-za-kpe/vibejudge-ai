"""Performance test to verify analysis completes within 90 seconds."""

import json
import time
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
        "usage": {"input_tokens": 2000, "output_tokens": 800, "total_tokens": 2800},
        "latency_ms": 1500,
    }
    mock_bedrock.parse_json_response.return_value = json.loads(response_json_str)


# ============================================================
# FIXTURES
# ============================================================


@pytest.fixture
def realistic_repo_data() -> RepoData:
    """Realistic repository data simulating a typical hackathon submission."""
    # Simulate a medium-sized hackathon project
    commits = []
    for i in range(50):  # 50 commits
        commits.append(
            CommitInfo(
                hash=f"commit{i:03d}",
                short_hash=f"c{i:03d}",
                author=f"Developer{i % 3}",  # 3 team members
                timestamp=datetime(2024, 1, 1 + i // 10, tzinfo=UTC),
                message=f"Commit message {i}",
                files_changed=3,
                insertions=50,
                deletions=10,
            )
        )

    source_files = []
    for i in range(25):  # 25 source files
        source_files.append(
            SourceFile(
                path=f"src/module{i}.py",
                language="Python",
                lines=200,
                content=f"# Module {i}\n" + "def function():\n    pass\n" * 50,
            )
        )

    return RepoData(
        repo_url="https://github.com/hackathon-team/awesome-project",
        repo_owner="hackathon-team",
        repo_name="awesome-project",
        default_branch="main",
        meta=RepoMeta(
            primary_language="Python",
            languages={"Python": 5000, "JavaScript": 1000, "HTML": 500},
            total_files=25,
            total_lines=6500,
            commit_count=50,
            first_commit_at=datetime(2024, 1, 1, tzinfo=UTC),
            last_commit_at=datetime(2024, 2, 1, tzinfo=UTC),
            development_duration_hours=120.0,
            workflow_run_count=10,
            workflow_success_rate=0.9,
        ),
        source_files=source_files,
        commit_history=commits,
        readme_content="# Awesome Project\n\nA hackathon submission with detailed README.",
        file_tree="src/\n" + "\n".join([f"  module{i}.py" for i in range(25)]),
        workflow_definitions=["name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest"],
    )


@pytest.fixture
def standard_rubric() -> RubricConfig:
    """Standard rubric with all 4 agents."""
    return RubricConfig(
        dimensions=[
            RubricDimension(name="Code Quality", agent=AgentName.BUG_HUNTER, weight=0.3),
            RubricDimension(name="Architecture", agent=AgentName.PERFORMANCE, weight=0.3),
            RubricDimension(name="Innovation", agent=AgentName.INNOVATION, weight=0.3),
            RubricDimension(name="Authenticity", agent=AgentName.AI_DETECTION, weight=0.1),
        ]
    )


# ============================================================
# PERFORMANCE TESTS
# ============================================================


@pytest.mark.asyncio
@pytest.mark.performance
async def test_orchestrator_completes_within_90_seconds(
    realistic_repo_data: RepoData,
    standard_rubric: RubricConfig,
) -> None:
    """Test that orchestrator completes analysis within 90 seconds.

    This test verifies Requirement 10.6: Complete full analysis within 90 seconds.
    """
    with (
        patch("src.analysis.orchestrator.BedrockClient") as mock_bedrock_cls,
        patch("src.analysis.actions_analyzer.ActionsAnalyzer") as mock_actions_cls,
    ):
        # Setup mock Bedrock client with realistic latency
        mock_bedrock = MagicMock()
        mock_bedrock_cls.return_value = mock_bedrock

        def mock_converse(*args, **kwargs):
            # Simulate realistic Bedrock API latency (1-2 seconds per call)
            time.sleep(1.5)
            # Return appropriate response based on call count
            call_count = getattr(mock_converse, "call_count", 0)
            mock_converse.call_count = call_count + 1

            responses = [
                BUG_HUNTER_RESPONSE,
                PERFORMANCE_RESPONSE,
                INNOVATION_RESPONSE,
                AI_DETECTION_RESPONSE,
            ]

            content = responses[call_count % len(responses)]

            return {
                "content": content,
                "usage": {"input_tokens": 2000, "output_tokens": 800, "total_tokens": 2800},
                "latency_ms": 1500,
            }

        mock_bedrock.converse = mock_converse

        # Mock parse_json_response to return parsed JSON
        def mock_parse_json(content):
            return json.loads(content)

        mock_bedrock.parse_json_response = mock_parse_json

        # Setup mock Actions analyzer with realistic latency
        mock_actions = MagicMock()
        mock_actions_cls.return_value = mock_actions

        def mock_analyze(*args, **kwargs):
            # Simulate CI/CD log parsing (5-10 seconds)
            time.sleep(7)
            return {
                "linter_findings": [
                    {"file": "src/main.py", "line": 10, "message": "Line too long"},
                    {"file": "src/api.py", "line": 25, "message": "Unused import"},
                ],
                "test_results": {"total": 10, "passed": 9, "failed": 1},
            }

        mock_actions.analyze = mock_analyze

        orchestrator = AnalysisOrchestrator(bedrock_client=mock_bedrock)

        # Start timer
        start_time = time.time()

        # Run full analysis with all 4 agents
        result = await orchestrator.analyze_submission(
            repo_data=realistic_repo_data,
            hackathon_name="Test Hackathon 2024",
            team_name="Awesome Team",
            hack_id="HACK#test123",
            sub_id="SUB#test456",
            rubric=standard_rubric,
            agents_enabled=[
                AgentName.BUG_HUNTER,
                AgentName.PERFORMANCE,
                AgentName.INNOVATION,
                AgentName.AI_DETECTION,
            ],
            github_token="ghp_test_token",
        )

        # Calculate duration
        duration_seconds = time.time() - start_time
        duration_ms = duration_seconds * 1000

        # Log results
        print(f"\n{'=' * 60}")
        print("PERFORMANCE TEST RESULTS")
        print(f"{'=' * 60}")
        print(f"Total Duration: {duration_seconds:.2f} seconds ({duration_ms:.0f} ms)")
        print("Target: 90 seconds (90000 ms)")
        print(f"Status: {'✅ PASS' if duration_seconds < 90 else '❌ FAIL'}")
        print(f"{'=' * 60}")

        # Print component breakdown
        if "component_performance" in result:
            print("\nComponent Performance Breakdown:")
            print(f"{'-' * 60}")
            total_component_ms = 0
            for record in result["component_performance"]:
                comp_name = record.component_name
                comp_duration = record.duration_ms
                comp_success = "✅" if record.success else "❌"
                total_component_ms += comp_duration
                print(f"  {comp_success} {comp_name:30s} {comp_duration:8.0f} ms")
            print(f"{'-' * 60}")
            print(f"  {'Total Components':30s} {total_component_ms:8.0f} ms")
            print(f"  {'Analysis Duration':30s} {result['analysis_duration_ms']:8.0f} ms")

        # Print agent performance
        if "cost_records" in result:
            print("\nAgent Performance:")
            print(f"{'-' * 60}")
            for record in result["cost_records"]:
                agent_name = (
                    record.agent_name.value
                    if hasattr(record.agent_name, "value")
                    else str(record.agent_name)
                )
                latency = record.latency_ms
                print(f"  {agent_name:30s} {latency:8.0f} ms")

        print(f"\n{'=' * 60}\n")

        # Assertions
        assert duration_seconds < 90, (
            f"Analysis took {duration_seconds:.2f}s, exceeding 90s target. "
            f"This violates Requirement 10.6."
        )

        # Verify all components completed
        assert result["overall_score"] > 0
        assert len(result["agent_responses"]) == 4
        assert result["team_analysis"] is not None
        assert result["strategy_analysis"] is not None

        # Verify performance tracking
        assert result["analysis_duration_ms"] < 90000


@pytest.mark.asyncio
@pytest.mark.performance
async def test_orchestrator_performance_with_failures(
    realistic_repo_data: RepoData,
    standard_rubric: RubricConfig,
) -> None:
    """Test that orchestrator still completes within 90s even with component failures.

    This verifies graceful degradation doesn't cause timeout issues.
    """
    with (
        patch("src.analysis.orchestrator.BedrockClient") as mock_bedrock_cls,
        patch("src.analysis.actions_analyzer.ActionsAnalyzer") as mock_actions_cls,
    ):
        mock_bedrock = MagicMock()
        mock_bedrock_cls.return_value = mock_bedrock

        def mock_converse(*args, **kwargs):
            time.sleep(1.5)
            return {
                "content": BUG_HUNTER_RESPONSE,
                "usage": {"input_tokens": 2000, "output_tokens": 800, "total_tokens": 2800},
                "latency_ms": 1500,
            }

        mock_bedrock.converse = mock_converse

        # Mock parse_json_response to return parsed JSON
        mock_bedrock.parse_json_response = lambda content: json.loads(content)

        # Make Actions analyzer fail
        mock_actions = MagicMock()
        mock_actions_cls.return_value = mock_actions
        mock_actions.analyze.side_effect = Exception("API rate limit")

        orchestrator = AnalysisOrchestrator(bedrock_client=mock_bedrock)

        # Make team analyzer fail
        with patch.object(orchestrator.team_analyzer, "analyze") as mock_team:
            mock_team.side_effect = Exception("Team analysis error")

            start_time = time.time()

            result = await orchestrator.analyze_submission(
                repo_data=realistic_repo_data,
                hackathon_name="Test Hackathon 2024",
                team_name="Awesome Team",
                hack_id="HACK#test123",
                sub_id="SUB#test456",
                rubric=standard_rubric,
                agents_enabled=[AgentName.BUG_HUNTER],
                github_token="ghp_test_token",
            )

            duration_seconds = time.time() - start_time

            print(f"\nPerformance with failures: {duration_seconds:.2f}s")

            # Should still complete within 90s
            assert duration_seconds < 90

            # Should have gracefully handled failures
            assert result["overall_score"] > 0
            assert result["team_analysis"] is None  # Failed

            # Check component performance records show failures
            component_perf = result["component_performance"]
            actions_records = [r for r in component_perf if r.component_name == "actions_analyzer"]
            team_records = [r for r in component_perf if r.component_name == "team_analyzer"]

            assert len(actions_records) == 1
            assert actions_records[0].success is False
            assert len(team_records) == 1
            assert team_records[0].success is False


@pytest.mark.performance
def test_performance_monitor_tracks_90s_target() -> None:
    """Test that PerformanceMonitor correctly tracks 90-second target."""
    from src.analysis.performance_monitor import (PERFORMANCE_TARGETS,
                                                  PerformanceMonitor)

    monitor = PerformanceMonitor("SUB#test")

    # Verify target is set correctly
    assert PERFORMANCE_TARGETS["total_pipeline"] == 90000

    # Simulate components
    with monitor.track("git_clone"):
        time.sleep(0.01)  # 10ms

    with monitor.track("orchestrator_analysis"):
        time.sleep(0.02)  # 20ms

    summary = monitor.get_summary()

    assert "total_duration_ms" in summary
    assert "within_target" in summary
    assert summary["target_ms"] == 90000
    assert summary["within_target"] is True  # Should be well under 90s

    # Test timeout risk detection
    assert monitor.check_timeout_risk() is False  # Should be well under 75% threshold


@pytest.mark.performance
def test_performance_targets_are_reasonable() -> None:
    """Test that performance targets sum to approximately 90 seconds."""
    from src.analysis.performance_monitor import PERFORMANCE_TARGETS

    # Sum of individual component targets
    component_sum = (
        PERFORMANCE_TARGETS["git_clone"]
        + PERFORMANCE_TARGETS["git_extract"]
        + PERFORMANCE_TARGETS["actions_analyzer"]
        + PERFORMANCE_TARGETS["team_analyzer"]
        + PERFORMANCE_TARGETS["strategy_detector"]
        + PERFORMANCE_TARGETS["agents_parallel"]
        + PERFORMANCE_TARGETS["brand_voice_transformer"]
    )

    print(f"\nComponent targets sum: {component_sum}ms ({component_sum / 1000:.1f}s)")
    print(f"Total pipeline target: {PERFORMANCE_TARGETS['total_pipeline']}ms")

    # Component sum should be close to total (within 10% buffer for overhead)
    assert component_sum <= PERFORMANCE_TARGETS["total_pipeline"] * 1.1

    # Individual components should be reasonable
    assert PERFORMANCE_TARGETS["git_clone"] <= 15000  # 15s max
    assert PERFORMANCE_TARGETS["agents_parallel"] <= 45000  # 45s max (parallel execution)
    assert PERFORMANCE_TARGETS["team_analyzer"] <= 10000  # 10s max
