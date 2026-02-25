"""Authentication helpers for Streamlit dashboard."""

import logging

import requests
import streamlit as st

logger = logging.getLogger(__name__)


def validate_api_key(api_key: str, base_url: str) -> bool:
    """Validate API key against backend.

    This function sends a request to the backend's /health endpoint with the
    provided API key to verify that it's valid. The /health endpoint is used
    because it's a lightweight endpoint that requires authentication.

    Args:
        api_key: The API key to validate
        base_url: The base URL of the FastAPI backend (e.g., "http://localhost:8000")

    Returns:
        True if the API key is valid (HTTP 200), False otherwise

    Example:
        >>> validate_api_key("test_key_123", "http://localhost:8000")
        True
    """
    try:
        # Remove trailing slash from base_url if present
        base_url = base_url.rstrip("/")

        # Send GET request to /health endpoint with X-API-Key header
        response = requests.get(f"{base_url}/health", headers={"X-API-Key": api_key}, timeout=5)

        # Return True if status code is 200 (OK)
        is_valid = response.status_code == 200

        if is_valid:
            logger.info("API key validation successful")
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
