"""Unit tests for data formatting utilities.

**Validates: Requirements 7.6, 9.2**

This module tests currency formatting with various amounts, timestamp formatting
with ISO strings, and percentage formatting with edge cases.
"""

from components.formatters import format_currency, format_percentage, format_timestamp


class TestFormatCurrency:
    """Test currency formatting with various amounts."""

    def test_format_small_amount(self):
        """Test formatting small currency amounts."""
        assert format_currency(1.5) == "$1.50"
        assert format_currency(0.023) == "$0.02"
        assert format_currency(0.99) == "$0.99"

    def test_format_zero(self):
        """Test formatting zero amount."""
        assert format_currency(0.0) == "$0.00"
        assert format_currency(0) == "$0.00"

    def test_format_large_amount(self):
        """Test formatting large currency amounts with comma separators."""
        assert format_currency(1000.0) == "$1,000.00"
        assert format_currency(1234.56) == "$1,234.56"
        assert format_currency(1000000.0) == "$1,000,000.00"

    def test_format_negative_amount(self):
        """Test formatting negative currency amounts."""
        assert format_currency(-10.50) == "$-10.50"
        assert format_currency(-1000.0) == "$-1,000.00"

    def test_format_rounds_to_two_decimals(self):
        """Test that currency formatting rounds to two decimal places."""
        assert format_currency(1.234) == "$1.23"
        assert format_currency(1.235) == "$1.24"
        assert format_currency(1.999) == "$2.00"

    def test_format_typical_analysis_costs(self):
        """Test formatting typical analysis costs from requirements."""
        # Typical per-repo cost
        assert format_currency(0.023) == "$0.02"
        # Typical agent cost
        assert format_currency(0.002) == "$0.00"
        # Typical batch cost
        assert format_currency(11.50) == "$11.50"


class TestFormatTimestamp:
    """Test timestamp formatting with ISO strings."""

    def test_format_iso_timestamp_with_z_suffix(self):
        """Test formatting ISO timestamp with Z suffix."""
        result = format_timestamp("2025-03-04T12:30:45Z")
        assert result == "2025-03-04 12:30:45"

    def test_format_iso_timestamp_without_z_suffix(self):
        """Test formatting ISO timestamp without Z suffix."""
        result = format_timestamp("2025-03-04T12:30:45")
        assert result == "2025-03-04 12:30:45"

    def test_format_iso_timestamp_with_microseconds(self):
        """Test formatting ISO timestamp with microseconds."""
        result = format_timestamp("2025-03-04T12:30:45.123456Z")
        assert result == "2025-03-04 12:30:45"

    def test_format_timestamp_midnight(self):
        """Test formatting timestamp at midnight."""
        result = format_timestamp("2025-03-01T00:00:00Z")
        assert result == "2025-03-01 00:00:00"

    def test_format_timestamp_end_of_day(self):
        """Test formatting timestamp at end of day."""
        result = format_timestamp("2025-03-03T23:59:59Z")
        assert result == "2025-03-03 23:59:59"

    def test_format_invalid_timestamp_returns_original(self):
        """Test that invalid timestamp returns original string."""
        invalid_timestamp = "not-a-timestamp"
        result = format_timestamp(invalid_timestamp)
        assert result == invalid_timestamp

    def test_format_timestamp_different_dates(self):
        """Test formatting timestamps with different dates."""
        assert format_timestamp("2025-01-01T10:00:00Z") == "2025-01-01 10:00:00"
        assert format_timestamp("2025-12-31T23:59:59Z") == "2025-12-31 23:59:59"
        assert format_timestamp("2024-02-29T12:00:00Z") == "2024-02-29 12:00:00"  # Leap year


