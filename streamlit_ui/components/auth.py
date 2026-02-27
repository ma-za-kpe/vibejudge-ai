"""Authentication helpers for Streamlit dashboard."""

import logging

import requests
import streamlit as st

logger = logging.getLogger(__name__)


def validate_api_key(api_key: str, base_url: str) -> bool:
    """Validate API key against backend.

    This function sends a request to the backend's /hackathons endpoint with the
    provided API key to verify that it's valid. The /hackathons endpoint requires
    authentication, so invalid keys will return HTTP 401.

    Args:
        api_key: The API key to validate
        base_url: The base URL of the FastAPI backend (e.g., "http://localhost:8000/api/v1")

    Returns:
        True if the API key is valid (HTTP 200), False otherwise

    Example:
        >>> validate_api_key("test_key_123", "http://localhost:8000/api/v1")
        True
    """
    try:
        # Remove trailing slash from base_url if present
        base_url = base_url.rstrip("/")

        # Use /hackathons endpoint instead of /health (requires authentication)
        # Note: base_url already includes /api/v1 prefix
        response = requests.get(f"{base_url}/hackathons", headers={"X-API-Key": api_key}, timeout=5)

        # Return True if status code is 200 (OK)
        is_valid = response.status_code == 200

        if is_valid:
            logger.info("API key validation successful")
        elif response.status_code == 401:
            logger.warning("API key validation failed: Invalid API key")
        else:
            logger.warning(f"API key validation failed with status {response.status_code}")

        return is_valid

    except requests.Timeout:
        logger.error("API key validation timed out")
        return False

    except requests.ConnectionError:
        logger.error("API key validation failed: Cannot connect to server")
        return False

    except Exception as e:
        logger.error(f"API key validation failed with unexpected error: {e}")
        return False


def is_authenticated() -> bool:
    """Check if user is authenticated.

    This function checks if the user has a valid API key stored in the
    Streamlit session state. It's used throughout the dashboard to protect
    pages that require authentication.

    Returns:
        True if "api_key" exists in st.session_state, False otherwise

    Example:
        >>> if not is_authenticated():
        ...     st.error("Please authenticate first")
        ...     st.stop()
    """
    return "api_key" in st.session_state and st.session_state["api_key"] is not None


def logout() -> None:
    """Clear authentication state.

    This function clears all data from the Streamlit session state, effectively
    logging the user out. After calling this function, is_authenticated() will
    return False and the user will need to authenticate again.

    Example:
        >>> if st.button("Logout"):
        ...     logout()
        ...     st.rerun()
    """
    logger.info("User logged out, clearing session state")
    st.session_state.clear()


def require_authentication(func):
    """Decorator to require authentication for a page.

    This decorator checks if the user is authenticated before allowing access
    to a page. If not authenticated, it displays an error message and stops
    execution.

    Args:
        func: The function to wrap (typically a page's main function)

    Returns:
        The wrapped function that checks authentication first

    Example:
        >>> @require_authentication
        ... def main():
        ...     st.title("Protected Page")
    """
    def wrapper(*args, **kwargs):
        if not is_authenticated():
            st.error("⚠️ Authentication required. Please login first.")
            st.info("👉 Go to the [home page](/) to authenticate.")
            st.stop()
        return func(*args, **kwargs)
    return wrapper
