"""Unit tests for cost estimation service."""

from unittest.mock import MagicMock

import pytest

from src.services.cost_estimation_service import (
    LARGE_REPO_PREMIUM_USD,
    CostEstimationService,
)


@pytest.fixture
def mock_db() -> MagicMock:
    """Create mock DynamoDB helper."""
    return MagicMock()


@pytest.fixture
def cost_estimation_service(mock_db: MagicMock) -> CostEstimationService:
    """Create cost estimation service with mock DB."""
    return CostEstimationService(db=mock_db)


class TestEstimateSubmissionCost:
    """Tests for estimate_submission_cost method."""

    def test_estimate_single_agent(self, cost_estimation_service: CostEstimationService) -> None:
        """Test cost estimation with single agent."""
        result = cost_estimation_service.estimate_submission_cost(
            repo_url="https://github.com/test/repo",
            agent_config={
                "bug_hunter": True,
                "performance": False,
                "innovation": False,
                "ai_detection": False,
            },
            repo_file_count=50,
        )

        assert result["repo_url"] == "https://github.com/test/repo"
        assert result["enabled_agents"] == ["bug_hunter"]
        assert result["base_cost_usd"] > 0
        assert result["large_repo_premium_usd"] == 0.0
        assert result["is_large_repo"] is False
        assert result["repo_file_count"] == 50
        assert len(result["agent_estimates"]) == 1
        assert result["agent_estimates"][0]["agent_name"] == "bug_hunter"

    def test_estimate_all_agents(self, cost_estimation_service: CostEstimationService) -> None:
        """Test cost estimation with all agents enabled."""
        result = cost_estimation_service.estimate_submission_cost(
            repo_url="https://github.com/test/repo",
            agent_config={
                "bug_hunter": True,
                "performance": True,
                "innovation": True,
                "ai_detection": True,
            },
            repo_file_count=50,
        )

        assert len(result["enabled_agents"]) == 4
        assert len(result["agent_estimates"]) == 4
        assert result["base_cost_usd"] > 0
        # Innovation agent (Claude Sonnet) should be most expensive
        innovation_cost = next(
            est["estimated_cost_usd"]
            for est in result["agent_estimates"]
            if est["agent_name"] == "innovation"
        )
        bug_hunter_cost = next(
            est["estimated_cost_usd"]
            for est in result["agent_estimates"]
            if est["agent_name"] == "bug_hunter"
        )
        assert innovation_cost > bug_hunter_cost

    def test_large_repo_premium_applied(
        self, cost_estimation_service: CostEstimationService
    ) -> None:
        """Test that large repo premium is applied for repos >100 files."""
        result = cost_estimation_service.estimate_submission_cost(
            repo_url="https://github.com/test/large-repo",
            agent_config={"bug_hunter": True},
            repo_file_count=150,
        )

        assert result["is_large_repo"] is True
        assert result["large_repo_premium_usd"] == LARGE_REPO_PREMIUM_USD
        assert (
            result["total_estimated_cost_usd"] == result["base_cost_usd"] + LARGE_REPO_PREMIUM_USD
        )

    def test_large_repo_premium_not_applied(
        self, cost_estimation_service: CostEstimationService
    ) -> None:
        """Test that large repo premium is NOT applied for repos <=100 files."""
        result = cost_estimation_service.estimate_submission_cost(
            repo_url="https://github.com/test/small-repo",
            agent_config={"bug_hunter": True},
            repo_file_count=100,
        )

        assert result["is_large_repo"] is False
        assert result["large_repo_premium_usd"] == 0.0
        assert result["total_estimated_cost_usd"] == result["base_cost_usd"]

    def test_no_file_count_provided(self, cost_estimation_service: CostEstimationService) -> None:
        """Test estimation when file count is not provided."""
        result = cost_estimation_service.estimate_submission_cost(
            repo_url="https://github.com/test/repo",
            agent_config={"bug_hunter": True},
            repo_file_count=None,
        )

        assert result["is_large_repo"] is False
        assert result["large_repo_premium_usd"] == 0.0
        assert result["repo_file_count"] is None


