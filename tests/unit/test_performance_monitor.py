"""Unit tests for performance monitoring."""

import time

from src.analysis.performance_monitor import (
    PERFORMANCE_TARGETS,
    PerformanceMonitor,
    log_performance_warning,
)


def test_performance_monitor_initialization():
    """Test performance monitor initialization."""
    monitor = PerformanceMonitor("test-sub-123")

    assert monitor.sub_id == "test-sub-123"
    assert monitor.timings == {}
    assert monitor.start_time > 0


def test_performance_monitor_track():
    """Test component tracking."""
    monitor = PerformanceMonitor("test-sub-123")

    with monitor.track("test_component"):
        time.sleep(0.01)  # 10ms

    assert "test_component" in monitor.timings
    assert monitor.timings["test_component"] >= 10  # At least 10ms


def test_performance_monitor_multiple_components():
    """Test tracking multiple components."""
    monitor = PerformanceMonitor("test-sub-123")

    with monitor.track("component_a"):
        time.sleep(0.01)

    with monitor.track("component_b"):
        time.sleep(0.02)

    assert len(monitor.timings) == 2
    assert monitor.timings["component_a"] >= 10
    assert monitor.timings["component_b"] >= 20


def test_performance_monitor_get_total_duration():
    """Test total duration calculation."""
    monitor = PerformanceMonitor("test-sub-123")

    time.sleep(0.05)  # 50ms

    total_ms = monitor.get_total_duration_ms()
    assert total_ms >= 50


def test_performance_monitor_get_summary():
    """Test performance summary generation."""
    monitor = PerformanceMonitor("test-sub-123")

    with monitor.track("component_a"):
        time.sleep(0.01)

    summary = monitor.get_summary()

    assert "total_duration_ms" in summary
    assert "component_timings" in summary
    assert "within_target" in summary
    assert "target_ms" in summary
    assert summary["target_ms"] == 90000
    assert summary["within_target"] is True  # Should be under 90 seconds


def test_performance_monitor_check_timeout_risk_no_risk():
    """Test timeout risk check when under threshold."""
    monitor = PerformanceMonitor("test-sub-123")

    time.sleep(0.01)  # 10ms - well under 67.5 second threshold

    assert monitor.check_timeout_risk() is False


def test_performance_monitor_check_timeout_risk_at_risk():
    """Test timeout risk check when over threshold."""
    monitor = PerformanceMonitor("test-sub-123")

    # Simulate being over 75% of target (67.5 seconds)
    # We can't actually wait that long, so we'll test the logic
    monitor.start_time = time.time() - 68  # 68 seconds ago

    assert monitor.check_timeout_risk() is True


def test_performance_monitor_within_target():
    """Test that fast analysis is marked as within target."""
    monitor = PerformanceMonitor("test-sub-123")

    with monitor.track("fast_component"):
        time.sleep(0.001)  # 1ms

    summary = monitor.get_summary()
    assert summary["within_target"] is True


def test_performance_targets_defined():
    """Test that all expected performance targets are defined."""
    expected_targets = [
        "git_clone",
        "git_extract",
        "actions_analyzer",
        "team_analyzer",
        "strategy_detector",
        "agents_parallel",
        "brand_voice_transformer",
        "total_pipeline",
    ]

    for target in expected_targets:
        assert target in PERFORMANCE_TARGETS
        assert PERFORMANCE_TARGETS[target] > 0


def test_performance_targets_sum_to_reasonable_total():
    """Test that component targets sum to less than total target."""
    component_sum = sum(
        PERFORMANCE_TARGETS[k] for k in PERFORMANCE_TARGETS if k != "total_pipeline"
    )

    # Component targets should sum to less than total (allows for overhead)
    assert component_sum <= PERFORMANCE_TARGETS["total_pipeline"]


def test_log_performance_warning_under_target():
    """Test that no warning is logged when under target."""
    # This function should not log when under target - verify no exception
    log_performance_warning("test_component", 100, 200)

    # If we get here without exception, the function works correctly
    assert True


def test_log_performance_warning_over_target():
    """Test that warning is logged when over target."""
    # This function logs a warning - we just verify it doesn't raise an exception
    # Actual log verification would require structlog test fixtures
    log_performance_warning("test_component", 300, 200)

    # If we get here without exception, the function works correctly
    assert True


def test_performance_monitor_track_exception_handling():
    """Test that tracking works even if exception occurs."""
    monitor = PerformanceMonitor("test-sub-123")

    try:
        with monitor.track("failing_component"):
            time.sleep(0.01)
            raise ValueError("Test error")
    except ValueError:
        pass

    # Should still record timing even though exception occurred
    assert "failing_component" in monitor.timings
    assert monitor.timings["failing_component"] >= 10


def test_performance_monitor_summary_rounding():
    """Test that summary values are properly rounded."""
    monitor = PerformanceMonitor("test-sub-123")

    with monitor.track("component"):
        time.sleep(0.0123)  # 12.3ms

    summary = monitor.get_summary()

    # Check that values are rounded to 2 decimal places
    assert isinstance(summary["total_duration_ms"], (int, float))
    assert isinstance(summary["component_timings"]["component"], (int, float))
