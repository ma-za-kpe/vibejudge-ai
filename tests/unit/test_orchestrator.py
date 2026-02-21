"""Unit tests for analysis orchestrator."""

import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from src.analysis.orchestrator import AnalysisOrchestrator
from src.models.common import AgentName, Recommendation
from tests.conftest import (
    build_bedrock_response,
    build_bug_hunter_json,
    build_performance_json,
    build_innovation_json,
    build_ai_detection_json,
)


# ============================================================
# ORCHESTRATOR INITIALIZATION TESTS
# ============================================================

class TestOrchestratorInitialization:
    """Tests for orchestrator initialization."""
    
    def test_initialization_with_default_client(self):
        """Test orchestrator initialization with default Bedrock client."""
        orchestrator = AnalysisOrchestrator()
        
        assert orchestrator.bedrock is not None
        assert orchestrator.cost_tracker is not None
        assert len(orchestrator.agents) == 4
        assert AgentName.BUG_HUNTER in orchestrator.agents
        assert AgentName.PERFORMANCE in orchestrator.agents
        assert AgentName.INNOVATION in orchestrator.agents
        assert AgentName.AI_DETECTION in orchestrator.agents
    
    def test_initialization_with_custom_client(self, mock_bedrock_client):
        """Test orchestrator initialization with custom Bedrock client."""
        orchestrator = AnalysisOrchestrator(bedrock_client=mock_bedrock_client)
        
        assert orchestrator.bedrock == mock_bedrock_client


# ============================================================
# PARALLEL EXECUTION TESTS
# ============================================================

class TestParallelExecution:
    """Tests for parallel agent execution."""
    
    @pytest.mark.asyncio
    async def test_all_agents_run_in_parallel(
        self,
        mock_bedrock_client,
        sample_repo_data,
        sample_rubric,
    ):
        """Test that all agents run in parallel with asyncio.gather()."""
        # Configure mock responses for each agent
        mock_bedrock_client.converse.side_effect = [
            build_bedrock_response(build_bug_hunter_json()),
            build_bedrock_response(build_performance_json()),
            build_bedrock_response(build_innovation_json()),
            build_bedrock_response(build_ai_detection_json()),
        ]
        
        mock_bedrock_client.parse_json_response.side_effect = [
            {
                "overall_score": 8.5,
                "confidence": 0.9,
                "evidence": [],
                "strengths": ["Clean code"],
                "improvements": ["Add tests"],
            },
            {
                "overall_score": 7.5,
                "confidence": 0.85,
                "evidence": [],
                "strengths": ["Scalable"],
                "improvements": ["Add caching"],
            },
            {
                "overall_score": 9.0,
                "confidence": 0.95,
                "evidence": [],
                "strengths": ["Innovative"],
                "improvements": ["More examples"],
            },
            {
                "overall_score": 8.0,
                "confidence": 0.88,
                "evidence": [],
                "strengths": ["Natural patterns"],
                "improvements": ["More commits"],
            },
        ]
        
        orchestrator = AnalysisOrchestrator(bedrock_client=mock_bedrock_client)
        
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
        
        # Verify all agents completed
        assert len(result["agent_responses"]) == 4
        assert AgentName.BUG_HUNTER in result["agent_responses"]
        assert AgentName.PERFORMANCE in result["agent_responses"]
        assert AgentName.INNOVATION in result["agent_responses"]
        assert AgentName.AI_DETECTION in result["agent_responses"]
        
        # Verify Bedrock was called 4 times (once per agent)
        assert mock_bedrock_client.converse.call_count == 4
    
    @pytest.mark.asyncio
    async def test_subset_of_agents(
        self,
        mock_bedrock_client,
        sample_repo_data,
        sample_rubric,
    ):
        """Test running only a subset of agents."""
        mock_bedrock_client.converse.side_effect = [
            build_bedrock_response(build_bug_hunter_json()),
            build_bedrock_response(build_performance_json()),
        ]
        
        mock_bedrock_client.parse_json_response.side_effect = [
            {
                "overall_score": 8.5,
                "confidence": 0.9,
                "evidence": [],
                "strengths": [],
                "improvements": [],
            },
            {
                "overall_score": 7.5,
                "confidence": 0.85,
                "evidence": [],
                "strengths": [],
                "improvements": [],
            },
        ]
        
        orchestrator = AnalysisOrchestrator(bedrock_client=mock_bedrock_client)
        
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
            ],
        )
        
        # Only 2 agents should have run
        assert len(result["agent_responses"]) == 2
        assert mock_bedrock_client.converse.call_count == 2


# ============================================================
# GRACEFUL DEGRADATION TESTS
# ============================================================

