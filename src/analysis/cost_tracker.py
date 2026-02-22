"""Cost tracking for agent analysis."""


from src.constants import MODEL_RATES
from src.models.common import AgentName, ServiceTier
from src.models.costs import CostRecord
from src.utils.logging import get_logger

logger = get_logger(__name__)


class CostTracker:
    """Track token usage and costs for agent analysis."""

    def __init__(self):
        """Initialize cost tracker."""
        self.records: list[CostRecord] = []

    def record_agent_cost(
        self,
        sub_id: str,
        hack_id: str,
        agent_name: AgentName,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
        service_tier: ServiceTier = ServiceTier.STANDARD,
    ) -> CostRecord:
        """Record cost for a single agent execution.
        
        Args:
            sub_id: Submission ID
            hack_id: Hackathon ID
            agent_name: Agent name
            model_id: Bedrock model ID
            input_tokens: Input token count
            output_tokens: Output token count
            latency_ms: Response latency in milliseconds
            service_tier: Service tier (standard or flex)
            
        Returns:
            CostRecord instance
        """
        # Calculate costs
        rates = MODEL_RATES.get(model_id, {"input": 0.0, "output": 0.0})
        input_cost = input_tokens * rates["input"]
        output_cost = output_tokens * rates["output"]
        total_cost = input_cost + output_cost

        record = CostRecord(
            sub_id=sub_id,
            hack_id=hack_id,
            agent_name=agent_name,
            model_id=model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            input_cost_usd=round(input_cost, 6),
            output_cost_usd=round(output_cost, 6),
            total_cost_usd=round(total_cost, 6),
            latency_ms=latency_ms,
            service_tier=service_tier,
        )

        self.records.append(record)

        logger.info(
            "cost_recorded",
            agent=agent_name,
            model=model_id,
            tokens=record.total_tokens,
            cost_usd=record.total_cost_usd,
        )

        return record

    def get_total_cost(self) -> float:
        """Get total cost across all recorded agents.
        
        Returns:
            Total cost in USD
        """
        return sum(r.total_cost_usd for r in self.records)

    def get_total_tokens(self) -> int:
        """Get total tokens across all recorded agents.
        
        Returns:
            Total token count
        """
        return sum(r.total_tokens for r in self.records)

    def get_cost_by_agent(self) -> dict[str, float]:
        """Get cost breakdown by agent.
        
        Returns:
            Dict mapping agent name to cost
        """
        costs = {}
        for record in self.records:
            agent = record.agent_name
            costs[agent] = costs.get(agent, 0.0) + record.total_cost_usd
        return costs

    def get_cost_by_model(self) -> dict[str, float]:
        """Get cost breakdown by model.
        
        Returns:
            Dict mapping model ID to cost
        """
        costs = {}
        for record in self.records:
            model = record.model_id
            costs[model] = costs.get(model, 0.0) + record.total_cost_usd
        return costs

    def get_records(self) -> list[CostRecord]:
        """Get all cost records.
        
        Returns:
            List of CostRecord instances
        """
        return self.records.copy()

    def clear(self) -> None:
        """Clear all recorded costs."""
        self.records.clear()
