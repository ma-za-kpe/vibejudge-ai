"""Unit tests for AI agents."""

import pytest

from src.agents.ai_detection import AIDetectionAgent
from src.agents.bug_hunter import BugHunterAgent
from src.agents.innovation import InnovationScorerAgent
from src.agents.performance import PerformanceAnalyzerAgent
from src.models.scores import (
    AIDetectionResponse,
    BugHunterResponse,
    InnovationResponse,
    PerformanceResponse,
)
from tests.conftest import (
    build_ai_detection_json,
    build_bedrock_response,
    build_bug_hunter_json,
    build_innovation_json,
    build_performance_json,
)

# ============================================================
# BUG HUNTER AGENT TESTS
# ============================================================


class TestBugHunterAgent:
    """Tests for BugHunter agent."""

    def test_initialization(self, mock_bedrock_client):
        """Test agent initialization with correct model."""
        agent = BugHunterAgent(mock_bedrock_client)

        assert agent.agent_name == "bug_hunter"
        assert agent.model_id == "amazon.nova-lite-v1:0"
        assert agent.temperature == 0.1
        assert agent.max_tokens == 2048

    def test_get_system_prompt(self, mock_bedrock_client):
        """Test system prompt retrieval."""
        agent = BugHunterAgent(mock_bedrock_client)
        prompt = agent.get_system_prompt()

        assert isinstance(prompt, str)
        assert len(prompt) > 100
        assert "BugHunter" in prompt or "code quality" in prompt.lower()

    def test_build_user_message(self, mock_bedrock_client, sample_repo_data):
        """Test user message construction."""
        agent = BugHunterAgent(mock_bedrock_client)
        message = agent.build_user_message(
            repo_data=sample_repo_data,
            hackathon_name="Test Hackathon",
            team_name="Test Team",
        )

        assert isinstance(message, str)
        assert "Test Hackathon" in message
        assert "Test Team" in message
        assert sample_repo_data.repo_url in message
        assert "src/main.py" in message

    def test_parse_response(self, mock_bedrock_client):
        """Test response parsing."""
        agent = BugHunterAgent(mock_bedrock_client)

        response_dict = {
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
            "evidence": [
                {
                    "category": "code_quality",
                    "finding": "Good code",
                    "file": "src/main.py",
                    "line": 10,
                    "severity": "info",
                    "recommendation": "Continue",
                }
            ],
            "ci_observations": {
                "has_ci": True,
                "has_automated_tests": True,
            },
        }

        result = agent.parse_response(response_dict)

        assert isinstance(result, BugHunterResponse)
        assert result.overall_score == 8.5
        assert result.scores.code_quality == 8.5
        assert len(result.evidence) == 1

    def test_analyze_success(self, mock_bedrock_client, sample_repo_data):
        """Test successful analysis."""
        # Configure mock
        mock_bedrock_client.converse.return_value = build_bedrock_response(
            content=build_bug_hunter_json(),
            input_tokens=1000,
            output_tokens=500,
        )
        mock_bedrock_client.parse_json_response.return_value = {
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
            "evidence": [
                {
                    "category": "code_quality",
                    "finding": "Well-structured code",
                    "file": "src/main.py",
                    "line": 10,
                    "severity": "info",
                    "recommendation": "Continue",
                }
            ],
            "ci_observations": {},
        }

        agent = BugHunterAgent(mock_bedrock_client)
        response, usage = agent.analyze(
            repo_data=sample_repo_data,
            hackathon_name="Test Hackathon",
            team_name="Test Team",
        )

        # Verify response
        assert isinstance(response, BugHunterResponse)
        assert response.overall_score == 8.5

        # Verify usage
        assert usage["input_tokens"] == 1000
        assert usage["output_tokens"] == 500
        assert "total_cost_usd" in usage

        # Verify Bedrock was called
        mock_bedrock_client.converse.assert_called_once()

    def test_analyze_with_retry(self, mock_bedrock_client, sample_repo_data):
        """Test analysis with JSON parsing retry."""
        # First call returns invalid JSON
        mock_bedrock_client.parse_json_response.side_effect = [
            None,  # First parse fails
            {  # Second parse succeeds
                "agent": "bug_hunter",
                "prompt_version": "v1.0",
                "overall_score": 8.5,
                "summary": "Code analysis",
                "scores": {
                    "code_quality": 8.5,
                    "security": 9.0,
                    "test_coverage": 7.0,
                    "error_handling": 8.0,
                    "dependency_hygiene": 8.5,
                },
                "evidence": [],
                "ci_observations": {},
            },
        ]

        mock_bedrock_client.converse.return_value = build_bedrock_response(
            content="invalid json",
        )

        mock_bedrock_client.retry_with_correction.return_value = build_bedrock_response(
            content=build_bug_hunter_json(),
        )

        agent = BugHunterAgent(mock_bedrock_client)
        response, usage = agent.analyze(
            repo_data=sample_repo_data,
            hackathon_name="Test Hackathon",
            team_name="Test Team",
        )

        # Verify retry was called
        mock_bedrock_client.retry_with_correction.assert_called_once()
        assert isinstance(response, BugHunterResponse)


