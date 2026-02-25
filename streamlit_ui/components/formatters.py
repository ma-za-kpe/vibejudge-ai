"""Data formatting utilities for the Streamlit dashboard.

This module provides functions for formatting currency, timestamps, and percentages
in a user-friendly format throughout the dashboard.
"""

from datetime import datetime


def format_currency(amount: float) -> str:
    """Format USD amount with dollar sign and two decimal places.

    Args:
        amount: The amount in USD to format

    Returns:
        Formatted currency string (e.g., "$1.50", "$1,000.00")

    Examples:
        >>> format_currency(1.5)
        '$1.50'
        >>> format_currency(1000.0)
        '$1,000.00'
        >>> format_currency(0.023)
        '$0.02'
    """
    return f"${amount:,.2f}"


def format_timestamp(iso_timestamp: str) -> str:
    """Format ISO timestamp to human-readable format.

    Args:
        iso_timestamp: ISO 8601 formatted timestamp string

    Returns:
        Formatted timestamp string (e.g., "2025-03-04 12:30:45")

    Examples:
        >>> format_timestamp("2025-03-04T12:30:45Z")
        '2025-03-04 12:30:45'
        >>> format_timestamp("2025-03-04T12:30:45.123456Z")
        '2025-03-04 12:30:45'
    """
    # Remove 'Z' suffix if present and parse
    timestamp_str = iso_timestamp.rstrip("Z")

    # Handle both with and without microseconds
    try:
        dt = datetime.fromisoformat(timestamp_str)
    except ValueError:
        # If parsing fails, return the original string
        return iso_timestamp

    return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_percentage(value: float) -> str:
    """Format percentage with one decimal place.

    Args:
        value: The percentage value (0-100)

    Returns:
        Formatted percentage string (e.g., "45.5%", "100.0%")

    Examples:
        >>> format_percentage(45.5)
        '45.5%'
        >>> format_percentage(100.0)
        '100.0%'
        >>> format_percentage(0.0)
        '0.0%'
    """
    return f"{value:.1f}%"
