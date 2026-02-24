"""Unit tests for component performance tracking in CostTracker."""

from src.analysis.cost_tracker import CostTracker


class TestComponentPerformanceTracking:
    """Tests for component performance tracking."""

    def test_record_component_performance_success(self):
        """Test recording successful component execution."""
        tracker = CostTracker()

        record = tracker.record_component_performance(
            sub_id="sub_123",
            hack_id="hack_456",
            component_name="team_analyzer",
            duration_ms=1500,
            findings_count=5,
            success=True,
        )

        assert record.sub_id == "sub_123"
        assert record.hack_id == "hack_456"
        assert record.component_name == "team_analyzer"
        assert record.duration_ms == 1500
        assert record.findings_count == 5
        assert record.success is True
        assert record.error_message is None

    def test_record_component_performance_failure(self):
        """Test recording failed component execution."""
        tracker = CostTracker()

        record = tracker.record_component_performance(
            sub_id="sub_123",
            hack_id="hack_456",
            component_name="strategy_detector",
            duration_ms=500,
            findings_count=0,
            success=False,
            error_message="Analysis failed",
        )

        assert record.success is False
        assert record.error_message == "Analysis failed"
        assert record.findings_count == 0

    def test_get_component_records(self):
        """Test retrieving component performance records."""
        tracker = CostTracker()

        tracker.record_component_performance(
            sub_id="sub_123",
            hack_id="hack_456",
            component_name="team_analyzer",
            duration_ms=1500,
            findings_count=5,
        )

        tracker.record_component_performance(
            sub_id="sub_123",
            hack_id="hack_456",
            component_name="strategy_detector",
            duration_ms=800,
            findings_count=3,
        )

        records = tracker.get_component_records()
        assert len(records) == 2
        assert records[0].component_name == "team_analyzer"
        assert records[1].component_name == "strategy_detector"

    def test_get_total_component_duration(self):
        """Test calculating total component duration."""
        tracker = CostTracker()

        tracker.record_component_performance(
            sub_id="sub_123",
            hack_id="hack_456",
            component_name="team_analyzer",
            duration_ms=1500,
            findings_count=5,
        )

        tracker.record_component_performance(
            sub_id="sub_123",
            hack_id="hack_456",
            component_name="strategy_detector",
            duration_ms=800,
            findings_count=3,
        )

        tracker.record_component_performance(
            sub_id="sub_123",
            hack_id="hack_456",
            component_name="brand_voice_transformer",
            duration_ms=1200,
            findings_count=10,
        )

        total_duration = tracker.get_total_component_duration_ms()
        assert total_duration == 3500  # 1500 + 800 + 1200

    def test_clear_clears_component_records(self):
        """Test that clear() removes component records."""
        tracker = CostTracker()

        tracker.record_component_performance(
            sub_id="sub_123",
            hack_id="hack_456",
            component_name="team_analyzer",
            duration_ms=1500,
            findings_count=5,
        )

        assert len(tracker.get_component_records()) == 1

        tracker.clear()

        assert len(tracker.get_component_records()) == 0
        assert tracker.get_total_component_duration_ms() == 0

    def test_component_tracking_independent_of_agent_tracking(self):
        """Test that component tracking doesn't interfere with agent tracking."""
        tracker = CostTracker()

        # Record agent cost
        tracker.record_agent_cost(
            sub_id="sub_123",
            hack_id="hack_456",
            agent_name="bug_hunter",
            model_id="amazon.nova-lite-v1:0",
            input_tokens=1000,
            output_tokens=500,
            latency_ms=2000,
        )

        # Record component performance
        tracker.record_component_performance(
            sub_id="sub_123",
            hack_id="hack_456",
            component_name="team_analyzer",
            duration_ms=1500,
            findings_count=5,
        )

        # Both should be tracked independently
        assert len(tracker.get_records()) == 1
        assert len(tracker.get_component_records()) == 1
        assert tracker.get_total_cost() > 0
        assert tracker.get_total_component_duration_ms() == 1500