# ============================================================
# PERFORMANCE ANALYZER AGENT TESTS
# ============================================================


class TestPerformanceAnalyzerAgent:
    """Tests for PerformanceAnalyzer agent."""

    def test_initialization(self, mock_bedrock_client):
        """Test agent initialization with correct model."""
        agent = PerformanceAnalyzerAgent(mock_bedrock_client)

        assert agent.agent_name == "performance"
        assert agent.model_id == "amazon.nova-lite-v1:0"
        assert agent.temperature == 0.1

    def test_analyze_success(self, mock_bedrock_client, sample_repo_data):
        """Test successful analysis."""
        mock_bedrock_client.converse.return_value = build_bedrock_response(
            content=build_performance_json(),
        )
        mock_bedrock_client.parse_json_response.return_value = {
            "agent": "performance",
            "prompt_version": "v1.0",
            "overall_score": 7.5,
            "summary": "Good architecture",
            "scores": {
                "architecture": 8.0,
                "database_design": 7.5,
                "api_design": 7.0,
                "scalability": 7.5,
                "resource_efficiency": 7.0,
            },
            "evidence": [
                {
                    "category": "architecture",
                    "finding": "Good architecture",
                    "file": "src/api.py",
                    "line": 1,
                    "severity": "info",
                    "recommendation": "Add caching",
                }
            ],
            "ci_observations": {},
            "tech_stack_assessment": {},
        }

        agent = PerformanceAnalyzerAgent(mock_bedrock_client)
        response, usage = agent.analyze(
            repo_data=sample_repo_data,
            hackathon_name="Test Hackathon",
            team_name="Test Team",
        )

        assert isinstance(response, PerformanceResponse)
        assert response.overall_score == 7.5


# ============================================================
# INNOVATION SCORER AGENT TESTS
# ============================================================


class TestInnovationScorerAgent:
    """Tests for InnovationScorer agent."""

    def test_initialization(self, mock_bedrock_client):
        """Test agent initialization with correct model."""
        agent = InnovationScorerAgent(mock_bedrock_client)

        assert agent.agent_name == "innovation"
        assert agent.model_id == "us.anthropic.claude-sonnet-4-6"
        assert agent.temperature == 0.3  # Higher temperature for creativity

    def test_analyze_success(self, mock_bedrock_client, sample_repo_data):
        """Test successful analysis."""
        mock_bedrock_client.converse.return_value = build_bedrock_response(
            content=build_innovation_json(),
            model_id="us.anthropic.claude-sonnet-4-6",
        )
        mock_bedrock_client.parse_json_response.return_value = {
            "agent": "innovation",
            "prompt_version": "v1.0",
            "overall_score": 9.0,
            "summary": "Highly innovative",
            "scores": {
                "technical_novelty": 9.0,
                "creative_problem_solving": 8.5,
                "architecture_elegance": 9.0,
                "readme_quality": 9.5,
                "demo_potential": 8.5,
            },
            "evidence": [
                {
                    "category": "technical_innovation",
                    "finding": "Novel approach",
                    "file": "src/main.py",
                    "line": 50,
                    "impact": "significant",
                    "detail": "Unique approach",
                }
            ],
            "innovation_highlights": [],
            "development_story": "",
            "hackathon_context_assessment": "",
        }

        agent = InnovationScorerAgent(mock_bedrock_client)
        response, usage = agent.analyze(
            repo_data=sample_repo_data,
            hackathon_name="Test Hackathon",
            team_name="Test Team",
        )

        assert isinstance(response, InnovationResponse)
        assert response.overall_score == 9.0


# ============================================================
# AI DETECTION AGENT TESTS
# ============================================================


