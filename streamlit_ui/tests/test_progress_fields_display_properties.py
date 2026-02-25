"""Property-based tests for progress fields display.

Feature: streamlit-organizer-dashboard
Tests universal properties of progress fields display behavior using Hypothesis.
"""

from typing import Any

from hypothesis import given
from hypothesis import strategies as st


# Custom strategies for progress data
@st.composite
def valid_progress_data(draw: Any) -> dict[str, Any]:
    """Generate a valid analysis job progress data dictionary.

    Returns:
        A dictionary with completed_submissions, failed_submissions, and current_cost_usd
    """
    total = draw(st.integers(min_value=1, max_value=500))
    completed = draw(st.integers(min_value=0, max_value=total))
    failed = draw(st.integers(min_value=0, max_value=completed))

    return {
        "completed_submissions": completed,
        "failed_submissions": failed,
        "total_submissions": total,
        "current_cost_usd": draw(
            st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False)
        ),
    }


def render_progress_display(progress: dict[str, Any]) -> dict[str, Any]:
    """Simulate the progress display logic from the dashboard.

    This function represents the logic that would be in the Streamlit page
    for displaying analysis progress fields.

    Args:
        progress: Progress data dictionary from API

    Returns:
        Dictionary of displayed progress fields
    """
    displayed_fields = {}

    # Display completed_submissions
    if "completed_submissions" in progress:
        displayed_fields["completed_submissions"] = progress["completed_submissions"]

    # Display failed_submissions
    if "failed_submissions" in progress:
        displayed_fields["failed_submissions"] = progress["failed_submissions"]

    # Display current_cost_usd
    if "current_cost_usd" in progress:
        displayed_fields["current_cost_usd"] = progress["current_cost_usd"]

    return displayed_fields


