"""Performance monitoring and optimization for analysis pipeline."""

import time
from contextlib import contextmanager
from typing import Any

from src.utils.logging import get_logger

logger = get_logger(__name__)


class PerformanceMonitor:
    """Monitor and track performance of analysis pipeline components."""

    def __init__(self, sub_id: str):
        """Initialize performance monitor.

        Args:
            sub_id: Submission ID for tracking
        """
        self.sub_id = sub_id
        self.timings: dict[str, float] = {}
        self.start_time = time.time()

    @contextmanager
    def track(self, component: str):
        """Context manager to track component execution time.

        Args:
            component: Name of component being tracked

        Yields:
            None
        """
        start = time.time()
        try:
            yield
        finally:
            duration_ms = (time.time() - start) * 1000
            self.timings[component] = duration_ms
            logger.info(
                "component_timing",
                sub_id=self.sub_id,
                component=component,
                duration_ms=round(duration_ms, 2),
            )

    def get_total_duration_ms(self) -> float:
        """Get total duration since monitor creation.

        Returns:
            Total duration in milliseconds
        """
        return (time.time() - self.start_time) * 1000

    def get_summary(self) -> dict[str, Any]:
        """Get performance summary.

        Returns:
            Dict with timing breakdown and total
        """
        total_ms = self.get_total_duration_ms()
        return {
            "total_duration_ms": round(total_ms, 2),
            "component_timings": {k: round(v, 2) for k, v in self.timings.items()},
            "within_target": total_ms < 90000,  # 90 seconds
            "target_ms": 90000,
        }

    def check_timeout_risk(self) -> bool:
        """Check if we're at risk of exceeding 90 second target.

        Returns:
            True if we're over 75% of target time (67.5 seconds)
        """
        current_ms = self.get_total_duration_ms()
        threshold_ms = 90000 * 0.75  # 75% of 90 seconds
        
        if current_ms > threshold_ms:
            logger.warning(
                "timeout_risk_detected",
                sub_id=self.sub_id,
                current_ms=round(current_ms, 2),
                threshold_ms=threshold_ms,
                target_ms=90000,
            )
            return True
        return False


# Performance optimization constants
PERFORMANCE_TARGETS = {
    "git_clone": 15000,  # 15 seconds max for cloning
    "git_extract": 10000,  # 10 seconds max for extraction
    "actions_analyzer": 10000,  # 10 seconds max for CI/CD analysis
    "team_analyzer": 5000,  # 5 seconds max for team analysis
    "strategy_detector": 3000,  # 3 seconds max for strategy detection
    "agents_parallel": 40000,  # 40 seconds max for all agents (parallel)
    "brand_voice_transformer": 2000,  # 2 seconds max for feedback transformation
    "total_pipeline": 90000,  # 90 seconds total target
}


def log_performance_warning(component: str, duration_ms: float, target_ms: float) -> None:
    """Log performance warning if component exceeds target.

    Args:
        component: Component name
        duration_ms: Actual duration in milliseconds
        target_ms: Target duration in milliseconds
    """
    if duration_ms > target_ms:
        logger.warning(
            "performance_target_exceeded",
            component=component,
            duration_ms=round(duration_ms, 2),
            target_ms=target_ms,
            overage_ms=round(duration_ms - target_ms, 2),
            overage_pct=round(((duration_ms - target_ms) / target_ms) * 100, 1),
        )