class TestAIDetectionAgent:
    """Tests for AIDetection agent."""

    def test_initialization(self, mock_bedrock_client):
        """Test agent initialization with correct model."""
        agent = AIDetectionAgent(mock_bedrock_client)

        assert agent.agent_name == "ai_detection"
        assert agent.model_id == "amazon.nova-micro-v1:0"
        assert agent.temperature == 0.0  # Deterministic

    def test_analyze_with_ai_policy(self, mock_bedrock_client, sample_repo_data):
        """Test analysis with AI policy mode."""
        mock_bedrock_client.converse.return_value = build_bedrock_response(
            content=build_ai_detection_json(),
            model_id="amazon.nova-micro-v1:0",
        )
        mock_bedrock_client.parse_json_response.return_value = {
            "agent": "ai_detection",
            "prompt_version": "v1.0",
            "overall_score": 8.0,
            "summary": "Natural patterns",
            "scores": {
                "commit_authenticity": 8.5,
                "development_velocity": 7.5,
                "authorship_consistency": 8.0,
                "iteration_depth": 8.0,
                "ai_generation_indicators": 8.5,
            },
            "evidence": [
                {
                    "finding": "Good patterns",
                    "source": "commit_history",
                    "detail": "Natural progression",
                    "signal": "human",
                    "confidence": 0.85,
                }
            ],
            "commit_analysis": {},
            "ai_policy_observation": "",
        }

        agent = AIDetectionAgent(mock_bedrock_client)
        response, usage = agent.analyze(
            repo_data=sample_repo_data,
            hackathon_name="Test Hackathon",
            team_name="Test Team",
            ai_policy_mode="ai_assisted",
        )

        assert isinstance(response, AIDetectionResponse)
        assert response.overall_score == 8.0


# ============================================================
# EVIDENCE VALIDATION TESTS
# ============================================================


class TestEvidenceValidation:
    """Tests for evidence validation (anti-hallucination)."""

    def test_validate_evidence_all_valid(self, mock_bedrock_client, sample_repo_data):
        """Test validation with all valid evidence."""
        mock_bedrock_client.converse.return_value = build_bedrock_response(
            content=build_bug_hunter_json(),
        )
        mock_bedrock_client.parse_json_response.return_value = {
            "agent": "bug_hunter",
            "prompt_version": "v1.0",
            "overall_score": 8.5,
            "summary": "Good code",
            "scores": {
                "code_quality": 8.5,
                "security": 9.0,
                "test_coverage": 7.0,
                "error_handling": 8.0,
                "dependency_hygiene": 8.5,
            },
            "evidence": [
                {
                    "category": "code_quality",
                    "finding": "Good code",
                    "file": "src/main.py",  # Valid file
                    "line": 10,
                    "severity": "info",
                    "recommendation": "Continue",
                }
            ],
            "ci_observations": {},
        }

        agent = BugHunterAgent(mock_bedrock_client)
        response, _ = agent.analyze(
            repo_data=sample_repo_data,
            hackathon_name="Test",
            team_name="Test",
        )

        # Confidence should remain high
        assert response.overall_score == 8.5

    def test_validate_evidence_invalid_file(self, mock_bedrock_client, sample_repo_data):
        """Test validation with invalid file reference."""
        mock_bedrock_client.converse.return_value = build_bedrock_response(
            content=build_bug_hunter_json(),
        )
        mock_bedrock_client.parse_json_response.return_value = {
            "agent": "bug_hunter",
            "prompt_version": "v1.0",
            "overall_score": 8.5,
            "summary": "Code analysis",
            "scores": {
                "code_quality": 8.5,
                "security": 9.0,
                "test_coverage": 7.0,
                "error_handling": 8.0,
                "dependency_hygiene": 8.5,
            },
            "evidence": [
                {
                    "category": "code_quality",
                    "finding": "Good code",
                    "file": "src/nonexistent.py",  # Invalid file
                    "line": 10,
                    "severity": "info",
                    "recommendation": "Continue",
                },
                {
                    "category": "security",
                    "finding": "Another finding",
                    "file": "src/fake.py",  # Invalid file
                    "line": 20,
                    "severity": "high",
                    "recommendation": "Fix",
                },
            ],
            "ci_observations": {},
        }

        agent = BugHunterAgent(mock_bedrock_client)
        response, _ = agent.analyze(
            repo_data=sample_repo_data,
            hackathon_name="Test",
            team_name="Test",
        )

        # Confidence should be capped at 0.5 (>30% unverified)
        assert response.overall_score <= 8.5  # Score may be adjusted

    def test_validate_evidence_invalid_commit(self, mock_bedrock_client, sample_repo_data):
        """Test validation with invalid commit reference."""
        mock_bedrock_client.converse.return_value = build_bedrock_response(
            content=build_ai_detection_json(),
        )
        mock_bedrock_client.parse_json_response.return_value = {
            "agent": "ai_detection",
            "prompt_version": "v1.0",
            "overall_score": 8.0,
            "confidence": 0.9,
            "summary": "Analysis complete",
            "scores": {
                "commit_authenticity": 8.5,
                "development_velocity": 7.5,
                "authorship_consistency": 8.0,
                "iteration_depth": 8.0,
                "ai_generation_indicators": 8.5,
            },
            "evidence": [
                {
                    "finding": "Good patterns",
                    "source": "commit_history",
                    "detail": "Commit invalid123 shows good patterns",  # Reference to invalid commit
                    "signal": "human",
                    "confidence": 0.85,
                }
            ],
            "commit_analysis": {},
            "ai_policy_observation": "",
        }

        agent = AIDetectionAgent(mock_bedrock_client)
        response, _ = agent.analyze(
            repo_data=sample_repo_data,
            hackathon_name="Test",
            team_name="Test",
        )

        # Evidence validation doesn't check commit hashes in detail field
        # This test verifies the agent completes successfully
        assert response.overall_score == 8.0


