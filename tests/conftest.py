"""Shared pytest fixtures for VibeJudge AI tests."""

import os
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

import boto3
import pytest
from moto import mock_aws

from src.models.analysis import (
    CommitInfo,
    RepoData,
    SourceFile,
)
from src.models.common import AgentName
from src.models.hackathon import RubricConfig, RubricDimension
from src.models.scores import (
    AIDetectionEvidence,
    AIDetectionResponse,
    AIDetectionScores,
    BugHunterEvidence,
    BugHunterResponse,
    BugHunterScores,
    CIObservations,
    CommitAnalysis,
    InnovationEvidence,
    InnovationResponse,
    InnovationScores,
    PerformanceCIObservations,
    PerformanceEvidence,
    PerformanceResponse,
    PerformanceScores,
    TechStackAssessment,
)
from src.models.submission import RepoMeta

# ============================================================
# PYTEST CONFIGURATION HOOKS
# ============================================================


def pytest_configure(config):
    """Set up test environment before any imports."""
    # Set a valid test GitHub token if not already set
    # This runs before collection, so it's available for all imports
    if "GITHUB_TOKEN" not in os.environ:
        os.environ["GITHUB_TOKEN"] = "ghp_test_token_for_automated_tests_1234567890"


# ============================================================
# ENVIRONMENT SETUP
# ============================================================


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables before any imports."""
    # Set a valid test GitHub token if not already set
    if "GITHUB_TOKEN" not in os.environ:
        os.environ["GITHUB_TOKEN"] = "ghp_test_token_for_automated_tests_1234567890"
    yield
    # Cleanup is optional since this is session-scoped


# ============================================================
# MOCK BEDROCK CLIENT
# ============================================================


@pytest.fixture
def mock_bedrock_client():
    """Mock Bedrock client with configurable responses."""
    client = MagicMock()

    # Default successful response
    client.converse.return_value = {
        "content": '{"overall_score": 8.5, "confidence": 0.9, "evidence": []}',
        "usage": {
            "input_tokens": 1000,
            "output_tokens": 500,
            "total_tokens": 1500,
        },
        "stop_reason": "end_turn",
        "latency_ms": 1200,
        "model_id": "amazon.nova-lite-v1:0",
    }

    client.calculate_cost.return_value = {
        "input_cost_usd": 0.00006,
        "output_cost_usd": 0.00012,
        "total_cost_usd": 0.00018,
    }

    client.parse_json_response.return_value = {
        "agent": "bug_hunter",
        "prompt_version": "v1.0",
        "overall_score": 8.5,
        "summary": "Well-structured code",
        "scores": {
            "code_quality": 8.5,
            "security": 9.0,
            "test_coverage": 7.0,
            "error_handling": 8.0,
            "dependency_hygiene": 8.5,
        },
        "evidence": [],
        "ci_observations": {},
    }

    return client


# ============================================================
# SAMPLE REPO DATA
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
            SourceFile(
                path="src/api.py",
                language="Python",
                lines=200,
                content="from fastapi import FastAPI\napp = FastAPI()\n",
            ),
            SourceFile(
                path="tests/test_main.py",
                language="Python",
                lines=50,
                content="def test_main():\n    assert True\n",
            ),
        ],
        commit_history=[
            CommitInfo(
                hash="abc123def456",
                short_hash="abc123d",
                author="John Doe",
                timestamp=datetime(2024, 1, 15, tzinfo=UTC),
                message="Initial commit",
                files_changed=5,
                insertions=100,
                deletions=0,
            ),
            CommitInfo(
                hash="def456ghi789",
                short_hash="def456g",
                author="Jane Smith",
                timestamp=datetime(2024, 1, 20, tzinfo=UTC),
                message="Add API endpoints",
                files_changed=3,
                insertions=200,
                deletions=10,
            ),
        ],
        readme_content="# Test Project\n\nThis is a test project for hackathon judging.",
        file_tree="src/\n  main.py\n  api.py\ntests/\n  test_main.py\n",
        workflow_definitions=["name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest"],
    )


# ============================================================
# SAMPLE AGENT RESPONSES
# ============================================================


@pytest.fixture
def sample_bug_hunter_response() -> BugHunterResponse:
    """Sample BugHunter agent response."""
    return BugHunterResponse(
        agent="bug_hunter",
        prompt_version="v1.0",
        overall_score=8.5,
        confidence=0.9,
        summary="Well-structured code with good security practices",
        scores=BugHunterScores(
            code_quality=8.5,
            security=9.0,
            test_coverage=7.0,
            error_handling=8.0,
            dependency_hygiene=8.5,
        ),
        evidence=[
            BugHunterEvidence(
                category="code_quality",
                finding="Well-structured code with clear separation of concerns",
                file="src/main.py",
                line=10,
                severity="info",
                recommendation="Continue following these patterns",
            ),
            BugHunterEvidence(
                category="security",
                finding="No SQL injection vulnerabilities detected",
                file="src/api.py",
                line=25,
                severity="info",
                recommendation="Maintain input validation",
            ),
        ],
        ci_observations=CIObservations(
            has_ci=True,
            has_automated_tests=True,
            has_linting=False,
            has_security_scanning=False,
            build_success_rate=0.9,
        ),
    )


@pytest.fixture
def sample_performance_response() -> PerformanceResponse:
    """Sample PerformanceAnalyzer agent response."""
    return PerformanceResponse(
        agent="performance",
        prompt_version="v1.0",
        overall_score=7.5,
        confidence=0.85,
        summary="Scalable architecture with room for optimization",
        scores=PerformanceScores(
            architecture=8.0,
            database_design=7.5,
            api_design=7.0,
            scalability=7.5,
            resource_efficiency=7.0,
        ),
        evidence=[
            PerformanceEvidence(
                category="architecture",
                finding="Microservices architecture with clear boundaries",
                file="src/api.py",
                line=1,
                severity="info",
                recommendation="Consider adding caching layer",
            ),
        ],
        ci_observations=PerformanceCIObservations(
            has_ci=True,
            deployment_sophistication="intermediate",
            infrastructure_as_code=True,
        ),
        tech_stack_assessment=TechStackAssessment(
            technologies_identified=["Python", "FastAPI", "PostgreSQL"],
            stack_appropriateness="Well-suited for the use case",
            notable_choices="FastAPI for async performance",
        ),
    )


@pytest.fixture
def sample_innovation_response() -> InnovationResponse:
    """Sample InnovationScorer agent response."""
    return InnovationResponse(
        agent="innovation",
        prompt_version="v1.0",
        overall_score=9.0,
        confidence=0.95,
        summary="Highly innovative approach with excellent documentation",
        scores=InnovationScores(
            technical_novelty=9.0,
            creative_problem_solving=8.5,
            architecture_elegance=9.0,
            readme_quality=9.5,
            demo_potential=8.5,
        ),
        evidence=[
            InnovationEvidence(
                category="technical_innovation",
                finding="Novel use of AI for automated code review",
                file="src/main.py",
                line=50,
                impact="significant",
                detail="Unique approach to multi-agent coordination",
            ),
        ],
        innovation_highlights=[
            "Novel AI agent architecture",
            "Excellent documentation",
            "Strong demo potential",
        ],
        development_story="Team showed consistent progress with iterative improvements",
        hackathon_context_assessment="Well-suited for hackathon judging use case",
    )


@pytest.fixture
def sample_ai_detection_response() -> AIDetectionResponse:
    """Sample AIDetection agent response."""
    return AIDetectionResponse(
        agent="ai_detection",
        prompt_version="v1.0",
        overall_score=8.0,
        confidence=0.88,
        summary="Natural development patterns with good commit hygiene",
        scores=AIDetectionScores(
            commit_authenticity=8.5,
            development_velocity=7.5,
            authorship_consistency=8.0,
            iteration_depth=8.0,
            ai_generation_indicators=8.5,
        ),
        evidence=[
            AIDetectionEvidence(
                finding="Consistent commit patterns with meaningful messages",
                source="commit_history",
                detail="Commits show natural progression",
                signal="human",
                confidence=0.85,
            ),
        ],
        commit_analysis=CommitAnalysis(
            total_commits=50,
            avg_lines_per_commit=120.0,
            largest_commit_lines=500,
            commit_frequency_pattern="steady",
            meaningful_message_ratio=0.9,
            fix_commit_count=5,
            refactor_commit_count=3,
        ),
        ai_policy_observation="Development shows natural human patterns",
    )


# ============================================================
# SAMPLE RUBRIC
# ============================================================


@pytest.fixture
def sample_rubric() -> RubricConfig:
    """Sample rubric configuration."""
    return RubricConfig(
        dimensions=[
            RubricDimension(
                name="Code Quality",
                agent=AgentName.BUG_HUNTER,
                weight=0.3,
            ),
            RubricDimension(
                name="Architecture",
                agent=AgentName.PERFORMANCE,
                weight=0.3,
            ),
            RubricDimension(
                name="Innovation",
                agent=AgentName.INNOVATION,
                weight=0.3,
            ),
            RubricDimension(
                name="Authenticity",
                agent=AgentName.AI_DETECTION,
                weight=0.1,
            ),
        ]
    )


# ============================================================
# BEDROCK RESPONSE BUILDERS
# ============================================================


def build_bedrock_response(
    content: str,
    input_tokens: int = 1000,
    output_tokens: int = 500,
    model_id: str = "amazon.nova-lite-v1:0",
) -> dict[str, Any]:
    """Build a mock Bedrock API response.

    Args:
        content: Response content (JSON string)
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        model_id: Bedrock model ID

    Returns:
        Mock Bedrock response dict
    """
    return {
        "content": content,
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        },
        "stop_reason": "end_turn",
        "latency_ms": 1200,
        "model_id": model_id,
    }


def build_bug_hunter_json() -> str:
    """Build BugHunter JSON response."""
    return """{
        "agent": "bug_hunter",
        "prompt_version": "v1.0",
        "overall_score": 8.5,
        "summary": "Well-structured code with good practices",
        "scores": {
            "code_quality": 8.5,
            "security": 9.0,
            "test_coverage": 7.0,
            "error_handling": 8.0,
            "dependency_hygiene": 8.5
        },
        "evidence": [
            {
                "category": "code_quality",
                "finding": "Well-structured code",
                "file": "src/main.py",
                "line": 10,
                "severity": "info",
                "recommendation": "Continue following these patterns"
            }
        ],
        "ci_observations": {
            "has_ci": true,
            "has_automated_tests": true,
            "has_linting": false,
            "has_security_scanning": false,
            "build_success_rate": 0.9
        }
    }"""


def build_performance_json() -> str:
    """Build PerformanceAnalyzer JSON response."""
    return """{
        "agent": "performance",
        "prompt_version": "v1.0",
        "overall_score": 7.5,
        "summary": "Scalable architecture with optimization opportunities",
        "scores": {
            "architecture": 8.0,
            "database_design": 7.5,
            "api_design": 7.0,
            "scalability": 7.5,
            "resource_efficiency": 7.0
        },
        "evidence": [
            {
                "category": "architecture",
                "finding": "Good architecture",
                "file": "src/api.py",
                "line": 1,
                "severity": "info",
                "recommendation": "Add caching layer"
            }
        ],
        "ci_observations": {
            "has_ci": true,
            "deployment_sophistication": "intermediate",
            "infrastructure_as_code": true
        },
        "tech_stack_assessment": {
            "technologies_identified": ["Python", "FastAPI"],
            "stack_appropriateness": "Well-suited",
            "notable_choices": "FastAPI for async"
        }
    }"""


def build_innovation_json() -> str:
    """Build InnovationScorer JSON response."""
    return """{
        "agent": "innovation",
        "prompt_version": "v1.0",
        "overall_score": 9.0,
        "summary": "Highly innovative with excellent documentation",
        "scores": {
            "technical_novelty": 9.0,
            "creative_problem_solving": 8.5,
            "architecture_elegance": 9.0,
            "readme_quality": 9.5,
            "demo_potential": 8.5
        },
        "evidence": [
            {
                "category": "technical_innovation",
                "finding": "Novel approach",
                "file": "src/main.py",
                "line": 50,
                "impact": "significant",
                "detail": "Unique multi-agent coordination"
            }
        ],
        "innovation_highlights": ["Novel architecture", "Excellent docs"],
        "development_story": "Consistent iterative progress",
        "hackathon_context_assessment": "Well-suited for judging"
    }"""


def build_ai_detection_json() -> str:
    """Build AIDetection JSON response."""
    return """{
        "agent": "ai_detection",
        "prompt_version": "v1.0",
        "overall_score": 8.0,
        "summary": "Natural development patterns observed",
        "scores": {
            "commit_authenticity": 8.5,
            "development_velocity": 7.5,
            "authorship_consistency": 8.0,
            "iteration_depth": 8.0,
            "ai_generation_indicators": 8.5
        },
        "evidence": [
            {
                "finding": "Good patterns",
                "source": "commit_history",
                "detail": "Natural progression",
                "signal": "human",
                "confidence": 0.85
            }
        ],
        "commit_analysis": {
            "total_commits": 50,
            "avg_lines_per_commit": 120.0,
            "largest_commit_lines": 500,
            "commit_frequency_pattern": "steady",
            "meaningful_message_ratio": 0.9,
            "fix_commit_count": 5,
            "refactor_commit_count": 3
        },
        "ai_policy_observation": "Natural human patterns"
    }"""


# ============================================================
# MOCK RESPONSE HELPERS FOR ORCHESTRATOR TESTS
# ============================================================


def build_complete_bug_hunter_dict(overall_score: float = 8.5, confidence: float = 0.9) -> dict:
    """Build complete BugHunter response dict for mocking."""
    return {
        "agent": "bug_hunter",
        "prompt_version": "v1.0",
        "overall_score": overall_score,
        "confidence": confidence,
        "summary": "Code analysis complete",
        "scores": {
            "code_quality": overall_score,
            "security": overall_score,
            "test_coverage": overall_score,
            "error_handling": overall_score,
            "dependency_hygiene": overall_score,
        },
        "evidence": [],
        "ci_observations": {},
    }


def build_complete_performance_dict(overall_score: float = 7.5, confidence: float = 0.85) -> dict:
    """Build complete PerformanceAnalyzer response dict for mocking."""
    return {
        "agent": "performance",
        "prompt_version": "v1.0",
        "overall_score": overall_score,
        "confidence": confidence,
        "summary": "Performance analysis complete",
        "scores": {
            "architecture": overall_score,
            "database_design": overall_score,
            "api_design": overall_score,
            "scalability": overall_score,
            "resource_efficiency": overall_score,
        },
        "evidence": [],
        "ci_observations": {},
        "tech_stack_assessment": {},
    }


def build_complete_innovation_dict(overall_score: float = 9.0, confidence: float = 0.95) -> dict:
    """Build complete InnovationScorer response dict for mocking."""
    return {
        "agent": "innovation",
        "prompt_version": "v1.0",
        "overall_score": overall_score,
        "confidence": confidence,
        "summary": "Innovation analysis complete",
        "scores": {
            "technical_novelty": overall_score,
            "creative_problem_solving": overall_score,
            "architecture_elegance": overall_score,
            "readme_quality": overall_score,
            "demo_potential": overall_score,
        },
        "evidence": [],
        "innovation_highlights": [],
        "development_story": "",
        "hackathon_context_assessment": "",
    }


def build_complete_ai_detection_dict(overall_score: float = 8.0, confidence: float = 0.88) -> dict:
    """Build complete AIDetection response dict for mocking."""
    return {
        "agent": "ai_detection",
        "prompt_version": "v1.0",
        "overall_score": overall_score,
        "confidence": confidence,
        "summary": "AI detection analysis complete",
        "scores": {
            "commit_authenticity": overall_score,
            "development_velocity": overall_score,
            "authorship_consistency": overall_score,
            "iteration_depth": overall_score,
            "ai_generation_indicators": overall_score,
        },
        "evidence": [],
        "commit_analysis": {},
        "ai_policy_observation": "",
    }


# ============================================================
# DYNAMODB HELPER FIXTURE
# ============================================================


@pytest.fixture
def dynamodb_helper():
    """Create a mock DynamoDB helper for testing."""
    with mock_aws():
        # Create mock DynamoDB table
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName="VibeJudgeTable",
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
                {"AttributeName": "GSI1PK", "AttributeType": "S"},
                {"AttributeName": "GSI1SK", "AttributeType": "S"},
                {"AttributeName": "GSI2PK", "AttributeType": "S"},
                {"AttributeName": "GSI2SK", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "GSI1",
                    "KeySchema": [
                        {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                        {"AttributeName": "GSI1SK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {
                        "ReadCapacityUnits": 5,
                        "WriteCapacityUnits": 5,
                    },
                },
                {
                    "IndexName": "GSI2",
                    "KeySchema": [
                        {"AttributeName": "GSI2PK", "KeyType": "HASH"},
                        {"AttributeName": "GSI2SK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {
                        "ReadCapacityUnits": 5,
                        "WriteCapacityUnits": 5,
                    },
                },
            ],
            BillingMode="PROVISIONED",
            ProvisionedThroughput={
                "ReadCapacityUnits": 5,
                "WriteCapacityUnits": 5,
            },
        )

        # Import and create DynamoDBHelper
        from src.utils.dynamo import DynamoDBHelper

        helper = DynamoDBHelper(table_name="VibeJudgeTable")
        yield helper
