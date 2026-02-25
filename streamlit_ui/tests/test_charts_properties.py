"""Property-based tests for charts component.

Feature: streamlit-organizer-dashboard
Tests universal properties of chart rendering behavior using Hypothesis.
"""

from unittest.mock import Mock, patch

from components.charts import create_progress_bar
from hypothesis import given
from hypothesis import strategies as st


class TestProgressBarRenderingProperty:
    """Property 15: Progress Bar Rendering

    **Validates: Requirements 5.2**

    For any progress_percent value between 0 and 100, the dashboard should
    render a progress bar with the correct percentage.
    """

    @given(
        progress_percent=st.floats(
            min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False
        )
    )
    @patch("components.charts.st")
    def test_progress_bar_renders_with_correct_percentage(
        self, mock_st: Mock, progress_percent: float
    ) -> None:
        """
        Property: For any progress_percent value between 0 and 100, the
        create_progress_bar function should call st.progress with the correct
        value in the 0.0-1.0 range.

        This test verifies that:
        1. st.progress is called exactly once
        2. The value passed to st.progress is in the range [0.0, 1.0]
        3. The value is correctly converted from percentage (0-100) to fraction (0-1)
        4. st.caption is called to display the percentage text

        Args:
            mock_st: Mocked Streamlit module
            progress_percent: Generated progress percentage (0-100)
        """
        # Act: Create progress bar
        create_progress_bar(progress_percent)

        # Assert: st.progress was called exactly once
        assert mock_st.progress.call_count == 1, (
            f"st.progress should be called exactly once, but was called {mock_st.progress.call_count} times"
        )

        # Get the value passed to st.progress
        progress_call_args = mock_st.progress.call_args
        assert progress_call_args is not None, "st.progress should have been called with arguments"

        progress_value = progress_call_args[0][0]  # First positional argument

        # Assert: Progress value is in valid range [0.0, 1.0]
        assert 0.0 <= progress_value <= 1.0, (
            f"Progress value {progress_value} should be in range [0.0, 1.0]"
        )

        # Assert: Progress value is correctly converted from percentage
        expected_value = progress_percent / 100.0
        assert abs(progress_value - expected_value) < 1e-6, (
            f"Progress value {progress_value} should equal {expected_value} (progress_percent / 100)"
        )

        # Assert: st.caption was called to display percentage text
        assert mock_st.caption.call_count == 1, (
            f"st.caption should be called exactly once, but was called {mock_st.caption.call_count} times"
        )

        # Verify caption contains the percentage
        caption_call_args = mock_st.caption.call_args
        assert caption_call_args is not None, "st.caption should have been called with arguments"
        caption_text = caption_call_args[0][0]

        assert "Progress:" in caption_text, (
            f"Caption text should contain 'Progress:', but got: {caption_text}"
        )
        assert f"{progress_percent:.1f}%" in caption_text, (
            f"Caption text should contain '{progress_percent:.1f}%', but got: {caption_text}"
        )

    @given(
        progress_percent=st.floats(
            min_value=-1000.0, max_value=0.0, allow_nan=False, allow_infinity=False
        )
    )
    @patch("components.charts.st")
    def test_progress_bar_clamps_negative_values_to_zero(
        self, mock_st: Mock, progress_percent: float
    ) -> None:
        """
        Property: For any negative progress_percent value, the create_progress_bar
        function should clamp it to 0.0 before rendering.

        This test verifies that:
        1. Negative values are clamped to 0.0
        2. st.progress is called with 0.0
        3. The caption displays 0.0%

        Args:
            mock_st: Mocked Streamlit module
            progress_percent: Generated negative progress percentage
        """
        # Act: Create progress bar with negative value
        create_progress_bar(progress_percent)

        # Assert: st.progress was called with 0.0
        progress_call_args = mock_st.progress.call_args
        assert progress_call_args is not None, "st.progress should have been called"

        progress_value = progress_call_args[0][0]

        assert progress_value == 0.0, (
            f"Negative progress {progress_percent} should be clamped to 0.0, but got {progress_value}"
        )

        # Assert: Caption displays 0.0%
        caption_call_args = mock_st.caption.call_args
        assert caption_call_args is not None, "st.caption should have been called"
        caption_text = caption_call_args[0][0]

        assert "0.0%" in caption_text, (
            f"Caption should display '0.0%' for negative input, but got: {caption_text}"
        )

    @given(
        progress_percent=st.floats(
            min_value=100.0, max_value=1000.0, allow_nan=False, allow_infinity=False
        )
    )
    @patch("components.charts.st")
    def test_progress_bar_clamps_over_hundred_to_hundred(
        self, mock_st: Mock, progress_percent: float
    ) -> None:
        """
        Property: For any progress_percent value over 100, the create_progress_bar
        function should clamp it to 100.0 before rendering.

        This test verifies that:
        1. Values over 100 are clamped to 100.0
        2. st.progress is called with 1.0 (100% as fraction)
        3. The caption displays 100.0%

        Args:
            mock_st: Mocked Streamlit module
            progress_percent: Generated progress percentage over 100
        """
        # Act: Create progress bar with value over 100
        create_progress_bar(progress_percent)

        # Assert: st.progress was called with 1.0
        progress_call_args = mock_st.progress.call_args
        assert progress_call_args is not None, "st.progress should have been called"

        progress_value = progress_call_args[0][0]

        assert progress_value == 1.0, (
            f"Progress over 100 ({progress_percent}) should be clamped to 1.0, but got {progress_value}"
        )

        # Assert: Caption displays 100.0%
        caption_call_args = mock_st.caption.call_args
        assert caption_call_args is not None, "st.caption should have been called"
        caption_text = caption_call_args[0][0]

        assert "100.0%" in caption_text, (
            f"Caption should display '100.0%' for input over 100, but got: {caption_text}"
        )

    @given(progress_percent=st.just(0.0))
    @patch("components.charts.st")
    def test_progress_bar_handles_zero_percent(
        self, mock_st: Mock, progress_percent: float
    ) -> None:
        """
        Property: For progress_percent of 0.0, the create_progress_bar function
        should render a progress bar at 0% (empty).

        This test verifies the edge case of 0% progress.

        Args:
            mock_st: Mocked Streamlit module
            progress_percent: 0.0
        """
        # Act: Create progress bar at 0%
        create_progress_bar(progress_percent)

        # Assert: st.progress was called with 0.0
        progress_call_args = mock_st.progress.call_args
        assert progress_call_args is not None, "st.progress should have been called"

        progress_value = progress_call_args[0][0]
        assert progress_value == 0.0, (
            f"Progress value should be 0.0 for 0% input, but got {progress_value}"
        )

        # Assert: Caption displays 0.0%
        caption_call_args = mock_st.caption.call_args
        caption_text = caption_call_args[0][0]
        assert "0.0%" in caption_text, f"Caption should display '0.0%', but got: {caption_text}"

    @given(progress_percent=st.just(100.0))
    @patch("components.charts.st")
    def test_progress_bar_handles_hundred_percent(
        self, mock_st: Mock, progress_percent: float
    ) -> None:
        """
        Property: For progress_percent of 100.0, the create_progress_bar function
        should render a progress bar at 100% (full).

        This test verifies the edge case of 100% progress.

        Args:
            mock_st: Mocked Streamlit module
            progress_percent: 100.0
        """
        # Act: Create progress bar at 100%
        create_progress_bar(progress_percent)

        # Assert: st.progress was called with 1.0
        progress_call_args = mock_st.progress.call_args
        assert progress_call_args is not None, "st.progress should have been called"

        progress_value = progress_call_args[0][0]
        assert progress_value == 1.0, (
            f"Progress value should be 1.0 for 100% input, but got {progress_value}"
        )

        # Assert: Caption displays 100.0%
        caption_call_args = mock_st.caption.call_args
        caption_text = caption_call_args[0][0]
        assert "100.0%" in caption_text, f"Caption should display '100.0%', but got: {caption_text}"

    @given(
        progress_values=st.lists(
            st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
            min_size=2,
            max_size=10,
        )
    )
    @patch("components.charts.st")
    def test_progress_bar_multiple_calls_are_independent(
        self, mock_st: Mock, progress_values: list[float]
    ) -> None:
        """
        Property: For any sequence of progress_percent values, each call to
        create_progress_bar should be independent and render the correct value.

        This test verifies that:
        1. Multiple calls work correctly
        2. Each call renders the correct percentage
        3. Calls don't interfere with each other

        Args:
            mock_st: Mocked Streamlit module
            progress_values: List of generated progress percentages
        """
        # Act: Create multiple progress bars
        for progress_percent in progress_values:
            create_progress_bar(progress_percent)

        # Assert: st.progress was called once for each value
        assert mock_st.progress.call_count == len(progress_values), (
            f"st.progress should be called {len(progress_values)} times, but was called {mock_st.progress.call_count} times"
        )

        # Assert: Each call had the correct value
        progress_calls = mock_st.progress.call_args_list
        for i, progress_percent in enumerate(progress_values):
            expected_value = progress_percent / 100.0
            actual_value = progress_calls[i][0][0]

            assert abs(actual_value - expected_value) < 1e-6, (
                f"Call {i}: expected {expected_value}, but got {actual_value}"
            )

    @given(
        progress_percent=st.floats(
            min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False
        )
    )
    @patch("components.charts.st")
    def test_progress_bar_caption_format_is_consistent(
        self, mock_st: Mock, progress_percent: float
    ) -> None:
        """
        Property: For any progress_percent value, the caption should follow
        a consistent format: "Progress: X.X%"

        This test verifies that:
        1. Caption always starts with "Progress:"
        2. Caption includes the percentage with one decimal place
        3. Caption ends with "%"

        Args:
            mock_st: Mocked Streamlit module
            progress_percent: Generated progress percentage
        """
        # Act: Create progress bar
        create_progress_bar(progress_percent)

        # Assert: Caption follows consistent format
        caption_call_args = mock_st.caption.call_args
        assert caption_call_args is not None, "st.caption should have been called"
        caption_text = caption_call_args[0][0]

        # Check format: "Progress: X.X%"
        assert caption_text.startswith("Progress:"), (
            f"Caption should start with 'Progress:', but got: {caption_text}"
        )
        assert caption_text.endswith("%"), f"Caption should end with '%', but got: {caption_text}"

        # Extract the numeric part and verify it's formatted with one decimal
        import re

        match = re.search(r"Progress:\s+([\d.]+)%", caption_text)
        assert match is not None, (
            f"Caption should match format 'Progress: X.X%', but got: {caption_text}"
        )

        numeric_part = match.group(1)
        # Check that it has exactly one decimal place
        assert "." in numeric_part, (
            f"Percentage should have a decimal point, but got: {numeric_part}"
        )
        decimal_places = len(numeric_part.split(".")[1])
        assert decimal_places == 1, (
            f"Percentage should have exactly 1 decimal place, but got {decimal_places}: {numeric_part}"
        )
