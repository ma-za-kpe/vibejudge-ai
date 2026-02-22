"""Cost service — Cost tracking and estimation."""

from datetime import UTC, datetime

from src.constants import AGENT_MODELS, MODEL_RATES
from src.models.costs import (
    AgentCostEstimate,
    BudgetCheck,
    BudgetInfo,
    CostEstimate,
    CostEstimateDetail,
    CostRange,
    CostRecord,
    HackathonCostResponse,
)
from src.utils.dynamo import DynamoDBHelper
from src.utils.logging import get_logger

logger = get_logger(__name__)


class CostService:
    """Service for cost tracking and estimation."""

    def __init__(self, db: DynamoDBHelper):
        """Initialize cost service.

        Args:
            db: DynamoDB helper instance
        """
        self.db = db

    def record_agent_cost(
        self,
        sub_id: str,
        agent_name: str,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
    ) -> CostRecord:
        """Record cost for a single agent execution.

        Args:
            sub_id: Submission ID
            agent_name: Agent name
            model_id: Model ID used
            input_tokens: Input tokens
            output_tokens: Output tokens

        Returns:
            Cost record

        Raises:
            ValueError: If cost record cannot be saved
        """
        # Calculate cost
        rates = MODEL_RATES.get(model_id, {"input": 0, "output": 0})
        input_cost = input_tokens * rates["input"]
        output_cost = output_tokens * rates["output"]
        total_cost = input_cost + output_cost

        now = datetime.now(UTC)

        # Create cost record
        record = {
            "PK": f"SUB#{sub_id}",
            "SK": f"COST#{agent_name}",
            "entity_type": "COST",
            "sub_id": sub_id,
            "agent_name": agent_name,
            "model_id": model_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "input_cost_usd": input_cost,
            "output_cost_usd": output_cost,
            "total_cost_usd": total_cost,
            "timestamp": now.isoformat(),
        }

        logger.info(
            "cost_record_saving",
            sub_id=sub_id,
            agent=agent_name,
            pk=record["PK"],
            sk=record["SK"],
            cost_usd=total_cost,
            tokens=input_tokens + output_tokens,
        )

        success = self.db.put_cost_record(record)
        if not success:
            error_msg = f"Failed to save cost record for {sub_id}/{agent_name}"
            logger.error(
                "cost_record_failed",
                sub_id=sub_id,
                agent=agent_name,
                error=error_msg,
            )
            raise ValueError(error_msg)

        logger.info(
            "cost_recorded",
            sub_id=sub_id,
            agent=agent_name,
            cost_usd=total_cost,
            tokens=input_tokens + output_tokens,
        )

        # Note: CostRecord model expects more fields, but for internal tracking we use dict
        return record

    def get_submission_costs(self, sub_id: str) -> dict:
        """Get cost breakdown for submission.

        Args:
            sub_id: Submission ID

        Returns:
            Dict with cost details
        """
        records = self.db.get_submission_costs(sub_id)

        total_cost = 0.0
        total_tokens = 0

        for r in records:
            total_cost += r["total_cost_usd"]
            total_tokens += r["total_tokens"]

        return {
            "sub_id": sub_id,
            "total_cost_usd": total_cost,
            "total_tokens": total_tokens,
            "agent_costs": records,
        }

    def get_hackathon_costs(self, hack_id: str) -> dict:
        """Get cost summary for hackathon.

        Args:
            hack_id: Hackathon ID

        Returns:
            Dict with cost summary
        """
        # Get all submissions
        submissions = self.db.list_submissions(hack_id)

        total_cost = 0.0
        total_tokens = 0
        submission_count = len(submissions)
        agent_breakdown = {}

        # Aggregate costs from all submissions
        for sub in submissions:
            sub_id = sub["sub_id"]
            sub_costs = self.db.get_submission_costs(sub_id)

            for cost in sub_costs:
                agent_name = cost["agent_name"]

                if agent_name not in agent_breakdown:
                    agent_breakdown[agent_name] = {
                        "agent_name": agent_name,
                        "total_cost_usd": 0.0,
                        "total_tokens": 0,
                        "execution_count": 0,
                    }

                agent_breakdown[agent_name]["total_cost_usd"] += cost["total_cost_usd"]
                agent_breakdown[agent_name]["total_tokens"] += cost["total_tokens"]
                agent_breakdown[agent_name]["execution_count"] += 1

                total_cost += cost["total_cost_usd"]
                total_tokens += cost["total_tokens"]

        avg_cost = total_cost / submission_count if submission_count > 0 else 0.0

        return {
            "hack_id": hack_id,
            "total_cost_usd": total_cost,
            "total_tokens": total_tokens,
            "submission_count": submission_count,
            "average_cost_per_submission": avg_cost,
            "agent_breakdown": list(agent_breakdown.values()),
        }

    def estimate_analysis_cost(
        self,
        agents_enabled: list[str],
        estimated_tokens_per_agent: int = 35000,
    ) -> dict:
        """Estimate cost for analysis.

        Args:
            agents_enabled: List of agent names
            estimated_tokens_per_agent: Estimated tokens per agent

        Returns:
            Dict with cost estimate
        """
        agent_estimates = []
        total_cost = 0.0
        total_tokens = 0

        for agent_name in agents_enabled:
            model_id = AGENT_MODELS.get(agent_name, "amazon.nova-lite-v1:0")
            rates = MODEL_RATES.get(model_id, {"input": 0, "output": 0})

            # Assume 85% input, 15% output
            input_tokens = int(estimated_tokens_per_agent * 0.85)
            output_tokens = int(estimated_tokens_per_agent * 0.15)

            input_cost = input_tokens * rates["input"]
            output_cost = output_tokens * rates["output"]
            agent_cost = input_cost + output_cost

            agent_estimates.append({
                "agent_name": agent_name,
                "model_id": model_id,
                "estimated_tokens": estimated_tokens_per_agent,
                "estimated_cost_usd": agent_cost,
            })

            total_cost += agent_cost
            total_tokens += estimated_tokens_per_agent

        return {
            "estimated_total_cost_usd": total_cost,
            "estimated_total_tokens": total_tokens,
            "agent_estimates": agent_estimates,
        }

    def update_hackathon_cost_summary(self, hack_id: str) -> bool:
        """Update hackathon cost summary record.

        Args:
            hack_id: Hackathon ID

        Returns:
            True if successful
        """
        summary = self.get_hackathon_costs(hack_id)

        record = {
            "PK": f"HACK#{hack_id}",
            "SK": "COST#SUMMARY",
            "entity_type": "COST_SUMMARY",
            "hack_id": hack_id,
            "total_cost_usd": summary["total_cost_usd"],
            "total_tokens": summary["total_tokens"],
            "submission_count": summary["submission_count"],
            "average_cost_per_submission": summary["average_cost_per_submission"],
            "agent_breakdown": summary["agent_breakdown"],
            "updated_at": datetime.now(UTC).isoformat(),
        }

        return self.db.put_hackathon_cost_summary(record)

    def get_hackathon_costs_response(
        self,
        hack_id: str,
        budget_limit_usd: float | None = None,
    ) -> HackathonCostResponse:
        """Get hackathon costs as API response model.

        Args:
            hack_id: Hackathon ID
            budget_limit_usd: Optional budget limit

        Returns:
            HackathonCostResponse for API
        """
        summary = self.get_hackathon_costs(hack_id)

        # Build cost by agent dict
        cost_by_agent = {
            b["agent_name"]: b["total_cost_usd"]
            for b in summary["agent_breakdown"]
        }

        # Build cost by model dict (aggregate by model)
        cost_by_model = {}
        for sub in self.db.list_submissions(hack_id):
            sub_costs = self.db.get_submission_costs(sub["sub_id"])
            for cost in sub_costs:
                model_id = cost["model_id"]
                cost_by_model[model_id] = cost_by_model.get(model_id, 0.0) + cost["total_cost_usd"]

        # Calculate budget info if limit provided
        budget = None
        if budget_limit_usd:
            budget = BudgetInfo(
                limit_usd=budget_limit_usd,
                used_usd=summary["total_cost_usd"],
                remaining_usd=max(0, budget_limit_usd - summary["total_cost_usd"]),
                utilization_pct=(summary["total_cost_usd"] / budget_limit_usd * 100) if budget_limit_usd > 0 else 0,
            )

        # Calculate token breakdown
        total_input = 0
        total_output = 0
        for sub in self.db.list_submissions(hack_id):
            sub_costs = self.db.get_submission_costs(sub["sub_id"])
            for cost in sub_costs:
                total_input += cost["input_tokens"]
                total_output += cost["output_tokens"]

        return HackathonCostResponse(
            hack_id=hack_id,
            total_cost_usd=summary["total_cost_usd"],
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            submissions_analyzed=summary["submission_count"],
            avg_cost_per_submission=summary["average_cost_per_submission"],
            cost_by_agent=cost_by_agent,
            cost_by_model=cost_by_model,
            budget=budget,
            optimization_tips=[],  # Can add tips based on usage patterns
        )

    def estimate_analysis_cost_response(
        self,
        hack_id: str,
        submission_count: int,
        agents_enabled: list[str],
        budget_limit_usd: float | None = None,
    ) -> CostEstimate:
        """Estimate analysis cost as API response model.

        Args:
            hack_id: Hackathon ID
            submission_count: Number of submissions
            agents_enabled: List of agent names
            budget_limit_usd: Optional budget limit

        Returns:
            CostEstimate for API
        """
        # Get base estimate per submission
        base_estimate = self.estimate_analysis_cost(agents_enabled)

        # Calculate ranges (±20% variance)
        total_expected = base_estimate["estimated_total_cost_usd"] * submission_count
        total_low = total_expected * 0.8
        total_high = total_expected * 1.2

        per_sub_expected = base_estimate["estimated_total_cost_usd"]
        per_sub_low = per_sub_expected * 0.8
        per_sub_high = per_sub_expected * 1.2

        # Build agent estimates
        cost_by_agent = {}
        for agent_est in base_estimate["agent_estimates"]:
            cost_by_agent[agent_est["agent_name"]] = AgentCostEstimate(
                model=agent_est["model_id"],
                estimated_usd=agent_est["estimated_cost_usd"],
            )

        # Estimate duration (assume 30 seconds per submission)
        duration_expected = (submission_count * 30) / 60  # minutes
        duration_low = duration_expected * 0.7
        duration_high = duration_expected * 1.5

        # Budget check
        budget_check = None
        if budget_limit_usd:
            budget_check = BudgetCheck(
                budget_limit_usd=budget_limit_usd,
                within_budget=total_expected <= budget_limit_usd,
                budget_utilization_pct=(total_expected / budget_limit_usd * 100) if budget_limit_usd > 0 else 0,
            )

        return CostEstimate(
            hack_id=hack_id,
            submission_count=submission_count,
            agents_enabled=agents_enabled,
            estimate=CostEstimateDetail(
                total_cost_usd=CostRange(low=total_low, expected=total_expected, high=total_high),
                per_submission_cost_usd=CostRange(low=per_sub_low, expected=per_sub_expected, high=per_sub_high),
                cost_by_agent=cost_by_agent,
                estimated_duration_minutes=CostRange(low=duration_low, expected=duration_expected, high=duration_high),
            ),
            budget_check=budget_check,
        )