class TestFormatPercentage:
    """Test percentage formatting with edge cases."""

    def test_format_zero_percent(self):
        """Test formatting zero percentage."""
        assert format_percentage(0.0) == "0.0%"
        assert format_percentage(0) == "0.0%"

    def test_format_hundred_percent(self):
        """Test formatting 100 percentage."""
        assert format_percentage(100.0) == "100.0%"
        assert format_percentage(100) == "100.0%"

    def test_format_decimal_percentage(self):
        """Test formatting percentage with decimals."""
        assert format_percentage(45.5) == "45.5%"
        assert format_percentage(92.3) == "92.3%"
        assert format_percentage(0.1) == "0.1%"

    def test_format_rounds_to_one_decimal(self):
        """Test that percentage formatting rounds to one decimal place."""
        assert format_percentage(45.55) == "45.5%"
        assert format_percentage(45.56) == "45.6%"
        assert format_percentage(99.99) == "100.0%"

    def test_format_typical_progress_values(self):
        """Test formatting typical progress percentage values."""
        # Analysis progress examples from requirements
        assert format_percentage(0.0) == "0.0%"
        assert format_percentage(25.0) == "25.0%"
        assert format_percentage(50.0) == "50.0%"
        assert format_percentage(75.0) == "75.0%"
        assert format_percentage(100.0) == "100.0%"

    def test_format_confidence_scores(self):
        """Test formatting confidence scores (0-1 range converted to percentage)."""
        # Note: These would need to be multiplied by 100 before formatting
        assert format_percentage(95.0) == "95.0%"  # 0.95 * 100
        assert format_percentage(85.5) == "85.5%"  # 0.855 * 100

    def test_format_over_hundred_percent(self):
        """Test formatting percentage over 100 (edge case)."""
        assert format_percentage(150.0) == "150.0%"
        assert format_percentage(200.5) == "200.5%"

    def test_format_negative_percentage(self):
        """Test formatting negative percentage (edge case)."""
        assert format_percentage(-10.0) == "-10.0%"
        assert format_percentage(-5.5) == "-5.5%"


class TestFormatterIntegration:
    """Test formatters working together in realistic scenarios."""

    def test_format_scorecard_display_data(self):
        """Test formatting data as it would appear in a scorecard."""
        # Simulate scorecard data formatting
        overall_score = 92.5
        confidence = 95.0  # Already converted from 0.95
        cost = 0.023
        timestamp = "2025-03-04T12:30:45Z"

        assert format_percentage(overall_score) == "92.5%"
        assert format_percentage(confidence) == "95.0%"
        assert format_currency(cost) == "$0.02"
        assert format_timestamp(timestamp) == "2025-03-04 12:30:45"

    def test_format_analysis_progress_data(self):
        """Test formatting data as it would appear in analysis progress."""
        # Simulate analysis progress data formatting
        progress = 45.5
        current_cost = 3.45
        estimated_cost = 7.50
        estimated_completion = "2025-03-04T13:30:00Z"

        assert format_percentage(progress) == "45.5%"
        assert format_currency(current_cost) == "$3.45"
        assert format_currency(estimated_cost) == "$7.50"
        assert format_timestamp(estimated_completion) == "2025-03-04 13:30:00"

    def test_format_cost_breakdown_data(self):
        """Test formatting cost breakdown by agent (Requirement 7.6)."""
        # Simulate agent cost breakdown
        agent_costs = {
            "bug_hunter": 0.002,
            "performance": 0.002,
            "innovation": 0.018,
            "ai_detection": 0.001,
        }
        total_cost = sum(agent_costs.values())

        formatted_costs = {agent: format_currency(cost) for agent, cost in agent_costs.items()}

        assert formatted_costs["bug_hunter"] == "$0.00"
        assert formatted_costs["performance"] == "$0.00"
        assert formatted_costs["innovation"] == "$0.02"
        assert formatted_costs["ai_detection"] == "$0.00"
        assert format_currency(total_cost) == "$0.02"

    def test_format_hiring_intelligence_data(self):
        """Test formatting hiring intelligence data (Requirement 9.2)."""
        # Simulate must_interview candidate data
        hiring_score = 95.0

        assert format_percentage(hiring_score) == "95.0%"
