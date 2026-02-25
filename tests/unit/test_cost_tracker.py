"""Unit tests for cost tracker."""

from src.analysis.cost_tracker import CostTracker
from src.models.common import AgentName


class TestCostTracker:
    """Tests for CostTracker."""

    def test_initialization(self):
        """Test cost tracker initialization."""
        tracker = CostTracker()

        assert tracker.get_total_cost() == 0.0
        assert tracker.get_total_tokens() == 0
        assert len(tracker.get_records()) == 0

    def test_record_single_agent_cost(self):
        """Test recording cost for a single agent."""
        tracker = CostTracker()

        tracker.record_agent_cost(
            sub_id="SUB#123",
            hack_id="HACK#456",
            agent_name=AgentName.BUG_HUNTER,
            model_id="amazon.nova-lite-v1:0",
            input_tokens=1000,
            output_tokens=500,
            latency_ms=1200,
        )

        # Verify total cost
        total_cost = tracker.get_total_cost()
        assert total_cost > 0

        # Verify total tokens
        assert tracker.get_total_tokens() == 1500

        # Verify records
        records = tracker.get_records()
        assert len(records) == 1
        assert records[0].agent_name == AgentName.BUG_HUNTER
        assert records[0].input_tokens == 1000
        assert records[0].output_tokens == 500

    def test_record_multiple_agents(self):
        """Test recording costs for multiple agents."""
        tracker = CostTracker()

        # Record BugHunter
        tracker.record_agent_cost(
            sub_id="SUB#123",
            hack_id="HACK#456",
            agent_name=AgentName.BUG_HUNTER,
            model_id="amazon.nova-lite-v1:0",
            input_tokens=1000,
            output_tokens=500,
            latency_ms=1200,
        )

        # Record Performance
        tracker.record_agent_cost(
            sub_id="SUB#123",
            hack_id="HACK#456",
            agent_name=AgentName.PERFORMANCE,
            model_id="amazon.nova-lite-v1:0",
            input_tokens=1200,
            output_tokens=600,
            latency_ms=1300,
        )

        # Record Innovation (different model)
        tracker.record_agent_cost(
            sub_id="SUB#123",
            hack_id="HACK#456",
            agent_name=AgentName.INNOVATION,
            model_id="anthropic.claude-sonnet-4-20250514",
            input_tokens=1500,
            output_tokens=800,
            latency_ms=1800,
        )

        # Verify total tokens
        assert tracker.get_total_tokens() == 5600  # 1000+500+1200+600+1500+800

        # Verify records
        records = tracker.get_records()
        assert len(records) == 3

    def test_get_cost_by_agent(self):
        """Test getting cost breakdown by agent."""
        tracker = CostTracker()

        tracker.record_agent_cost(
            sub_id="SUB#123",
            hack_id="HACK#456",
            agent_name=AgentName.BUG_HUNTER,
            model_id="amazon.nova-lite-v1:0",
            input_tokens=1000,
            output_tokens=500,
            latency_ms=1200,
        )

        tracker.record_agent_cost(
            sub_id="SUB#123",
            hack_id="HACK#456",
            agent_name=AgentName.PERFORMANCE,
            model_id="amazon.nova-lite-v1:0",
            input_tokens=1200,
            output_tokens=600,
            latency_ms=1300,
        )

        by_agent = tracker.get_cost_by_agent()

        assert AgentName.BUG_HUNTER in by_agent
        assert AgentName.PERFORMANCE in by_agent
        assert by_agent[AgentName.BUG_HUNTER] > 0
        assert by_agent[AgentName.PERFORMANCE] > 0

    def test_get_cost_by_model(self):
        """Test getting cost breakdown by model."""
        tracker = CostTracker()

        # Two agents using Nova Lite
        tracker.record_agent_cost(
            sub_id="SUB#123",
            hack_id="HACK#456",
            agent_name=AgentName.BUG_HUNTER,
            model_id="amazon.nova-lite-v1:0",
            input_tokens=1000,
            output_tokens=500,
            latency_ms=1200,
        )

        tracker.record_agent_cost(
            sub_id="SUB#123",
            hack_id="HACK#456",
            agent_name=AgentName.PERFORMANCE,
            model_id="amazon.nova-lite-v1:0",
            input_tokens=1200,
            output_tokens=600,
            latency_ms=1300,
        )

        # One agent using Claude Sonnet
        tracker.record_agent_cost(
            sub_id="SUB#123",
            hack_id="HACK#456",
            agent_name=AgentName.INNOVATION,
            model_id="anthropic.claude-sonnet-4-20250514",
            input_tokens=1500,
            output_tokens=800,
            latency_ms=1800,
        )

        by_model = tracker.get_cost_by_model()

        assert "amazon.nova-lite-v1:0" in by_model
        assert "anthropic.claude-sonnet-4-20250514" in by_model

        # Nova Lite should have combined cost from 2 agents
        assert (
            by_model["amazon.nova-lite-v1:0"]
            > by_model["anthropic.claude-sonnet-4-20250514"] * 0.01
        )

    def test_cost_calculation_accuracy(self):
        """Test that cost calculation matches expected values."""
        tracker = CostTracker()

        # Nova Lite rates: input=0.00000006, output=0.00000024
        tracker.record_agent_cost(
            sub_id="SUB#123",
            hack_id="HACK#456",
            agent_name=AgentName.BUG_HUNTER,
            model_id="amazon.nova-lite-v1:0",
            input_tokens=1000,
            output_tokens=500,
            latency_ms=1200,
        )

        # Expected: (1000 * 0.00000006) + (500 * 0.00000024) = 0.00006 + 0.00012 = 0.00018
        total_cost = tracker.get_total_cost()
        assert abs(total_cost - 0.00018) < 0.000001  # Allow small floating point error