class TestEstimateHackathonCost:
    """Tests for estimate_hackathon_cost method."""

    def test_estimate_with_submissions(
        self, cost_estimation_service: CostEstimationService, mock_db: MagicMock
    ) -> None:
        """Test hackathon cost estimation with submissions."""
        mock_db.get_hackathon.return_value = {"hack_id": "hack_123", "name": "Test Hackathon"}
        mock_db.list_submissions.return_value = [
            {"sub_id": "sub_1"},
            {"sub_id": "sub_2"},
            {"sub_id": "sub_3"},
        ]

        result = cost_estimation_service.estimate_hackathon_cost(
            hackathon_id="hack_123",
            agent_config={"bug_hunter": True, "performance": True},
        )

        assert result["hackathon_id"] == "hack_123"
        assert result["submission_count"] == 3
        assert result["enabled_agents"] == ["bug_hunter", "performance"]
        assert result["per_submission_base_usd"] > 0
        assert result["total_base_cost_usd"] == result["per_submission_base_usd"] * 3
        assert "cost_range" in result
        assert result["cost_range"]["low"] < result["cost_range"]["expected"]
        assert result["cost_range"]["expected"] < result["cost_range"]["high"]

    def test_estimate_with_default_agents(
        self, cost_estimation_service: CostEstimationService, mock_db: MagicMock
    ) -> None:
        """Test hackathon cost estimation with default agent config."""
        mock_db.get_hackathon.return_value = {"hack_id": "hack_123"}
        mock_db.list_submissions.return_value = [{"sub_id": "sub_1"}]

        result = cost_estimation_service.estimate_hackathon_cost(
            hackathon_id="hack_123",
            agent_config=None,
        )

        # Should default to all 4 agents
        assert len(result["enabled_agents"]) == 4
        assert "bug_hunter" in result["enabled_agents"]
        assert "performance" in result["enabled_agents"]
        assert "innovation" in result["enabled_agents"]
        assert "ai_detection" in result["enabled_agents"]

    def test_estimate_large_repo_premium_calculation(
        self, cost_estimation_service: CostEstimationService, mock_db: MagicMock
    ) -> None:
        """Test that large repo premium is estimated (20% of repos)."""
        mock_db.get_hackathon.return_value = {"hack_id": "hack_123"}
        mock_db.list_submissions.return_value = [{"sub_id": f"sub_{i}"} for i in range(10)]

        result = cost_estimation_service.estimate_hackathon_cost(
            hackathon_id="hack_123",
            agent_config={"bug_hunter": True},
        )

        # 20% of 10 submissions = 2 large repos
        assert result["estimated_large_repos"] == 2
        assert result["total_large_repo_premium_usd"] == 2 * LARGE_REPO_PREMIUM_USD

    def test_estimate_hackathon_not_found(
        self, cost_estimation_service: CostEstimationService, mock_db: MagicMock
    ) -> None:
        """Test error when hackathon not found."""
        mock_db.get_hackathon.return_value = None

        with pytest.raises(ValueError, match="Hackathon hack_999 not found"):
            cost_estimation_service.estimate_hackathon_cost(
                hackathon_id="hack_999",
                agent_config={"bug_hunter": True},
            )

    def test_estimate_variance_ranges(
        self, cost_estimation_service: CostEstimationService, mock_db: MagicMock
    ) -> None:
        """Test that variance ranges are ±20%."""
        mock_db.get_hackathon.return_value = {"hack_id": "hack_123"}
        mock_db.list_submissions.return_value = [{"sub_id": "sub_1"}]

        result = cost_estimation_service.estimate_hackathon_cost(
            hackathon_id="hack_123",
            agent_config={"bug_hunter": True},
        )

        expected = result["cost_range"]["expected"]
        low = result["cost_range"]["low"]
        high = result["cost_range"]["high"]

        # Low should be 80% of expected
        assert abs(low - expected * 0.8) < 0.001
        # High should be 120% of expected
        assert abs(high - expected * 1.2) < 0.001