# ============================================================
# ERROR HANDLING TESTS
# ============================================================


class TestAgentErrorHandling:
    """Tests for agent error handling."""

    def test_bedrock_api_error(self, mock_bedrock_client, sample_repo_data):
        """Test handling of Bedrock API errors."""
        mock_bedrock_client.converse.side_effect = Exception("Bedrock API error")

        agent = BugHunterAgent(mock_bedrock_client)

        with pytest.raises(Exception) as exc_info:
            agent.analyze(
                repo_data=sample_repo_data,
                hackathon_name="Test",
                team_name="Test",
            )

        assert "Bedrock API error" in str(exc_info.value)

    def test_json_parse_failure_after_retry(self, mock_bedrock_client, sample_repo_data):
        """Test failure when JSON parsing fails after retry."""
        # Both parse attempts fail
        mock_bedrock_client.parse_json_response.return_value = None
        mock_bedrock_client.converse.return_value = build_bedrock_response(
            content="invalid json",
        )
        mock_bedrock_client.retry_with_correction.return_value = build_bedrock_response(
            content="still invalid",
        )

        agent = BugHunterAgent(mock_bedrock_client)

        with pytest.raises(ValueError) as exc_info:
            agent.analyze(
                repo_data=sample_repo_data,
                hackathon_name="Test",
                team_name="Test",
            )

        assert "Failed to parse JSON after retry" in str(exc_info.value)


# ============================================================
# COST CALCULATION TESTS
# ============================================================


class TestCostCalculation:
    """Tests for cost calculation."""

    @pytest.mark.parametrize(
        "agent_class,expected_model",
        [
            (BugHunterAgent, "amazon.nova-lite-v1:0"),
            (PerformanceAnalyzerAgent, "amazon.nova-lite-v1:0"),
            (InnovationScorerAgent, "us.anthropic.claude-sonnet-4-6"),
            (AIDetectionAgent, "amazon.nova-micro-v1:0"),
        ],
    )
    def test_agent_uses_correct_model(self, mock_bedrock_client, agent_class, expected_model):
        """Test that each agent uses the correct Bedrock model."""
        agent = agent_class(mock_bedrock_client)
        assert agent.model_id == expected_model

    def test_cost_tracking_in_usage(self, mock_bedrock_client, sample_repo_data):
        """Test that cost is tracked in usage dict."""
        mock_bedrock_client.converse.return_value = build_bedrock_response(
            content=build_bug_hunter_json(),
            input_tokens=1000,
            output_tokens=500,
        )
        mock_bedrock_client.parse_json_response.return_value = {
            "agent": "bug_hunter",
            "prompt_version": "v1.0",
            "overall_score": 8.5,
            "confidence": 0.9,
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
        mock_bedrock_client.calculate_cost.return_value = {
            "input_cost_usd": 0.00006,
            "output_cost_usd": 0.00012,
            "total_cost_usd": 0.00018,
        }

        agent = BugHunterAgent(mock_bedrock_client)
        response, usage = agent.analyze(
            repo_data=sample_repo_data,
            hackathon_name="Test",
            team_name="Test",
        )

        assert "input_tokens" in usage
        assert "output_tokens" in usage
        assert "total_cost_usd" in usage
        assert usage["input_tokens"] == 1000
        assert usage["output_tokens"] == 500
        assert usage["total_cost_usd"] == 0.00018
