"""Cost estimation service for budget planning and control.

This service provides cost estimation before analysis to prevent budget surprises.
It includes repo size analysis, large repo premiums, and budget availability checks.
"""

from src.constants import AGENT_MODELS, MODEL_RATES
from src.models.costs import (
    AgentCostEstimate,
    BudgetCheck,
    CostEstimate,
    CostEstimateDetail,
    CostRange,
)
from src.utils.dynamo import DynamoDBHelper
from src.utils.logging import get_logger

logger = get_logger(__name__)


# Constants for cost estimation
LARGE_REPO_THRESHOLD = 100  # files
LARGE_REPO_PREMIUM_USD = 0.10
BUDGET_WARNING_THRESHOLD = 0.80  # 80%
BASE_COST_PER_SUBMISSION = 0.063  # Average from historical data


class CostEstimationService:
    """Service for estimating analysis costs before execution."""

    def __init__(self, db: DynamoDBHelper):
        """Initialize cost estimation service.

        Args:
            db: DynamoDB helper instance
        """
        self.db = db

    def estimate_submission_cost(
        self,
        repo_url: str,
        agent_config: dict[str, bool],
        repo_file_count: int | None = None,
    ) -> dict:
        """Estimate cost for a single submission based on repo size and enabled agents.

        Args:
            repo_url: Repository URL
            agent_config: Dict of agent_name -> enabled (bool)
            repo_file_count: Number of files in repo (if known)

        Returns:
            Dict with cost estimate details
        """
        # Determine which agents are enabled
        enabled_agents = [agent for agent, enabled in agent_config.items() if enabled]

        # Base cost calculation per agent
        agent_estimates = []
        total_base_cost = 0.0

        for agent_name in enabled_agents:
            model_id = AGENT_MODELS.get(agent_name, "amazon.nova-lite-v1:0")
            rates = MODEL_RATES.get(model_id, {"input": 0, "output": 0})

            # Historical average: ~35k tokens per agent (85% input, 15% output)
            estimated_tokens = 35000
            input_tokens = int(estimated_tokens * 0.85)
            output_tokens = int(estimated_tokens * 0.15)

            input_cost = input_tokens * rates["input"]
            output_cost = output_tokens * rates["output"]
            agent_cost = input_cost + output_cost

            agent_estimates.append(
                {
                    "agent_name": agent_name,
                    "model_id": model_id,
                    "estimated_tokens": estimated_tokens,
                    "estimated_cost_usd": agent_cost,
                }
            )

            total_base_cost += agent_cost

        # Apply large repo premium if applicable
        large_repo_premium = 0.0
        is_large_repo = False

        if repo_file_count is not None and repo_file_count > LARGE_REPO_THRESHOLD:
            large_repo_premium = LARGE_REPO_PREMIUM_USD
            is_large_repo = True
            logger.info(
                "large_repo_premium_applied",
                repo_url=repo_url,
                file_count=repo_file_count,
                premium_usd=large_repo_premium,
            )

        total_estimated_cost = total_base_cost + large_repo_premium

        return {
            "repo_url": repo_url,
            "base_cost_usd": total_base_cost,
            "large_repo_premium_usd": large_repo_premium,
            "is_large_repo": is_large_repo,
            "repo_file_count": repo_file_count,
            "total_estimated_cost_usd": total_estimated_cost,
            "agent_estimates": agent_estimates,
            "enabled_agents": enabled_agents,
        }

    def estimate_hackathon_cost(
        self,
        hackathon_id: str,
        agent_config: dict[str, bool] | None = None,
    ) -> dict:
        """Estimate total cost for analyzing all submissions in a hackathon.

        Args:
            hackathon_id: Hackathon ID
            agent_config: Optional dict of agent_name -> enabled (bool)
                         If None, uses hackathon's configured agents

        Returns:
            Dict with batch cost estimate
        """
        # Get hackathon details
        hackathon = self.db.get_hackathon(hackathon_id)
        if not hackathon:
            raise ValueError(f"Hackathon {hackathon_id} not found")

        # Get submissions
        submissions = self.db.list_submissions(hackathon_id)
        submission_count = len(submissions)

        # Use hackathon's agent config if not provided
        if agent_config is None:
            # Default: all agents enabled
            agent_config = {
                "bug_hunter": True,
                "performance": True,
                "innovation": True,
                "ai_detection": True,
            }

        # Estimate per submission (use historical average)
        enabled_agents = [agent for agent, enabled in agent_config.items() if enabled]
        per_submission_base = self._calculate_base_cost_per_submission(enabled_agents)

        # Calculate total with variance
        total_base_cost = per_submission_base * submission_count

        # Estimate large repo premium (assume 20% of repos are large)
        estimated_large_repos = int(submission_count * 0.20)
        total_large_repo_premium = estimated_large_repos * LARGE_REPO_PREMIUM_USD

        total_estimated_cost = total_base_cost + total_large_repo_premium

        # Calculate ranges (±20% variance)
        cost_low = total_estimated_cost * 0.8
        cost_high = total_estimated_cost * 1.2

        return {
            "hackathon_id": hackathon_id,
            "submission_count": submission_count,
            "enabled_agents": enabled_agents,
            "per_submission_base_usd": per_submission_base,
            "total_base_cost_usd": total_base_cost,
            "estimated_large_repos": estimated_large_repos,
            "total_large_repo_premium_usd": total_large_repo_premium,
            "total_estimated_cost_usd": total_estimated_cost,
            "cost_range": {"low": cost_low, "expected": total_estimated_cost, "high": cost_high},
        }

    def check_budget_availability(
        self,
        api_key: str,
        estimated_cost: float,
    ) -> tuple[bool, float, str | None]:
        """Check if estimated cost is within available budget.

        Args:
            api_key: API key to check budget for
            estimated_cost: Estimated cost in USD

        Returns:
            Tuple of (within_budget, remaining_budget, warning_message)
        """
        # Get API key budget info
        # Note: This will use the future get_api_key method when API key service is implemented
        try:
            api_key_data = self.db.get_api_key(api_key)  # type: ignore[attr-defined]
        except AttributeError:
            # Fallback for when API key service is not yet implemented
            logger.warning("budget_check_not_available", api_key_prefix=api_key[:8])
            return True, float("inf"), None

        if not api_key_data:
            logger.warning("budget_check_failed_no_key", api_key_prefix=api_key[:8])
            return False, 0.0, "API key not found"

        budget_limit = api_key_data.get("budget_limit_usd", 0.0)
        current_spend = api_key_data.get("total_cost_usd", 0.0)

        remaining_budget = budget_limit - current_spend

        # Check if within budget
        within_budget = estimated_cost <= remaining_budget

        # Generate warning if estimate exceeds 80% of remaining budget
        warning = None
        if remaining_budget > 0:
            utilization = (estimated_cost / remaining_budget) * 100
            if utilization >= BUDGET_WARNING_THRESHOLD * 100:
                warning = (
                    f"Warning: Estimated cost ${estimated_cost:.3f} will use "
                    f"{utilization:.1f}% of remaining budget (${remaining_budget:.3f})"
                )
                logger.warning(
                    "budget_warning_threshold_exceeded",
                    api_key_prefix=api_key[:8],
                    estimated_cost=estimated_cost,
                    remaining_budget=remaining_budget,
                    utilization_pct=utilization,
                )

        logger.info(
            "budget_availability_checked",
            api_key_prefix=api_key[:8],
            estimated_cost=estimated_cost,
            remaining_budget=remaining_budget,
            within_budget=within_budget,
        )

        return within_budget, remaining_budget, warning

    def _calculate_base_cost_per_submission(self, enabled_agents: list[str]) -> float:
        """Calculate base cost per submission for given agents.

        Args:
            enabled_agents: List of enabled agent names

        Returns:
            Base cost in USD
        """
        total_cost = 0.0

        for agent_name in enabled_agents:
            model_id = AGENT_MODELS.get(agent_name, "amazon.nova-lite-v1:0")
            rates = MODEL_RATES.get(model_id, {"input": 0, "output": 0})

            # Historical average: ~35k tokens per agent (85% input, 15% output)
            estimated_tokens = 35000
            input_tokens = int(estimated_tokens * 0.85)
            output_tokens = int(estimated_tokens * 0.15)

            input_cost = input_tokens * rates["input"]
            output_cost = output_tokens * rates["output"]
            agent_cost = input_cost + output_cost

            total_cost += agent_cost

        return total_cost

    def get_cost_estimate_response(
        self,
        hack_id: str,
        submission_count: int,
        agents_enabled: list[str],
        budget_limit_usd: float | None = None,
    ) -> CostEstimate:
        """Get cost estimate as API response model.

        Args:
            hack_id: Hackathon ID
            submission_count: Number of submissions
            agents_enabled: List of agent names
            budget_limit_usd: Optional budget limit

        Returns:
            CostEstimate for API response
        """
        # Calculate base cost per submission
        per_submission_base = self._calculate_base_cost_per_submission(agents_enabled)

        # Estimate large repo premium (assume 20% of repos are large)
        estimated_large_repos = int(submission_count * 0.20)
        total_large_repo_premium = estimated_large_repos * LARGE_REPO_PREMIUM_USD

        # Calculate total cost
        total_base_cost = per_submission_base * submission_count
        total_estimated_cost = total_base_cost + total_large_repo_premium

        # Calculate ranges (±20% variance)
        total_low = total_estimated_cost * 0.8
        total_high = total_estimated_cost * 1.2

        per_sub_expected = per_submission_base + (total_large_repo_premium / submission_count)
        per_sub_low = per_sub_expected * 0.8
        per_sub_high = per_sub_expected * 1.2

        # Build agent cost breakdown
        cost_by_agent = {}
        for agent_name in agents_enabled:
            model_id = AGENT_MODELS.get(agent_name, "amazon.nova-lite-v1:0")
            rates = MODEL_RATES.get(model_id, {"input": 0, "output": 0})

            # Historical average: ~35k tokens per agent
            estimated_tokens = 35000
            input_tokens = int(estimated_tokens * 0.85)
            output_tokens = int(estimated_tokens * 0.15)

            input_cost = input_tokens * rates["input"]
            output_cost = output_tokens * rates["output"]
            agent_cost = input_cost + output_cost

            cost_by_agent[agent_name] = AgentCostEstimate(
                model=model_id,
                estimated_usd=agent_cost,
            )

        # Estimate duration (assume 30 seconds per submission)
        duration_expected = (submission_count * 30) / 60  # minutes
        duration_low = duration_expected * 0.7
        duration_high = duration_expected * 1.5

        # Budget check
        budget_check = None
        if budget_limit_usd:
            within_budget = total_estimated_cost <= budget_limit_usd
            utilization_pct = (
                (total_estimated_cost / budget_limit_usd * 100) if budget_limit_usd > 0 else 0
            )

            budget_check = BudgetCheck(
                budget_limit_usd=budget_limit_usd,
                within_budget=within_budget,
                budget_utilization_pct=utilization_pct,
            )

            # Log warning if exceeds 80% threshold
            if utilization_pct >= BUDGET_WARNING_THRESHOLD * 100:
                logger.warning(
                    "budget_estimate_warning",
                    hack_id=hack_id,
                    estimated_cost=total_estimated_cost,
                    budget_limit=budget_limit_usd,
                    utilization_pct=utilization_pct,
                )

        return CostEstimate(
            hack_id=hack_id,
            submission_count=submission_count,
            agents_enabled=agents_enabled,
            estimate=CostEstimateDetail(
                total_cost_usd=CostRange(low=total_low, expected=total_estimated_cost, high=total_high),
                per_submission_cost_usd=CostRange(
                    low=per_sub_low, expected=per_sub_expected, high=per_sub_high
                ),
                cost_by_agent=cost_by_agent,
                estimated_duration_minutes=CostRange(
                    low=duration_low, expected=duration_expected, high=duration_high
                ),
            ),
            budget_check=budget_check,
        )