class TestCheckBudgetAvailability:
    """Tests for check_budget_availability method."""

    def test_within_budget(
        self, cost_estimation_service: CostEstimationService, mock_db: MagicMock
    ) -> None:
        """Test budget check when within budget."""
        mock_db.get_api_key.return_value = {
            "api_key": "vj_test_abc123",
            "budget_limit_usd": 10.0,
            "total_cost_usd": 2.0,
        }

        within_budget, remaining, warning = cost_estimation_service.check_budget_availability(
            api_key="vj_test_abc123",
            estimated_cost=5.0,
        )

        assert within_budget is True
        assert remaining == 8.0
        assert warning is None

    def test_exceeds_budget(
        self, cost_estimation_service: CostEstimationService, mock_db: MagicMock
    ) -> None:
        """Test budget check when exceeding budget."""
        mock_db.get_api_key.return_value = {
            "api_key": "vj_test_abc123",
            "budget_limit_usd": 10.0,
            "total_cost_usd": 8.0,
        }

        within_budget, remaining, warning = cost_estimation_service.check_budget_availability(
            api_key="vj_test_abc123",
            estimated_cost=5.0,
        )

        assert within_budget is False
        assert remaining == 2.0
        assert warning is not None

    def test_warning_at_80_percent_threshold(
        self, cost_estimation_service: CostEstimationService, mock_db: MagicMock
    ) -> None:
        """Test that warning is generated at 80% threshold."""
        mock_db.get_api_key.return_value = {
            "api_key": "vj_test_abc123",
            "budget_limit_usd": 10.0,
            "total_cost_usd": 1.0,
        }

        # Estimate uses 80% of remaining budget (7.2 / 9.0 = 80%)
        within_budget, remaining, warning = cost_estimation_service.check_budget_availability(
            api_key="vj_test_abc123",
            estimated_cost=7.2,
        )

        assert within_budget is True
        assert remaining == 9.0
        assert warning is not None
        assert "80.0%" in warning

    def test_no_warning_below_threshold(
        self, cost_estimation_service: CostEstimationService, mock_db: MagicMock
    ) -> None:
        """Test that no warning is generated below 80% threshold."""
        mock_db.get_api_key.return_value = {
            "api_key": "vj_test_abc123",
            "budget_limit_usd": 10.0,
            "total_cost_usd": 1.0,
        }

        # Estimate uses 50% of remaining budget
        within_budget, remaining, warning = cost_estimation_service.check_budget_availability(
            api_key="vj_test_abc123",
            estimated_cost=4.5,
        )

        assert within_budget is True
        assert warning is None

    def test_api_key_not_found(
        self, cost_estimation_service: CostEstimationService, mock_db: MagicMock
    ) -> None:
        """Test budget check when API key not found."""
        mock_db.get_api_key.return_value = None

        within_budget, remaining, warning = cost_estimation_service.check_budget_availability(
            api_key="vj_test_invalid",
            estimated_cost=5.0,
        )

        assert within_budget is False
        assert remaining == 0.0
        assert warning == "API key not found"


