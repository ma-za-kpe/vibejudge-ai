"""Form validation utilities for hackathon dashboard.

This module provides validation functions for form inputs and data structures,
ensuring data integrity before submission to the backend API and safe rendering
of API responses.
"""

from datetime import datetime
from typing import Any


def validate_date_range(start_date: datetime, end_date: datetime) -> bool:
    """Validate that end_date is after start_date.

    Args:
        start_date: The hackathon start date
        end_date: The hackathon end date

    Returns:
        True if end_date > start_date, False otherwise

    Examples:
        >>> from datetime import datetime
        >>> start = datetime(2025, 3, 1)
        >>> end = datetime(2025, 3, 3)
        >>> validate_date_range(start, end)
        True

        >>> validate_date_range(end, start)
        False

        >>> validate_date_range(start, start)
        False
    """
    return end_date > start_date


def validate_budget(budget: float | None) -> bool:
    """Validate that budget is positive or None.

    Args:
        budget: The budget limit in USD, or None if no budget

    Returns:
        True if budget is None or positive, False if negative or zero

    Examples:
        >>> validate_budget(None)
        True

        >>> validate_budget(100.0)
        True

        >>> validate_budget(0.0)
        False

        >>> validate_budget(-10.0)
        False
    """
    if budget is None:
        return True
    return budget > 0


def validate_scorecard(data: dict[str, Any]) -> bool:
    """Validate that scorecard response has all required fields.

    Args:
        data: The scorecard data dictionary from API response

    Returns:
        True if all required fields are present, False otherwise

    Examples:
        >>> scorecard = {
        ...     "overall_score": 92.5,
        ...     "confidence": 0.95,
        ...     "recommendation": "must_interview",
        ...     "dimension_scores": {},
        ...     "agent_results": {},
        ...     "repo_meta": {}
        ... }
        >>> validate_scorecard(scorecard)
        True

        >>> incomplete = {"overall_score": 92.5}
        >>> validate_scorecard(incomplete)
        False
    """
    required_fields = [
        "overall_score",
        "confidence",
        "recommendation",
        "dimension_scores",
        "agent_results",
        "repo_meta",
    ]
    return all(field in data for field in required_fields)


def validate_individual_scorecard(data: dict[str, Any]) -> bool:
    """Validate that individual scorecard response has all required fields.

    Args:
        data: The individual scorecard data dictionary from API response

    Returns:
        True if all required fields are present, False otherwise

    Examples:
        >>> individual = {
        ...     "team_dynamics": {},
        ...     "strategy_analysis": {},
        ...     "contributors": []
        ... }
        >>> validate_individual_scorecard(individual)
        True

        >>> incomplete = {"team_dynamics": {}}
        >>> validate_individual_scorecard(incomplete)
        False
    """
    required_fields = ["team_dynamics", "strategy_analysis", "contributors"]
    return all(field in data for field in required_fields)


def validate_leaderboard(data: dict[str, Any]) -> bool:
    """Validate that leaderboard response has all required fields.

    Args:
        data: The leaderboard data dictionary from API response

    Returns:
        True if all required fields are present, False otherwise

    Examples:
        >>> leaderboard = {
        ...     "hack_id": "01HXXX",
        ...     "total_submissions": 150,
        ...     "analyzed_count": 148,
        ...     "submissions": []
        ... }
        >>> validate_leaderboard(leaderboard)
        True

        >>> incomplete = {"total_submissions": 150}
        >>> validate_leaderboard(incomplete)
        False
    """
    required_fields = ["hack_id", "total_submissions", "analyzed_count", "submissions"]
    return all(field in data for field in required_fields)


def safe_get(data: dict[str, Any], key: str, default: Any = None) -> Any:
    """Safely get a value from a dictionary with a default fallback.

    This is a wrapper around dict.get() that provides consistent behavior
    for accessing potentially missing keys in API responses.

    Args:
        data: The dictionary to access
        key: The key to retrieve
        default: The default value if key is not found (default: None)

    Returns:
        The value at the key, or the default if key is not present

    Examples:
        >>> data = {"score": 92.5, "name": "Team A"}
        >>> safe_get(data, "score", 0)
        92.5

        >>> safe_get(data, "missing", "N/A")
        'N/A'

        >>> safe_get(data, "missing")

    """
    return data.get(key, default)


def safe_get_nested(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Safely get a nested value from a dictionary with a default fallback.

    This function traverses nested dictionaries safely, returning the default
    value if any key in the path is missing.

    Args:
        data: The dictionary to access
        *keys: Variable number of keys representing the path to traverse
        default: The default value if any key is not found (default: None)

    Returns:
        The value at the nested path, or the default if any key is not present

    Examples:
        >>> data = {"agent_results": {"bug_hunter": {"cost_usd": 0.002}}}
        >>> safe_get_nested(data, "agent_results", "bug_hunter", "cost_usd", default=0)
        0.002

        >>> safe_get_nested(data, "agent_results", "missing", "cost_usd", default=0)
        0

        >>> safe_get_nested(data, "missing", default="N/A")
        'N/A'
    """
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current
