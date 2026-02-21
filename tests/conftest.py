"""Shared pytest fixtures for VibeJudge AI tests."""

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, Mock

import pytest

from src.models.analysis import (
    RepoData,
    SourceFile,
    CommitInfo,
)
from src.models.submission import RepoMeta
from src.models.common import AgentName
from src.models.hackathon import RubricConfig, RubricDimension
from src.models.scores import (
    BugHunterResponse,
    PerformanceResponse,
    InnovationResponse,
    AIDetectionResponse,
    BugHunterEvidence,
    PerformanceEvidence,
    InnovationEvidence,
    AIDetectionEvidence,
)


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
        "overall_score": 8.5,
        "confidence": 0.9,
        "evidence": [],
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
            first_commit_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            last_commit_at=datetime(2024, 2, 1, tzinfo=timezone.utc),
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
                timestamp=datetime(2024, 1, 15, tzinfo=timezone.utc),
                message="Initial commit",
                files_changed=5,
                insertions=100,
                deletions=0,
            ),
            CommitInfo(
                hash="def456ghi789",
                short_hash="def456g",
                author="Jane Smith",
                timestamp=datetime(2024, 1, 20, tzinfo=timezone.utc),
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
        overall_score=8.5,
        confidence=0.9,
        evidence=[
            BugHunterEvidence(
                category="code_quality",
                finding="Well-structured code with clear separation of concerns",
                file="src/main.py",
                line=10,
                severity="info",
            ),
            BugHunterEvidence(
                category="security",
                finding="No SQL injection vulnerabilities detected",
                file="src/api.py",
                line=25,
                severity="info",
            ),
        ],
        strengths=[
            "Clean code structure",
            "Good test coverage",
        ],
        improvements=[
            "Add input validation",
            "Implement rate limiting",
        ],
    )


@pytest.fixture
def sample_performance_response() -> PerformanceResponse:
    """Sample PerformanceAnalyzer agent response."""
    return PerformanceResponse(
        overall_score=7.5,
        confidence=0.85,
        evidence=[
            PerformanceEvidence(
                category="architecture",
                finding="Microservices architecture with clear boundaries",
                file="src/api.py",
                line=1,
                impact="high",
            ),
        ],
        strengths=[
            "Scalable architecture",
            "Good database design",
        ],
        improvements=[
            "Add caching layer",
            "Optimize database queries",
        ],
    )


@pytest.fixture
def sample_innovation_response() -> InnovationResponse:
    """Sample InnovationScorer agent response."""
    return InnovationResponse(
        overall_score=9.0,
        confidence=0.95,
        evidence=[
            InnovationEvidence(
                category="technical_innovation",
                finding="Novel use of AI for automated code review",
                file="src/main.py",
                line=50,
                novelty="high",
            ),
        ],
        strengths=[
            "Innovative approach",
            "Excellent documentation",
        ],
        improvements=[
            "Add more examples",
        ],
    )


@pytest.fixture
def sample_ai_detection_response() -> AIDetectionResponse:
    """Sample AIDetection agent response."""
    return AIDetectionResponse(
        overall_score=8.0,
        confidence=0.88,
        evidence=[
            AIDetectionEvidence(
                dimension="commit_patterns",
                finding="Consistent commit patterns with meaningful messages",
                commit="abc123d",
                indicator="positive",
            ),
        ],
        strengths=[
            "Natural development patterns",
            "Good commit hygiene",
        ],
        improvements=[
            "More granular commits",
        ],
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
        "overall_score": 8.5,
        "confidence": 0.9,
        "evidence": [
            {
                "category": "code_quality",
                "finding": "Well-structured code",
                "file": "src/main.py",
                "line": 10,
                "severity": "info"
            }
        ],
        "strengths": ["Clean code"],
        "improvements": ["Add validation"]
    }"""


def build_performance_json() -> str:
    """Build PerformanceAnalyzer JSON response."""
    return """{
        "overall_score": 7.5,
        "confidence": 0.85,
        "evidence": [
            {
                "category": "architecture",
                "finding": "Good architecture",
                "file": "src/api.py",
                "line": 1,
                "impact": "high"
            }
        ],
        "strengths": ["Scalable"],
        "improvements": ["Add caching"]
    }"""


def build_innovation_json() -> str:
    """Build InnovationScorer JSON response."""
    return """{
        "overall_score": 9.0,
        "confidence": 0.95,
        "evidence": [
            {
                "category": "technical_innovation",
                "finding": "Novel approach",
                "file": "src/main.py",
                "line": 50,
                "novelty": "high"
            }
        ],
        "strengths": ["Innovative"],
        "improvements": ["More examples"]
    }"""


def build_ai_detection_json() -> str:
    """Build AIDetection JSON response."""
    return """{
        "overall_score": 8.0,
        "confidence": 0.88,
        "evidence": [
            {
                "dimension": "commit_patterns",
                "finding": "Good patterns",
                "commit": "abc123d",
                "indicator": "positive"
            }
        ],
        "strengths": ["Natural patterns"],
        "improvements": ["More granular commits"]
    }"""