class TestGracefulDegradation:
    """Tests for graceful degradation when agents fail."""
    
    @pytest.mark.asyncio
    async def test_one_agent_fails_others_continue(
        self,
        mock_bedrock_client,
        sample_repo_data,
        sample_rubric,
    ):
        """Test that if one agent fails, others continue."""
        # BugHunter fails, others succeed
        mock_bedrock_client.converse.side_effect = [
            Exception("BugHunter failed"),  # BugHunter fails
            build_bedrock_response(build_performance_json()),
            build_bedrock_response(build_innovation_json()),
            build_bedrock_response(build_ai_detection_json()),
        ]
        
        mock_bedrock_client.parse_json_response.side_effect = [
            {
                "overall_score": 7.5,
                "confidence": 0.85,
                "evidence": [],
                "strengths": [],
                "improvements": [],
            },
            {
                "overall_score": 9.0,
                "confidence": 0.95,
                "evidence": [],
                "strengths": [],
                "improvements": [],
            },
            {
                "overall_score": 8.0,
                "confidence": 0.88,
                "evidence": [],
                "strengths": [],
                "improvements": [],
            },
        ]
        
        orchestrator = AnalysisOrchestrator(bedrock_client=mock_bedrock_client)
        
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
        
        # 3 agents should have succeeded
        assert len(result["agent_responses"]) == 3
        assert AgentName.BUG_HUNTER not in result["agent_responses"]
        assert AgentName.PERFORMANCE in result["agent_responses"]
        
        # Failed agent should be tracked
        assert AgentName.BUG_HUNTER in result["failed_agents"]
        assert len(result["failed_agents"]) == 1
    
    @pytest.mark.asyncio
    async def test_multiple_agents_fail(
        self,
        mock_bedrock_client,
        sample_repo_data,
        sample_rubric,
    ):
        """Test handling of multiple agent failures."""
        # 2 agents fail, 2 succeed
        mock_bedrock_client.converse.side_effect = [
            Exception("BugHunter failed"),
            Exception("Performance failed"),
            build_bedrock_response(build_innovation_json()),
            build_bedrock_response(build_ai_detection_json()),
        ]
        
        mock_bedrock_client.parse_json_response.side_effect = [
            {
                "overall_score": 9.0,
                "confidence": 0.95,
                "evidence": [],
                "strengths": [],
                "improvements": [],
            },
            {
                "overall_score": 8.0,
                "confidence": 0.88,
                "evidence": [],
                "strengths": [],
                "improvements": [],
            },
        ]
        
        orchestrator = AnalysisOrchestrator(bedrock_client=mock_bedrock_client)
        
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
        
        # 2 agents succeeded
        assert len(result["agent_responses"]) == 2
        assert len(result["failed_agents"]) == 2
    
    @pytest.mark.asyncio
    async def test_all_agents_fail(
        self,
        mock_bedrock_client,
        sample_repo_data,
        sample_rubric,
    ):
        """Test that analysis fails if all agents fail."""
        # All agents fail
        mock_bedrock_client.converse.side_effect = [
            Exception("Agent 1 failed"),
            Exception("Agent 2 failed"),
            Exception("Agent 3 failed"),
            Exception("Agent 4 failed"),
        ]
        
        orchestrator = AnalysisOrchestrator(bedrock_client=mock_bedrock_client)
        
        with pytest.raises(ValueError) as exc_info:
            await orchestrator.analyze_submission(
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
        
        assert "All agents failed" in str(exc_info.value)


# ============================================================
# WEIGHTED SCORING TESTS
# ============================================================

class TestWeightedScoring:
    """Tests for weighted scoring aggregation."""
    
    @pytest.mark.asyncio
    async def test_weighted_score_calculation(
        self,
        mock_bedrock_client,
        sample_repo_data,
        sample_rubric,
    ):
        """Test weighted score calculation using rubric."""
        mock_bedrock_client.converse.side_effect = [
            build_bedrock_response(build_bug_hunter_json()),
            build_bedrock_response(build_performance_json()),
            build_bedrock_response(build_innovation_json()),
            build_bedrock_response(build_ai_detection_json()),
        ]
        
        # Set specific scores for calculation
        mock_bedrock_client.parse_json_response.side_effect = [
            {
                "overall_score": 8.0,  # BugHunter: 8.0 * 0.3 * 10 = 24
                "confidence": 0.9,
                "evidence": [],
                "strengths": [],
                "improvements": [],
            },
            {
                "overall_score": 7.0,  # Performance: 7.0 * 0.3 * 10 = 21
                "confidence": 0.85,
                "evidence": [],
                "strengths": [],
                "improvements": [],
            },
            {
                "overall_score": 9.0,  # Innovation: 9.0 * 0.3 * 10 = 27
                "confidence": 0.95,
                "evidence": [],
                "strengths": [],
                "improvements": [],
            },
            {
                "overall_score": 6.0,  # AI Detection: 6.0 * 0.1 * 10 = 6
                "confidence": 0.88,
                "evidence": [],
                "strengths": [],
                "improvements": [],
            },
        ]
        
        orchestrator = AnalysisOrchestrator(bedrock_client=mock_bedrock_client)
        
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
        
        # Expected: 24 + 21 + 27 + 6 = 78.0
        assert result["overall_score"] == 78.0
        
        # Verify weighted scores per dimension
        assert "Code Quality" in result["weighted_scores"]
        assert result["weighted_scores"]["Code Quality"]["raw"] == 8.0
        assert result["weighted_scores"]["Code Quality"]["weight"] == 0.3
        assert result["weighted_scores"]["Code Quality"]["weighted"] == 24.0
    
    @pytest.mark.asyncio
    async def test_confidence_is_minimum(
        self,
        mock_bedrock_client,
        sample_repo_data,
        sample_rubric,
    ):
        """Test that overall confidence is minimum of all agents."""
        mock_bedrock_client.converse.side_effect = [
            build_bedrock_response(build_bug_hunter_json()),
            build_bedrock_response(build_performance_json()),
            build_bedrock_response(build_innovation_json()),
            build_bedrock_response(build_ai_detection_json()),
        ]
        
        mock_bedrock_client.parse_json_response.side_effect = [
            {
                "overall_score": 8.0,
                "confidence": 0.95,  # High
                "evidence": [],
                "strengths": [],
                "improvements": [],
            },
            {
                "overall_score": 7.0,
                "confidence": 0.70,  # Lowest
                "evidence": [],
                "strengths": [],
                "improvements": [],
            },
            {
                "overall_score": 9.0,
                "confidence": 0.90,  # High
                "evidence": [],
                "strengths": [],
                "improvements": [],
            },
            {
                "overall_score": 8.0,
                "confidence": 0.85,  # Medium
                "evidence": [],
                "strengths": [],
                "improvements": [],
            },
        ]
        
        orchestrator = AnalysisOrchestrator(bedrock_client=mock_bedrock_client)
        
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
        
        # Confidence should be minimum (0.70)
        assert result["confidence"] == 0.70


# ============================================================
# RECOMMENDATION CLASSIFICATION TESTS
# ============================================================

class TestRecommendationClassification:
    """Tests for score-to-recommendation classification."""
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("score,expected_recommendation", [
        (85.0, Recommendation.STRONG_CONTENDER),  # 8.5/10 >= 8.0
        (80.0, Recommendation.STRONG_CONTENDER),  # 8.0/10 >= 8.0
        (75.0, Recommendation.SOLID_SUBMISSION),  # 7.5/10 >= 6.5
        (65.0, Recommendation.SOLID_SUBMISSION),  # 6.5/10 >= 6.5
        (50.0, Recommendation.NEEDS_IMPROVEMENT),  # 5.0/10 >= 4.5
        (45.0, Recommendation.NEEDS_IMPROVEMENT),  # 4.5/10 >= 4.5
        (40.0, Recommendation.CONCERNS_FLAGGED),  # 4.0/10 < 4.5
        (20.0, Recommendation.CONCERNS_FLAGGED),  # 2.0/10 < 4.5
    ])
    async def test_recommendation_classification(
        self,
        mock_bedrock_client,
        sample_repo_data,
        sample_rubric,
        score,
        expected_recommendation,
    ):
        """Test recommendation classification based on score."""
        # Configure all agents to return the same score
        agent_score = score / 10  # Convert 0-100 to 0-10
        
        mock_bedrock_client.converse.side_effect = [
            build_bedrock_response(build_bug_hunter_json()),
            build_bedrock_response(build_performance_json()),
            build_bedrock_response(build_innovation_json()),
            build_bedrock_response(build_ai_detection_json()),
        ]
        
        mock_bedrock_client.parse_json_response.side_effect = [
            {
                "overall_score": agent_score,
                "confidence": 0.9,
                "evidence": [],
                "strengths": [],
                "improvements": [],
            },
            {
                "overall_score": agent_score,
                "confidence": 0.9,
                "evidence": [],
                "strengths": [],
                "improvements": [],
            },
            {
                "overall_score": agent_score,
                "confidence": 0.9,
                "evidence": [],
                "strengths": [],
                "improvements": [],
            },
            {
                "overall_score": agent_score,
                "confidence": 0.9,
                "evidence": [],
                "strengths": [],
                "improvements": [],
            },
        ]
        
        orchestrator = AnalysisOrchestrator(bedrock_client=mock_bedrock_client)
        
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
        
        assert result["recommendation"] == expected_recommendation


# ============================================================
# COST TRACKING TESTS
# ============================================================

class TestCostTracking:
    """Tests for cost tracking in orchestrator."""
    
    @pytest.mark.asyncio
    async def test_cost_tracking_per_agent(
        self,
        mock_bedrock_client,
        sample_repo_data,
        sample_rubric,
    ):
        """Test that costs are tracked per agent."""
        mock_bedrock_client.converse.side_effect = [
            build_bedrock_response(build_bug_hunter_json(), input_tokens=1000, output_tokens=500),
            build_bedrock_response(build_performance_json(), input_tokens=1200, output_tokens=600),
            build_bedrock_response(build_innovation_json(), input_tokens=1500, output_tokens=800),
            build_bedrock_response(build_ai_detection_json(), input_tokens=800, output_tokens=400),
        ]
        
        mock_bedrock_client.parse_json_response.side_effect = [
            {"overall_score": 8.0, "confidence": 0.9, "evidence": [], "strengths": [], "improvements": []},
            {"overall_score": 7.0, "confidence": 0.85, "evidence": [], "strengths": [], "improvements": []},
            {"overall_score": 9.0, "confidence": 0.95, "evidence": [], "strengths": [], "improvements": []},
            {"overall_score": 8.0, "confidence": 0.88, "evidence": [], "strengths": [], "improvements": []},
        ]
        
        orchestrator = AnalysisOrchestrator(bedrock_client=mock_bedrock_client)
        
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
        
        # Verify cost records exist
        assert "cost_records" in result
        assert len(result["cost_records"]) == 4
        
        # Verify total cost
        assert "total_cost_usd" in result
        assert result["total_cost_usd"] > 0
        
        # Verify total tokens
        assert "total_tokens" in result
    
    @pytest.mark.asyncio
    async def test_analysis_duration_tracked(
        self,
        mock_bedrock_client,
        sample_repo_data,
        sample_rubric,
    ):
        """Test that analysis duration is tracked."""
        mock_bedrock_client.converse.side_effect = [
            build_bedrock_response(build_bug_hunter_json()),
        ]
        
        mock_bedrock_client.parse_json_response.side_effect = [
            {"overall_score": 8.0, "confidence": 0.9, "evidence": [], "strengths": [], "improvements": []},
        ]
        
        orchestrator = AnalysisOrchestrator(bedrock_client=mock_bedrock_client)
        
        result = await orchestrator.analyze_submission(
            repo_data=sample_repo_data,
            hackathon_name="Test Hackathon",
            team_name="Test Team",
            hack_id="HACK#123",
            sub_id="SUB#456",
            rubric=sample_rubric,
            agents_enabled=[AgentName.BUG_HUNTER],
        )
        
        # Verify duration is tracked
        assert "analysis_duration_ms" in result
        assert result["analysis_duration_ms"] > 0


# ============================================================
# STRENGTHS AND WEAKNESSES AGGREGATION TESTS
# ============================================================

class TestStrengthsWeaknessesAggregation:
    """Tests for aggregating strengths and weaknesses."""
    
    @pytest.mark.asyncio
    async def test_strengths_aggregation(
        self,
        mock_bedrock_client,
        sample_repo_data,
        sample_rubric,
    ):
        """Test that strengths are aggregated from all agents."""
        mock_bedrock_client.converse.side_effect = [
            build_bedrock_response(build_bug_hunter_json()),
            build_bedrock_response(build_performance_json()),
        ]
        
        mock_bedrock_client.parse_json_response.side_effect = [
            {
                "overall_score": 8.0,
                "confidence": 0.9,
                "evidence": [],
                "strengths": ["Clean code", "Good tests"],
                "improvements": ["Add docs"],
            },
            {
                "overall_score": 7.0,
                "confidence": 0.85,
                "evidence": [],
                "strengths": ["Scalable architecture"],
                "improvements": ["Add caching"],
            },
        ]
        
        orchestrator = AnalysisOrchestrator(bedrock_client=mock_bedrock_client)
        
        result = await orchestrator.analyze_submission(
            repo_data=sample_repo_data,
            hackathon_name="Test Hackathon",
            team_name="Test Team",
            hack_id="HACK#123",
            sub_id="SUB#456",
            rubric=sample_rubric,
            agents_enabled=[AgentName.BUG_HUNTER, AgentName.PERFORMANCE],
        )
        
        # Verify strengths are aggregated (max 5, top 2 from each agent)
        assert "strengths" in result
        assert len(result["strengths"]) <= 5
        
        # Verify weaknesses are aggregated
        assert "weaknesses" in result
        assert len(result["weaknesses"]) <= 5