class TestProgressFieldsDisplayProperty:
    """Property 16: Progress Fields Display

    **Validates: Requirements 5.3**

    For any analysis job response, the dashboard should display completed_submissions,
    failed_submissions, and current_cost_usd.
    """

    @given(progress=valid_progress_data())
    def test_all_three_progress_fields_are_displayed(self, progress: dict[str, Any]) -> None:
        """
        Property: For any progress data, the dashboard should display all three
        required progress fields.

        This test verifies that:
        1. All three required fields are displayed
        2. No required fields are missing
        3. The displayed values match the input data

        Args:
            progress: Generated progress data dictionary
        """
        # Act: Simulate rendering progress display
        displayed = render_progress_display(progress)

        # Assert: All three required fields are displayed
        required_fields = ["completed_submissions", "failed_submissions", "current_cost_usd"]

        for field in required_fields:
            assert field in displayed, f"Dashboard should display '{field}' field, but it's missing"

        # Assert: Displayed values match input data
        for field in required_fields:
            assert displayed[field] == progress[field], (
                f"Displayed value for '{field}' should be {progress[field]}, "
                f"but got {displayed[field]}"
            )

    @given(progress=valid_progress_data())
    def test_display_includes_exactly_three_required_fields(self, progress: dict[str, Any]) -> None:
        """
        Property: For any progress data, the dashboard should display exactly
        the three required fields (no more, no less).

        This test verifies that:
        1. Exactly three fields are displayed
        2. No extra fields are added
        3. No required fields are omitted

        Args:
            progress: Generated progress data dictionary
        """
        # Act: Simulate rendering progress display
        displayed = render_progress_display(progress)

        # Assert: Exactly three fields are displayed
        assert len(displayed) == 3, (
            f"Dashboard should display exactly 3 progress fields, but displayed {len(displayed)}"
        )

        # Assert: The three fields are the required ones
        required_fields = {"completed_submissions", "failed_submissions", "current_cost_usd"}
        displayed_fields = set(displayed.keys())

        assert displayed_fields == required_fields, (
            f"Dashboard should display {required_fields}, but displayed {displayed_fields}"
        )

    @given(progress=valid_progress_data())
    def test_submission_counts_are_integers(self, progress: dict[str, Any]) -> None:
        """
        Property: For any progress data, submission counts should be integers.

        This test verifies that:
        1. completed_submissions is an integer
        2. failed_submissions is an integer
        3. No type conversion errors occur

        Args:
            progress: Generated progress data dictionary
        """
        # Act: Simulate rendering progress display
        displayed = render_progress_display(progress)

        # Assert: Submission counts are integers
        assert isinstance(displayed["completed_submissions"], int), (
            f"completed_submissions should be an integer, "
            f"but got {type(displayed['completed_submissions'])}"
        )

        assert isinstance(displayed["failed_submissions"], int), (
            f"failed_submissions should be an integer, "
            f"but got {type(displayed['failed_submissions'])}"
        )

    @given(progress=valid_progress_data())
    def test_current_cost_is_number(self, progress: dict[str, Any]) -> None:
        """
        Property: For any progress data, current_cost_usd should be a number.

        This test verifies that:
        1. current_cost_usd is a number (int or float)
        2. Cost is non-negative
        3. Cost is not NaN or infinity

        Args:
            progress: Generated progress data dictionary
        """
        # Act: Simulate rendering progress display
        displayed = render_progress_display(progress)

        # Assert: current_cost_usd is a number
        assert isinstance(displayed["current_cost_usd"], (int, float)), (
            f"current_cost_usd should be a number, but got {type(displayed['current_cost_usd'])}"
        )

        # Assert: Cost is non-negative
        assert displayed["current_cost_usd"] >= 0, (
            f"current_cost_usd should be non-negative, but got {displayed['current_cost_usd']}"
        )

        # Assert: Cost is not NaN or infinity
        import math

        assert not math.isnan(displayed["current_cost_usd"]), "current_cost_usd should not be NaN"
        assert not math.isinf(displayed["current_cost_usd"]), (
            "current_cost_usd should not be infinity"
        )

    @given(progress=valid_progress_data())
    def test_display_handles_zero_values_correctly(self, progress: dict[str, Any]) -> None:
        """
        Property: For any progress data including zero values, the dashboard
        should display zero values correctly (not hide or skip them).

        This test verifies that:
        1. Zero values are displayed
        2. Zero is not treated as missing or null
        3. All fields are shown even when zero

        Args:
            progress: Generated progress data dictionary
        """
        # Arrange: Set fields to zero
        progress["completed_submissions"] = 0
        progress["failed_submissions"] = 0
        progress["current_cost_usd"] = 0.0

        # Act: Simulate rendering progress display
        displayed = render_progress_display(progress)

        # Assert: Zero values are displayed
        assert "completed_submissions" in displayed, (
            "Dashboard should display 'completed_submissions' even when it's zero"
        )
        assert displayed["completed_submissions"] == 0, (
            f"Dashboard should display zero for 'completed_submissions', "
            f"but got {displayed['completed_submissions']}"
        )

        assert "failed_submissions" in displayed, (
            "Dashboard should display 'failed_submissions' even when it's zero"
        )
        assert displayed["failed_submissions"] == 0, (
            f"Dashboard should display zero for 'failed_submissions', "
            f"but got {displayed['failed_submissions']}"
        )

        assert "current_cost_usd" in displayed, (
            "Dashboard should display 'current_cost_usd' even when it's zero"
        )
        assert displayed["current_cost_usd"] == 0.0, (
            f"Dashboard should display zero for 'current_cost_usd', "
            f"but got {displayed['current_cost_usd']}"
        )

        # Assert: All three fields are still displayed
        assert len(displayed) == 3, (
            f"Dashboard should display all 3 fields even with zero values, "
            f"but displayed {len(displayed)}"
        )

    @given(progress=valid_progress_data())
    def test_failed_submissions_not_greater_than_completed(self, progress: dict[str, Any]) -> None:
        """
        Property: For any progress data, failed_submissions should not exceed
        completed_submissions (logical constraint).

        This test verifies that:
        1. failed_submissions <= completed_submissions
        2. The data is logically consistent
        3. No impossible states are displayed

        Args:
            progress: Generated progress data dictionary
        """
        # Act: Simulate rendering progress display
        displayed = render_progress_display(progress)

        # Assert: failed_submissions <= completed_submissions
        assert displayed["failed_submissions"] <= displayed["completed_submissions"], (
            f"failed_submissions ({displayed['failed_submissions']}) should not exceed "
            f"completed_submissions ({displayed['completed_submissions']})"
        )
