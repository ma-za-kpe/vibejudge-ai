"""VibeJudge AI - Streamlit Organizer Dashboard

Main entry point for the Streamlit dashboard. This page handles authentication
and serves as the gateway to all other dashboard pages.
"""

import logging
import os

import streamlit as st
from components.auth import is_authenticated, logout, validate_api_key

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Page configuration
st.set_page_config(
    page_title="VibeJudge AI - Organizer Dashboard",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)


def get_api_base_url() -> str:
    """Get API base URL from environment variable or use default.

    Returns:
        The API base URL (defaults to http://localhost:8000 if not set)
    """
    return os.getenv("API_BASE_URL", "http://localhost:8000")


def render_authentication_form() -> None:
    """Render the authentication form for API key login."""
    st.title("🎯 VibeJudge AI")
    st.subheader("Organizer Dashboard")

    st.markdown("""
    Welcome to the VibeJudge AI Organizer Dashboard! This platform uses specialized
    AI agents to automatically evaluate hackathon submissions with evidence-based scoring.

    **Please enter your API key to get started.**
    """)

    # Get API base URL (can be configured via environment variable)
    if "api_base_url" not in st.session_state:
        st.session_state["api_base_url"] = get_api_base_url()

    # Create authentication form
    with st.form("login_form"):
        st.markdown("### Authentication")

        # API key input
        api_key = st.text_input(
            "API Key",
            type="password",
            placeholder="Enter your API key",
            help="Your API key can be found in your organizer profile",
        )

        # Optional: Allow users to override API base URL (useful for development)
        with st.expander("Advanced Settings"):
            api_base_url = st.text_input(
                "API Base URL",
                value=st.session_state["api_base_url"],
                placeholder="http://localhost:8000",
                help="The base URL of the VibeJudge API backend",
            )

        # Login button
        submit_button = st.form_submit_button("Login", type="primary", use_container_width=True)

        # Handle form submission
        if submit_button:
            if not api_key:
                st.error("Please enter your API key")
            else:
                # Show loading spinner while validating
                with st.spinner("🔐 Validating API key..."):
                    # Update API base URL if changed
                    st.session_state["api_base_url"] = api_base_url.rstrip("/")

                    # Validate API key
                    if validate_api_key(api_key, st.session_state["api_base_url"]):
                        # Store API key in session state
                        st.session_state["api_key"] = api_key
                        logger.info("User authenticated successfully")
                        st.success("✅ Authentication successful! Redirecting...")
                        st.rerun()
                    else:
                        st.error("❌ Invalid API key. Please check your credentials and try again.")
                        logger.warning("Authentication failed: Invalid API key")


def render_authenticated_home() -> None:
    """Render the home page for authenticated users."""
    st.title("🎯 VibeJudge AI Dashboard")

    st.markdown("""
    ### Welcome to your Organizer Dashboard!

    Use the sidebar to navigate between different sections:

    - **🎯 Create Hackathon**: Set up a new hackathon event
    - **📊 Live Dashboard**: Monitor submissions and trigger analysis
    - **🏆 Results**: View leaderboard and detailed scorecards
    - **💡 Intelligence**: Access hiring insights and technology trends

    ---

    #### Quick Start Guide

    1. **Create a Hackathon**: Start by creating a new hackathon with your custom rubric
    2. **Collect Submissions**: Teams submit their GitHub repository URLs
    3. **Trigger Analysis**: Start the AI analysis when submissions are ready
    4. **Monitor Progress**: Watch real-time progress as agents evaluate submissions
    5. **Review Results**: Explore detailed scorecards and hiring insights

    ---

    #### About VibeJudge AI

    VibeJudge AI uses 4 specialized AI agents on Amazon Bedrock to evaluate code submissions:

    - **BugHunter**: Code quality, security, and testing
    - **PerformanceAnalyzer**: Architecture, scalability, and design
    - **InnovationScorer**: Creativity, novelty, and documentation
    - **AIDetection**: Development authenticity and AI usage patterns

    All evaluations include evidence-based scoring with specific file:line citations,
    ensuring transparent and verifiable results.
    """)

    # Display current API configuration
    with st.expander("ℹ️ Configuration"):
        st.info(f"**API Base URL**: {st.session_state.get('api_base_url', 'Not set')}")
        st.info("**Authenticated**: ✅ Yes")


def render_sidebar() -> None:
    """Render the sidebar with logout button for authenticated users."""
    with st.sidebar:
        st.markdown("### 👤 Account")

        # Display authentication status
        if is_authenticated():
            st.success("✅ Authenticated")

            # Logout button
            if st.button("🚪 Logout", use_container_width=True):
                logout()
                logger.info("User logged out")
                st.rerun()
        else:
            st.warning("⚠️ Not authenticated")

        st.markdown("---")

        # Navigation info
        st.markdown("### 📚 Navigation")
        st.markdown("""
        Use the pages in the sidebar to navigate:
        - 🎯 Create Hackathon
        - 📊 Live Dashboard
        - 🏆 Results
        - 💡 Intelligence
        """)

        st.markdown("---")

        # Help section
        st.markdown("### ❓ Help")
        st.markdown("""
        Need assistance? Check out:
        - [Documentation](#)
        - [API Reference](#)
        - [Support](#)
        """)


def main() -> None:
    """Main application entry point."""
    # Render sidebar
    render_sidebar()

    # Check authentication status
    if is_authenticated():
        # User is authenticated, show home page
        render_authenticated_home()
    else:
        # User is not authenticated, show login form
        render_authentication_form()


if __name__ == "__main__":
    main()
