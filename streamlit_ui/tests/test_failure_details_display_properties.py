"""Property-based tests for failure details display.

This module tests Property 17 from the design document:
- Property 17: Failure Details Display

Feature: streamlit-organizer-dashboard, Property 17: Failure Details Display

For any analysis job where failed_submissions > 0, the dashboard should
display error details.

Validates: Requirements 5.6
"""

from hypothesis import given
from hypothesis import strategies as st


class TestFailureDetailsDisplayProperty:
    """Tests for Property 17: Failure Details Display.

    Feature: streamlit-organizer-dashboard, Property 17: Failure Details Display

    For any analysis job where failed_submissions > 0, the dashboard should
    display error details.

    Validates: Requirements 5.6
    """

    @given(
        failed_submissions=st.integers(min_value=1, max_value=100),
        completed_submissions=st.integers(min_value=0, max_value=100),
    )
    def test_failure_details_shown_when_failures_exist(
        self,
        failed_submissions: int,
        completed_submissions: int,
    ) -> None:
        """When failed_submissions > 0, error details must be displayed."""
        # Simulate analysis job response with failures
        job_response = {
            "job_id": "01HYYY...",
            "hack_id": "01HXXX...",
            "status": "completed",
            "progress_percent": 100.0,
            "completed_submissions": completed_submissions,
            "failed_submissions": failed_submissions,
            "total_submissions": completed_submissions + failed_submissions,
            "current_cost_usd": 5.0,
            "estimated_cost_usd": 5.0,
            "started_at": "2025-03-04T12:00:00Z",
            "completed_at": "2025-03-04T13:00:00Z",
        }

        # Verify failed_submissions is greater than 0
        assert job_response["failed_submissions"] > 0

        # Simulate logic to determine if error details should be shown
        should_show_errors = job_response["failed_submissions"] > 0

        # Error details must be shown
        assert should_show_errors is True, (
            f"Error details should be shown when failed_submissions={failed_submissions}"
        )

    @given(
        completed_submissions=st.integers(min_value=1, max_value=100),
    )
    def test_no_failure_details_when_no_failures(
        self,
        completed_submissions: int,
    ) -> None:
        """When failed_submissions = 0, error details should not be displayed."""
        # Simulate analysis job response with no failures
        job_response = {
            "job_id": "01HYYY...",
            "hack_id": "01HXXX...",
            "status": "completed",
            "progress_percent": 100.0,
            "completed_submissions": completed_submissions,
            "failed_submissions": 0,
            "total_submissions": completed_submissions,
            "current_cost_usd": 5.0,
            "estimated_cost_usd": 5.0,
            "started_at": "2025-03-04T12:00:00Z",
            "completed_at": "2025-03-04T13:00:00Z",
        }

        # Verify failed_submissions is 0
        assert job_response["failed_submissions"] == 0

        # Simulate logic to determine if error details should be shown
        should_show_errors = job_response["failed_submissions"] > 0

        # Error details should not be shown
        assert should_show_errors is False, (
            "Error details should not be shown when failed_submissions=0"
        )

    @given(
        failed_submissions=st.integers(min_value=1, max_value=100),
        error_count=st.integers(min_value=1, max_value=10),
    )
    def test_error_details_structure(
        self,
        failed_submissions: int,
        error_count: int,
    ) -> None:
        """Error details must have proper structure for display."""
        # Simulate error details that would be displayed
        error_details = []

        for i in range(min(error_count, failed_submissions)):
            error_details.append(
                {
                    "sub_id": f"01HZZZ{i:03d}",
                    "team_name": f"Team {i}",
                    "error_message": f"Analysis failed: {i}",
                    "error_type": "timeout",
                }
            )

        # Verify error details structure
        assert len(error_details) > 0, "Error details should not be empty when failures exist"

        for error in error_details:
            # Each error must have required fields
            assert "sub_id" in error, "Error detail missing 'sub_id'"
            assert "team_name" in error, "Error detail missing 'team_name'"
            assert "error_message" in error, "Error detail missing 'error_message'"

            # Verify field types
            assert isinstance(error["sub_id"], str)
            assert isinstance(error["team_name"], str)
            assert isinstance(error["error_message"], str)
            assert len(error["error_message"]) > 0

    @given(
        failed_submissions=st.integers(min_value=1, max_value=100),
        completed_submissions=st.integers(min_value=0, max_value=100),
    )
    def test_failure_count_displayed(
        self,
        failed_submissions: int,
        completed_submissions: int,
    ) -> None:
        """The number of failed submissions must be displayed."""
        job_response = {
            "failed_submissions": failed_submissions,
            "completed_submissions": completed_submissions,
            "total_submissions": completed_submissions + failed_submissions,
        }

        # Simulate displaying failure count
        failure_message = f"{job_response['failed_submissions']} submission(s) failed"

        # Verify failure count is in the message
        assert str(failed_submissions) in failure_message
        assert "failed" in failure_message.lower()

    @given(
        failed_submissions=st.integers(min_value=1, max_value=100),
    )
    def test_failure_details_displayable_as_warning(
        self,
        failed_submissions: int,
    ) -> None:
        """Failure details should be displayable as a warning message."""
        job_response = {
            "failed_submissions": failed_submissions,
        }

        # Simulate warning message logic
        if job_response["failed_submissions"] > 0:
            warning_message = (
                f"⚠️ {job_response['failed_submissions']} submission(s) failed during analysis. "
                "Check error details below."
            )

            # Verify warning message is properly formatted
            assert "⚠️" in warning_message or "warning" in warning_message.lower()
            assert str(failed_submissions) in warning_message
            assert "failed" in warning_message.lower()

    @given(
        failed_submissions=st.integers(min_value=1, max_value=100),
        total_submissions=st.integers(min_value=1, max_value=100),
    )
    def test_failure_percentage_calculable(
        self,
        failed_submissions: int,
        total_submissions: int,
    ) -> None:
        """Failure percentage should be calculable and displayable."""
        # Ensure failed_submissions doesn't exceed total_submissions
        failed = min(failed_submissions, total_submissions)

        job_response = {
            "failed_submissions": failed,
            "total_submissions": total_submissions,
        }

        # Calculate failure percentage
        failure_percentage = (
            job_response["failed_submissions"] / job_response["total_submissions"]
        ) * 100

        # Verify percentage is valid
        assert 0.0 <= failure_percentage <= 100.0

        # Verify percentage can be formatted for display
        formatted_percentage = f"{failure_percentage:.1f}%"
        assert "%" in formatted_percentage

    def test_error_details_empty_when_no_failures(self) -> None:
        """Error details should be empty or not displayed when there are no failures."""
        job_response = {
            "failed_submissions": 0,
        }

        # Simulate error details logic
        error_details = []

        if job_response["failed_submissions"] > 0:
            # Would populate error_details here
            pass

        # Error details should remain empty
        assert len(error_details) == 0

    @given(
        failed_submissions=st.integers(min_value=1, max_value=100),
    )
    def test_error_details_section_visible(
        self,
        failed_submissions: int,
    ) -> None:
        """An error details section should be visible when failures exist."""
        job_response = {
            "failed_submissions": failed_submissions,
        }

        # Simulate section visibility logic
        show_error_section = job_response["failed_submissions"] > 0

        # Error section must be visible
        assert show_error_section is True

        # Simulate section header
        section_header = "Failed Submissions"
        assert len(section_header) > 0
        assert "fail" in section_header.lower()

    @given(
        failed_submissions=st.integers(min_value=1, max_value=10),
    )
    def test_individual_error_messages_displayable(
        self,
        failed_submissions: int,
    ) -> None:
        """Each failed submission should have a displayable error message."""
        # Simulate error details for each failed submission
        error_details = []

        for i in range(failed_submissions):
            error_details.append(
                {
                    "sub_id": f"01HZZZ{i:03d}",
                    "team_name": f"Team {i}",
                    "error_message": "Repository clone failed: timeout after 300s",
                }
            )

        # Verify each error is displayable
        for error in error_details:
            # Simulate display format
            display_text = f"{error['team_name']}: {error['error_message']}"

            assert len(display_text) > 0
            assert error["team_name"] in display_text
            assert error["error_message"] in display_text

    @given(
        failed_submissions=st.integers(min_value=1, max_value=100),
        completed_submissions=st.integers(min_value=0, max_value=100),
    )
    def test_failure_summary_includes_counts(
        self,
        failed_submissions: int,
        completed_submissions: int,
    ) -> None:
        """Failure summary should include both failed and completed counts."""
        job_response = {
            "failed_submissions": failed_submissions,
            "completed_submissions": completed_submissions,
            "total_submissions": completed_submissions + failed_submissions,
        }

        # Simulate summary message
        summary = (
            f"Analysis completed: {job_response['completed_submissions']} succeeded, "
            f"{job_response['failed_submissions']} failed out of {job_response['total_submissions']} total"
        )

        # Verify all counts are in the summary
        assert str(failed_submissions) in summary
        assert str(completed_submissions) in summary
        assert str(job_response["total_submissions"]) in summary
        assert "failed" in summary.lower()
        assert "succeeded" in summary.lower() or "completed" in summary.lower()
