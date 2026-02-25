"""Retry helpers for handling failed API requests.

This module provides utilities for displaying retry buttons and handling
retry logic for failed API requests in the Streamlit dashboard.
"""

from collections.abc import Callable
from typing import Any

import streamlit as st


def retry_button(
    func: Callable[..., Any], button_label: str = "🔄 Retry", *args, **kwargs
) -> Any | None:
    """Display a retry button for failed operations.

    This function creates a retry button that, when clicked, re-executes
    the provided function with the given arguments. It handles the retry
    logic and displays appropriate feedback to the user.

    Args:
        func: The function to retry when the button is clicked
        button_label: The label for the retry button (default: "🔄 Retry")
        *args: Positional arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function

    Returns:
        The result of the function if retry is successful, None otherwise

    Example:
        >>> def fetch_data():
        ...     return api_client.get("/data")
        >>>
        >>> try:
        ...     data = fetch_data()
        ... except APIError as e:
        ...     st.error(f"Failed to fetch data: {e}")
        ...     retry_button(fetch_data)
    """
    if st.button(button_label):
        with st.spinner("Retrying..."):
            try:
                result = func(*args, **kwargs)
                st.success("✅ Success!")
                st.rerun()
                return result
            except Exception as e:
                st.error(f"❌ Retry failed: {e}")
                return None
    return None


def retry_section(
    func: Callable[..., Any], error_message: str, button_label: str = "🔄 Retry", *args, **kwargs
) -> Any | None:
    """Display an error message with a retry button.

    This is a convenience function that combines error display with
    retry functionality. It shows the error message and provides a
    retry button in a single call.

    Args:
        func: The function to retry when the button is clicked
        error_message: The error message to display
        button_label: The label for the retry button (default: "🔄 Retry")
        *args: Positional arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function

    Returns:
        The result of the function if retry is successful, None otherwise

    Example:
        >>> try:
        ...     data = api_client.get("/data")
        ... except APIError as e:
        ...     retry_section(
        ...         lambda: api_client.get("/data"),
        ...         f"Failed to fetch data: {e}"
        ...     )
    """
    st.error(error_message)
    return retry_button(func, button_label, *args, **kwargs)
