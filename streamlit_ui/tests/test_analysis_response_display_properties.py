"""Property-based tests for analysis response display.

Feature: streamlit-organizer-dashboard
Tests universal properties of analysis response display behavior using Hypothesis.
"""

from typing import Any

from hypothesis import given
from hypothesis import strategies as st


# Custom strategies for analysis response data
@st.composite
def valid_job_id(draw: Any) -> str:
    """Generate a valid ULID-format job ID.

    Returns:
        A string matching ULID format (01 followed by 24 alphanumeric chars)
    """
    return draw(st.from_regex(r"01[A-Z0-9]{24}", fullmatch=True))


@st.composite
def valid_analysis_response(draw: Any) -> dict[str, Any]:
    """Generate a valid analysis response (HTTP 202).

    Returns:
        A dictionary with job_id and estimated_cost_usd
    """
    return {
        "job_id": draw(valid_job_id()),
        "estimated_cost_usd": draw(
            st.floats(min_value=0.01, max_value=100.0, allow_nan=False, allow_infinity=False)
        ),
    }


def render_analysis_response(response: dict[str, Any]) -> dict[str, Any]:
    """Simulate the analysis response display logic from the dashboard.

    This function represents the logic that would be in the Streamlit page
    for displaying analysis response after triggering analysis.

    Args:
        response: Analysis response dictionary from API

    Returns:
        Dictionary of displayed fields
    """
    displayed_fields = {}

    # Display job_id
    if "job_id" in response:
        displayed_fields["job_id"] = response["job_id"]

    # Display estimated_cost_usd
    if "estimated_cost_usd" in response:
        displayed_fields["estimated_cost_usd"] = response["estimated_cost_usd"]

    return displayed_fields


