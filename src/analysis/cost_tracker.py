"""Cost tracking for agent analysis."""

from src.constants import MODEL_RATES
from src.models.common import AgentName, ServiceTier
from src.models.costs import ComponentPerformanceRecord, CostRecord
from src.utils.logging import get_logger

logger = get_logger(__name__)


class CostTracker:
    """Track token usage and costs for agent analysis."""

    def __init__(self):
        """Initialize cost tracker."""
        self.records: list[CostRecord] = []
        self.component_records: list[ComponentPerformanceRecord] = []

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

    def record_component_performance(
        self,
        sub_id: str,
        hack_id: str,
        component_name: str,
        duration_ms: int,
        findings_count: int = 0,
        success: bool = True,
        error_message: str | None = None,
    ) -> ComponentPerformanceRecord:
        """Record performance for a non-AI component (free static analysis).

        Args:
            sub_id: Submission ID
            hack_id: Hackathon ID
            component_name: Component name (team_analyzer, strategy_detector, etc.)
            duration_ms: Execution duration in milliseconds
            findings_count: Number of findings/items produced
            success: Whether the component executed successfully
            error_message: Error message if failed

        Returns:
            ComponentPerformanceRecord instance
        """
        record = ComponentPerformanceRecord(
            sub_id=sub_id,
            hack_id=hack_id,
            component_name=component_name,
            duration_ms=duration_ms,
            findings_count=findings_count,
            success=success,
            error_message=error_message,
        )

        self.component_records.append(record)

        logger.info(
            "component_performance_recorded",
            component=component_name,
            duration_ms=duration_ms,
            findings_count=findings_count,
            success=success,
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
        costs: dict[str, float] = {}
        for record in self.records:
            agent = (
                record.agent_name.value
                if hasattr(record.agent_name, "value")
                else str(record.agent_name)
            )
            costs[agent] = costs.get(agent, 0.0) + record.total_cost_usd
        return costs

    def get_cost_by_model(self) -> dict[str, float]:
        """Get cost breakdown by model.

        Returns:
            Dict mapping model ID to cost
        """
        costs: dict[str, float] = {}
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

    def get_component_records(self) -> list[ComponentPerformanceRecord]:
        """Get all component performance records.

        Returns:
            List of ComponentPerformanceRecord instances
        """
        return self.component_records.copy()

    def get_total_component_duration_ms(self) -> int:
        """Get total duration across all components.

        Returns:
            Total duration in milliseconds
        """
        return sum(r.duration_ms for r in self.component_records)

    def clear(self) -> None:
        """Clear all recorded costs and component performance."""
        self.records.clear()
        self.component_records.clear()
