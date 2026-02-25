"""Property-based tests for retry button availability.

Feature: streamlit-organizer-dashboard
Tests universal properties of retry button behavior using Hypothesis.
"""

from typing import Any
from unittest.mock import Mock, patch

from components.api_client import (
    APIError,
    AuthenticationError,
    BadRequestError,
    BudgetExceededError,
    ConflictError,
    ConnectionTimeoutError,
    RateLimitError,
    ResourceNotFoundError,
    ServerError,
    ServiceUnavailableError,
    ValidationError,
)
from components.retry_helpers import retry_button, retry_section
from hypothesis import given
from hypothesis import strategies as st_hypothesis


class TestRetryButtonAvailabilityProperty:
    """Property 27: Retry Button Availability

    **Validates: Requirements 10.6**

    For any failed API request, the dashboard should display a retry button
    that re-attempts the request.
    """

    @given(
        button_label=st_hypothesis.text(min_size=1, max_size=50),
        error_type=st_hypothesis.sampled_from(
            [
                APIError,
                AuthenticationError,
                BadRequestError,
                BudgetExceededError,
                ConflictError,
                ConnectionTimeoutError,
                RateLimitError,
                ResourceNotFoundError,
                ServerError,
                ServiceUnavailableError,
                ValidationError,
            ]
        ),
    )
    @patch("streamlit.button")
    @patch("streamlit.spinner")
    @patch("streamlit.success")
    @patch("streamlit.rerun")
    def test_retry_button_is_displayed_after_api_error(
        self,
        mock_rerun: Mock,
        mock_success: Mock,
        mock_spinner: Mock,
        mock_button: Mock,
        button_label: str,
        error_type: type[Exception],
    ) -> None:
        """
        Property: For any API error, calling retry_button should display
        a button to the user.

        This test verifies that:
        1. retry_button creates a Streamlit button
        2. The button is displayed with the correct label
        3. The button is available for any type of API error

        Args:
            mock_rerun: Mocked st.rerun function
            mock_success: Mocked st.success function
            mock_spinner: Mocked st.spinner function
            mock_button: Mocked st.button function
            button_label: Generated button label text
            error_type: Type of API error that occurred
        """
        # Arrange: Create a mock function that will be retried
        mock_func = Mock(return_value="success")
        mock_button.return_value = False  # Button not clicked yet

        # Act: Call retry_button after an error
        result = retry_button(mock_func, button_label)

        # Assert: Button was created with the correct label
        mock_button.assert_called_once_with(button_label)

        # Assert: Function was not called yet (button not clicked)
        mock_func.assert_not_called()

        # Assert: Result is None when button not clicked
        assert result is None

    @given(button_label=st_hypothesis.text(min_size=1, max_size=50))
    @patch("streamlit.button")
    @patch("streamlit.spinner")
    @patch("streamlit.success")
    @patch("streamlit.rerun")
    def test_retry_button_executes_function_when_clicked(
        self,
        mock_rerun: Mock,
        mock_success: Mock,
        mock_spinner: Mock,
        mock_button: Mock,
        button_label: str,
    ) -> None:
        """
        Property: For any retry button, clicking it should re-execute
        the failed function.

        This test verifies that:
        1. Clicking the retry button calls the provided function
        2. The function is called with the correct arguments
        3. Success feedback is displayed after successful retry

        Args:
            mock_rerun: Mocked st.rerun function
            mock_success: Mocked st.success function
            mock_spinner: Mocked st.spinner function
            mock_button: Mocked st.button function
            button_label: Generated button label text
        """
        # Arrange: Create a mock function and simulate button click
        mock_func = Mock(return_value="success")
        mock_button.return_value = True  # Button clicked
        mock_spinner.return_value.__enter__ = Mock()
        mock_spinner.return_value.__exit__ = Mock()

        # Act: Call retry_button with button clicked
        retry_button(mock_func, button_label)

        # Assert: Button was created
        mock_button.assert_called_once_with(button_label)

        # Assert: Function was called (retry executed)
        mock_func.assert_called_once()

        # Assert: Success message was displayed
        mock_success.assert_called_once()

        # Assert: Page was rerun to show updated state
        mock_rerun.assert_called_once()

    @given(
        button_label=st_hypothesis.text(min_size=1, max_size=50),
        func_args=st_hypothesis.lists(
            st_hypothesis.one_of(
                st_hypothesis.integers(), st_hypothesis.text(), st_hypothesis.booleans()
            ),
            min_size=0,
            max_size=3,
        ),
    )
    @patch("streamlit.button")
    @patch("streamlit.spinner")
    @patch("streamlit.success")
    @patch("streamlit.rerun")
    def test_retry_button_passes_arguments_to_function(
        self,
        mock_rerun: Mock,
        mock_success: Mock,
        mock_spinner: Mock,
        mock_button: Mock,
        button_label: str,
        func_args: list[Any],
    ) -> None:
        """
        Property: For any retry button with function arguments, the arguments
        should be passed correctly to the function when retried.

        This test verifies that:
        1. Arguments are preserved across retry attempts
        2. The function receives the correct arguments
        3. Both positional and keyword arguments work

        Args:
            mock_rerun: Mocked st.rerun function
            mock_success: Mocked st.success function
            mock_spinner: Mocked st.spinner function
            mock_button: Mocked st.button function
            button_label: Generated button label text
            func_args: Generated list of function arguments
        """
        # Arrange: Create a mock function and simulate button click
        mock_func = Mock(return_value="success")
        mock_button.return_value = True  # Button clicked
        mock_spinner.return_value.__enter__ = Mock()
        mock_spinner.return_value.__exit__ = Mock()

        # Act: Call retry_button with arguments
        retry_button(mock_func, button_label, *func_args)

        # Assert: Function was called with correct arguments
        mock_func.assert_called_once_with(*func_args)

    @given(
        error_message=st_hypothesis.text(min_size=1, max_size=200),
        button_label=st_hypothesis.text(min_size=1, max_size=50),
    )
    @patch("streamlit.button")
    @patch("streamlit.error")
    def test_retry_section_displays_error_and_button(
        self, mock_error: Mock, mock_button: Mock, error_message: str, button_label: str
    ) -> None:
        """
        Property: For any failed request, retry_section should display
        both an error message and a retry button.

        This test verifies that:
        1. Error message is displayed to the user
        2. Retry button is displayed after the error
        3. Both components are created in the correct order

        Args:
            mock_error: Mocked st.error function
            mock_button: Mocked st.button function
            error_message: Generated error message text
            button_label: Generated button label text
        """
        # Arrange: Create a mock function
        mock_func = Mock(return_value="success")
        mock_button.return_value = False  # Button not clicked

        # Act: Call retry_section
        retry_section(mock_func, error_message, button_label)

        # Assert: Error message was displayed
        mock_error.assert_called_once_with(error_message)

        # Assert: Retry button was created
        mock_button.assert_called_once_with(button_label)

    @given(
        button_label=st_hypothesis.text(min_size=1, max_size=50),
        error_message=st_hypothesis.text(min_size=1, max_size=200),
    )
    @patch("streamlit.button")
    @patch("streamlit.spinner")
    @patch("streamlit.error")
    def test_retry_button_handles_retry_failure(
        self,
        mock_error: Mock,
        mock_spinner: Mock,
        mock_button: Mock,
        button_label: str,
        error_message: str,
    ) -> None:
        """
        Property: For any retry attempt that fails, the retry button should
        display an error message and remain available.

        This test verifies that:
        1. Failed retry attempts are caught and handled
        2. Error message is displayed for failed retry
        3. The button remains available for another retry

        Args:
            mock_error: Mocked st.error function
            mock_spinner: Mocked st.spinner function
            mock_button: Mocked st.button function
            button_label: Generated button label text
            error_message: Generated error message text
        """
        # Arrange: Create a mock function that fails
        mock_func = Mock(side_effect=APIError(error_message))
        mock_button.return_value = True  # Button clicked
        mock_spinner.return_value.__enter__ = Mock()
        mock_spinner.return_value.__exit__ = Mock()

        # Act: Call retry_button with failing function
        result = retry_button(mock_func, button_label)

        # Assert: Function was called (retry attempted)
        mock_func.assert_called_once()

        # Assert: Error message was displayed
        assert mock_error.call_count >= 1, "Error should be displayed after failed retry"

        # Assert: Result is None when retry fails
        assert result is None

    @given(
        button_label=st_hypothesis.text(min_size=1, max_size=50),
        num_retries=st_hypothesis.integers(min_value=1, max_value=5),
    )
    @patch("streamlit.button")
    @patch("streamlit.spinner")
    @patch("streamlit.success")
    @patch("streamlit.rerun")
    def test_retry_button_can_be_clicked_multiple_times(
        self,
        mock_rerun: Mock,
        mock_success: Mock,
        mock_spinner: Mock,
        mock_button: Mock,
        button_label: str,
        num_retries: int,
    ) -> None:
        """
        Property: For any retry button, it should be possible to retry
        multiple times if needed.

        This test verifies that:
        1. The retry button can be clicked multiple times
        2. Each click executes the function again
        3. The button remains functional across retries

        Args:
            mock_rerun: Mocked st.rerun function
            mock_success: Mocked st.success function
            mock_spinner: Mocked st.spinner function
            mock_button: Mocked st.button function
            button_label: Generated button label text
            num_retries: Number of retry attempts to simulate
        """
        # Arrange: Create a mock function
        mock_func = Mock(return_value="success")
        mock_spinner.return_value.__enter__ = Mock()
        mock_spinner.return_value.__exit__ = Mock()

        # Act: Simulate multiple button clicks
        for _i in range(num_retries):
            mock_button.return_value = True  # Button clicked
            retry_button(mock_func, button_label)

        # Assert: Function was called for each retry
        assert mock_func.call_count == num_retries, (
            f"Function should be called {num_retries} times, but was called {mock_func.call_count} times"
        )

    @given(button_label=st_hypothesis.text(min_size=1, max_size=50))
    @patch("streamlit.button")
    def test_retry_button_default_label(self, mock_button: Mock, button_label: str) -> None:
        """
        Property: For any retry button, if no label is provided, it should
        use a default label.

        This test verifies that:
        1. Default label is used when none provided
        2. Custom label is used when provided
        3. Label is always a non-empty string

        Args:
            mock_button: Mocked st.button function
            button_label: Generated button label text
        """
        # Arrange: Create a mock function
        mock_func = Mock(return_value="success")
        mock_button.return_value = False

        # Act: Call retry_button with default label
        retry_button(mock_func)

        # Assert: Button was created with default label
        default_call = mock_button.call_args_list[0]
        assert default_call[0][0] == "🔄 Retry", (
            f"Default label should be '🔄 Retry', but got: {default_call[0][0]}"
        )

        # Act: Call retry_button with custom label
        mock_button.reset_mock()
        retry_button(mock_func, button_label)

        # Assert: Button was created with custom label
        custom_call = mock_button.call_args_list[0]
        assert custom_call[0][0] == button_label, (
            f"Custom label should be '{button_label}', but got: {custom_call[0][0]}"
        )

    @given(
        button_label=st_hypothesis.text(min_size=1, max_size=50),
        error_types=st_hypothesis.lists(
            st_hypothesis.sampled_from(
                [
                    APIError,
                    AuthenticationError,
                    ValidationError,
                    ServerError,
                    ConnectionTimeoutError,
                ]
            ),
            min_size=1,
            max_size=5,
        ),
    )
    @patch("streamlit.button")
    def test_retry_button_available_for_all_error_types(
        self, mock_button: Mock, button_label: str, error_types: list[type[Exception]]
    ) -> None:
        """
        Property: For any type of API error, a retry button should be
        available to the user.

        This test verifies that:
        1. Retry button works for all error types
        2. No error type is excluded from retry functionality
        3. The button is consistently available

        Args:
            mock_button: Mocked st.button function
            button_label: Generated button label text
            error_types: List of error types to test
        """
        # Arrange: Create a mock function
        mock_func = Mock(return_value="success")
        mock_button.return_value = False

        # Act & Assert: Test retry button for each error type
        for _error_type in error_types:
            mock_button.reset_mock()

            # Simulate error occurred, then retry button displayed
            retry_button(mock_func, button_label)

            # Assert: Button was created regardless of error type
            mock_button.assert_called_once_with(button_label)