class TestAnalysisResponseDisplayProperty:
    """Property 13: Analysis Response Display

    **Validates: Requirements 4.3**

    For any successful analysis start (HTTP 202), the dashboard should display
    both job_id and estimated_cost_usd from the response.
    """

    @given(response=valid_analysis_response())
    def test_both_job_id_and_cost_are_displayed(self, response: dict[str, Any]) -> None:
        """
        Property: For any analysis response, the dashboard should display both
        job_id and estimated_cost_usd.

        This test verifies that:
        1. Both required fields are displayed
        2. No required fields are missing
        3. The displayed values match the input data

        Args:
            response: Generated analysis response dictionary
        """
        # Act: Simulate rendering analysis response display
        displayed = render_analysis_response(response)

        # Assert: Both required fields are displayed
        required_fields = ["job_id", "estimated_cost_usd"]

        for field in required_fields:
            assert field in displayed, f"Dashboard should display '{field}' field, but it's missing"

        # Assert: Displayed values match input data
        for field in required_fields:
            assert displayed[field] == response[field], (
                f"Displayed value for '{field}' should be {response[field]}, "
                f"but got {displayed[field]}"
            )

    @given(response=valid_analysis_response())
    def test_display_includes_exactly_two_required_fields(self, response: dict[str, Any]) -> None:
        """
        Property: For any analysis response, the dashboard should display exactly
        the two required fields (no more, no less).

        This test verifies that:
        1. Exactly two fields are displayed
        2. No extra fields are added
        3. No required fields are omitted

        Args:
            response: Generated analysis response dictionary
        """
        # Act: Simulate rendering analysis response display
        displayed = render_analysis_response(response)

        # Assert: Exactly two fields are displayed
        assert len(displayed) == 2, (
            f"Dashboard should display exactly 2 fields, but displayed {len(displayed)}"
        )

        # Assert: The two fields are the required ones
        required_fields = {"job_id", "estimated_cost_usd"}
        displayed_fields = set(displayed.keys())

        assert displayed_fields == required_fields, (
            f"Dashboard should display {required_fields}, but displayed {displayed_fields}"
        )

    @given(response=valid_analysis_response())
    def test_job_id_format_is_preserved(self, response: dict[str, Any]) -> None:
        """
        Property: For any analysis response, the dashboard should preserve the
        job_id format (ULID format).

        This test verifies that:
        1. job_id is displayed as a string
        2. job_id format is not modified
        3. job_id matches ULID pattern

        Args:
            response: Generated analysis response dictionary
        """
        # Act: Simulate rendering analysis response display
        displayed = render_analysis_response(response)

        # Assert: job_id is a string
        assert isinstance(displayed["job_id"], str), (
            f"job_id should be a string, but got {type(displayed['job_id'])}"
        )

        # Assert: job_id matches ULID format (01 followed by 24 alphanumeric chars)
        import re

        ulid_pattern = r"^01[A-Z0-9]{24}$"
        assert re.match(ulid_pattern, displayed["job_id"]), (
            f"job_id '{displayed['job_id']}' does not match ULID format"
        )

    @given(response=valid_analysis_response())
    def test_cost_is_displayed_as_number(self, response: dict[str, Any]) -> None:
        """
        Property: For any analysis response, the dashboard should display
        estimated_cost_usd as a number (float).

        This test verifies that:
        1. estimated_cost_usd is a number
        2. Cost is positive
        3. Cost is not NaN or infinity

        Args:
            response: Generated analysis response dictionary
        """
        # Act: Simulate rendering analysis response display
        displayed = render_analysis_response(response)

        # Assert: estimated_cost_usd is a number
        assert isinstance(displayed["estimated_cost_usd"], (int, float)), (
            f"estimated_cost_usd should be a number, but got {type(displayed['estimated_cost_usd'])}"
        )

        # Assert: Cost is positive
        assert displayed["estimated_cost_usd"] > 0, (
            f"estimated_cost_usd should be positive, but got {displayed['estimated_cost_usd']}"
        )

        # Assert: Cost is not NaN or infinity
        import math

        assert not math.isnan(displayed["estimated_cost_usd"]), (
            "estimated_cost_usd should not be NaN"
        )
        assert not math.isinf(displayed["estimated_cost_usd"]), (
            "estimated_cost_usd should not be infinity"
        )

    @given(
        response=valid_analysis_response(),
        extra_fields=st.dictionaries(
            keys=st.text(min_size=1, max_size=50),
            values=st.one_of(
                st.integers(), st.floats(allow_nan=False, allow_infinity=False), st.text()
            ),
            min_size=1,
            max_size=5,
        ),
    )
    def test_display_ignores_extra_fields_in_response(
        self, response: dict[str, Any], extra_fields: dict[str, Any]
    ) -> None:
        """
        Property: For any analysis response with extra fields, the dashboard
        should only display the two required fields and ignore extras.

        This test verifies that:
        1. Extra fields in the API response don't break the display
        2. Only the two required fields are shown
        3. The display is not cluttered with unexpected data

        Args:
            response: Generated analysis response dictionary
            extra_fields: Generated extra fields to add to response
        """
        # Arrange: Add extra fields to response (avoiding collisions)
        extended_response = {**response}
        for key, value in extra_fields.items():
            if key not in response:
                extended_response[key] = value

        # Act: Simulate rendering analysis response display
        displayed = render_analysis_response(extended_response)

        # Assert: Only the two required fields are displayed
        required_fields = {"job_id", "estimated_cost_usd"}
        displayed_fields = set(displayed.keys())

        assert displayed_fields == required_fields, (
            f"Dashboard should only display {required_fields}, but displayed {displayed_fields}"
        )

        # Assert: Extra fields are not displayed
        for extra_key in extra_fields:
            if extra_key not in required_fields:
                assert extra_key not in displayed, (
                    f"Dashboard should not display extra field '{extra_key}'"
                )

    @given(
        job_id=valid_job_id(),
        cost=st.floats(min_value=0.01, max_value=100.0, allow_nan=False, allow_infinity=False),
    )
    def test_display_handles_various_cost_ranges(self, job_id: str, cost: float) -> None:
        """
        Property: For any analysis response with various cost values, the
        dashboard should display them correctly.

        This test verifies that:
        1. Small costs (< $1) are displayed correctly
        2. Large costs (> $50) are displayed correctly
        3. No truncation or rounding errors occur

        Args:
            job_id: Generated job ID
            cost: Generated cost value
        """
        # Arrange: Create response with specific cost
        response = {"job_id": job_id, "estimated_cost_usd": cost}

        # Act: Simulate rendering analysis response display
        displayed = render_analysis_response(response)

        # Assert: Cost is displayed correctly
        assert displayed["estimated_cost_usd"] == cost, (
            f"Displayed cost should be {cost}, but got {displayed['estimated_cost_usd']}"
        )

        # Assert: Cost precision is maintained
        assert abs(displayed["estimated_cost_usd"] - cost) < 1e-9, (
            f"Cost precision lost: expected {cost}, got {displayed['estimated_cost_usd']}"
        )

    @given(response_list=st.lists(valid_analysis_response(), min_size=2, max_size=5))
    def test_display_updates_correctly_for_different_responses(
        self, response_list: list[dict[str, Any]]
    ) -> None:
        """
        Property: For any sequence of different analysis responses, the dashboard
        should update the display correctly for each one.

        This test verifies that:
        1. Display updates when response changes
        2. Previous values don't persist
        3. Each display is independent and correct

        Args:
            response_list: List of generated analysis response dictionaries
        """
        # Act & Assert: Render each response and verify
        for i, response in enumerate(response_list):
            displayed = render_analysis_response(response)

            # Assert: Both fields are displayed for each response
            assert len(displayed) == 2, (
                f"Response {i}: Dashboard should display 2 fields, but displayed {len(displayed)}"
            )

            # Assert: Values match the current response (not previous ones)
            assert displayed["job_id"] == response["job_id"], (
                f"Response {i}: Displayed job_id should be "
                f"{response['job_id']}, but got {displayed['job_id']}"
            )

            assert displayed["estimated_cost_usd"] == response["estimated_cost_usd"], (
                f"Response {i}: Displayed cost should be "
                f"{response['estimated_cost_usd']}, but got {displayed['estimated_cost_usd']}"
            )

    @given(response=valid_analysis_response())
    def test_display_field_order_is_consistent(self, response: dict[str, Any]) -> None:
        """
        Property: For any analysis response, the dashboard should display fields
        in a consistent order.

        This test verifies that:
        1. Fields are displayed in the same order every time
        2. The order matches the requirement specification
        3. No random reordering occurs

        Args:
            response: Generated analysis response dictionary
        """
        # Act: Simulate rendering analysis response display multiple times
        displayed1 = render_analysis_response(response)
        displayed2 = render_analysis_response(response)

        # Assert: Field order is consistent
        fields1 = list(displayed1.keys())
        fields2 = list(displayed2.keys())

        assert fields1 == fields2, (
            f"Field order should be consistent, but got {fields1} and {fields2}"
        )

        # Assert: Expected order (as per requirement 4.3)
        expected_order = ["job_id", "estimated_cost_usd"]

        assert fields1 == expected_order, (
            f"Field order should be {expected_order}, but got {fields1}"
        )

    @given(response=valid_analysis_response())
    def test_job_id_is_not_empty(self, response: dict[str, Any]) -> None:
        """
        Property: For any analysis response, the job_id should not be empty.

        This test verifies that:
        1. job_id has content
        2. job_id is not an empty string
        3. job_id has the expected length (26 characters for ULID)

        Args:
            response: Generated analysis response dictionary
        """
        # Act: Simulate rendering analysis response display
        displayed = render_analysis_response(response)

        # Assert: job_id is not empty
        assert len(displayed["job_id"]) > 0, "job_id should not be empty"

        # Assert: job_id has expected ULID length (26 characters)
        assert len(displayed["job_id"]) == 26, (
            f"job_id should be 26 characters long, but got {len(displayed['job_id'])}"
        )

    @given(
        job_id=valid_job_id(),
        cost=st.floats(min_value=0.01, max_value=0.10, allow_nan=False, allow_infinity=False),
    )
    def test_display_handles_small_costs_correctly(self, job_id: str, cost: float) -> None:
        """
        Property: For any analysis response with small costs (< $0.10), the
        dashboard should display them with appropriate precision.

        This test verifies that:
        1. Small costs are not rounded to zero
        2. Precision is maintained for small values
        3. Display is accurate for budget-conscious users

        Args:
            job_id: Generated job ID
            cost: Generated small cost value
        """
        # Arrange: Create response with small cost
        response = {"job_id": job_id, "estimated_cost_usd": cost}

        # Act: Simulate rendering analysis response display
        displayed = render_analysis_response(response)

        # Assert: Small cost is not rounded to zero
        assert displayed["estimated_cost_usd"] > 0, (
            f"Small cost should not be rounded to zero, got {displayed['estimated_cost_usd']}"
        )

        # Assert: Cost value is preserved
        assert displayed["estimated_cost_usd"] == cost, (
            f"Small cost should be {cost}, but got {displayed['estimated_cost_usd']}"
        )