class TestGetCostEstimateResponse:
    """Tests for get_cost_estimate_response method."""

    def test_response_structure(self, cost_estimation_service: CostEstimationService) -> None:
        """Test that response has correct structure."""
        result = cost_estimation_service.get_cost_estimate_response(
            hack_id="hack_123",
            submission_count=5,
            agents_enabled=["bug_hunter", "performance"],
            budget_limit_usd=None,
        )

        assert result.hack_id == "hack_123"
        assert result.submission_count == 5
        assert result.agents_enabled == ["bug_hunter", "performance"]
        assert result.estimate is not None
        assert result.estimate.total_cost_usd is not None
        assert result.estimate.per_submission_cost_usd is not None
        assert result.estimate.cost_by_agent is not None
        assert result.estimate.estimated_duration_minutes is not None
        assert result.budget_check is None

    def test_response_with_budget_check(
        self, cost_estimation_service: CostEstimationService
    ) -> None:
        """Test response includes budget check when limit provided."""
        result = cost_estimation_service.get_cost_estimate_response(
            hack_id="hack_123",
            submission_count=5,
            agents_enabled=["bug_hunter"],
            budget_limit_usd=10.0,
        )

        assert result.budget_check is not None
        assert result.budget_check.budget_limit_usd == 10.0
        assert result.budget_check.within_budget is not None
        assert result.budget_check.budget_utilization_pct >= 0

    def test_cost_by_agent_breakdown(self, cost_estimation_service: CostEstimationService) -> None:
        """Test that cost breakdown by agent is correct."""
        result = cost_estimation_service.get_cost_estimate_response(
            hack_id="hack_123",
            submission_count=1,
            agents_enabled=["bug_hunter", "innovation"],
            budget_limit_usd=None,
        )

        assert "bug_hunter" in result.estimate.cost_by_agent
        assert "innovation" in result.estimate.cost_by_agent
        assert result.estimate.cost_by_agent["bug_hunter"].model == "amazon.nova-lite-v1:0"
        assert result.estimate.cost_by_agent["innovation"].model == "us.anthropic.claude-sonnet-4-6"

    def test_duration_estimation(self, cost_estimation_service: CostEstimationService) -> None:
        """Test that duration is estimated correctly (30s per submission)."""
        result = cost_estimation_service.get_cost_estimate_response(
            hack_id="hack_123",
            submission_count=10,
            agents_enabled=["bug_hunter"],
            budget_limit_usd=None,
        )

        # 10 submissions * 30 seconds = 300 seconds = 5 minutes
        expected_duration = 5.0
        assert abs(result.estimate.estimated_duration_minutes.expected - expected_duration) < 0.1

    def test_budget_warning_logged(self, cost_estimation_service: CostEstimationService) -> None:
        """Test that budget warning is logged when exceeding 80% threshold."""
        result = cost_estimation_service.get_cost_estimate_response(
            hack_id="hack_123",
            submission_count=100,
            agents_enabled=["bug_hunter", "performance", "innovation", "ai_detection"],
            budget_limit_usd=1.0,  # Very low budget to trigger warning
        )

        assert result.budget_check is not None
        assert result.budget_check.budget_utilization_pct > 80


class TestCalculateBaseCostPerSubmission:
    """Tests for _calculate_base_cost_per_submission private method."""

    def test_single_agent_cost(self, cost_estimation_service: CostEstimationService) -> None:
        """Test base cost calculation for single agent."""
        cost = cost_estimation_service._calculate_base_cost_per_submission(["bug_hunter"])
        assert cost > 0
        assert cost < 0.01  # Nova Lite should be cheap

    def test_multiple_agents_cost(self, cost_estimation_service: CostEstimationService) -> None:
        """Test base cost calculation for multiple agents."""
        cost = cost_estimation_service._calculate_base_cost_per_submission(
            ["bug_hunter", "performance", "innovation", "ai_detection"]
        )
        assert cost > 0
        # Innovation (Claude Sonnet) should dominate the cost
        assert cost > 0.01

    def test_cost_increases_with_agents(
        self, cost_estimation_service: CostEstimationService
    ) -> None:
        """Test that cost increases as more agents are added."""
        cost_one = cost_estimation_service._calculate_base_cost_per_submission(["bug_hunter"])
        cost_two = cost_estimation_service._calculate_base_cost_per_submission(
            ["bug_hunter", "performance"]
        )
        cost_four = cost_estimation_service._calculate_base_cost_per_submission(
            ["bug_hunter", "performance", "innovation", "ai_detection"]
        )

        assert cost_two > cost_one
        assert cost_four > cost_two
