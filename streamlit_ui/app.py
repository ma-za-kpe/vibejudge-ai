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


def login_with_email_password(email: str, password: str, api_base_url: str) -> tuple[bool, str, str | None]:
    """Login with email and password to get API key.

    Args:
        email: User email address
        password: User password
        api_base_url: API base URL

    Returns:
        Tuple of (success, message, api_key)
    """
    try:
        import requests

        url = f"{api_base_url.rstrip('/')}/organizers/login"
        payload = {"email": email, "password": password}

        logger.info(f"Attempting login for: {email}")
        response = requests.post(url, json=payload, timeout=10)

        if response.status_code == 200:
            data = response.json()
            api_key = data.get("api_key")
            if api_key:
                logger.info(f"Login successful for {email}")
                return True, "Login successful!", api_key
            else:
                logger.error("Login response missing API key")
                return False, "Login failed: No API key returned", None
        elif response.status_code == 401:
            logger.warning(f"Login failed: Invalid credentials for {email}")
            return False, "Invalid email or password", None
        elif response.status_code == 404:
            logger.warning(f"Login failed: Account not found for {email}")
            return False, "Account not found. Please register first.", None
        else:
            error_detail = response.json().get("detail", "Unknown error")
            logger.error(f"Login failed with status {response.status_code}: {error_detail}")
            return False, f"Login failed: {error_detail}", None

    except requests.Timeout:
        logger.error("Login request timed out")
        return False, "Connection timeout. Please check your network.", None
    except requests.ConnectionError:
        logger.error("Login connection error")
        return False, "Cannot connect to server. Please check API URL.", None
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return False, f"Login error: {str(e)}", None


def render_authentication_form() -> None:
    """Render the authentication form with API key and email/password login options."""
    st.title("🎯 VibeJudge AI")
    st.subheader("Organizer Dashboard")

    st.markdown("""
    Welcome to the VibeJudge AI Organizer Dashboard! This platform uses specialized
    AI agents to automatically evaluate hackathon submissions with evidence-based scoring.
    """)

    # Get API base URL (can be configured via environment variable)
    if "api_base_url" not in st.session_state:
        st.session_state["api_base_url"] = get_api_base_url()

    # Create tabs for different login methods
    tab1, tab2 = st.tabs(["🔑 API Key Login", "📧 Email/Password Login"])

    # Tab 1: API Key Login
    with tab1:
        with st.form("api_key_login_form"):
            st.markdown("### Login with API Key")

            # API key input
            api_key = st.text_input(
                "API Key",
                type="password",
                placeholder="vj_live_xxxxxxxxxxxxx",
                help="Your API key from registration or settings",
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
            submit_button = st.form_submit_button("Login with API Key", type="primary", use_container_width=True)

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
                            logger.info("User authenticated successfully with API key")
                            st.success("✅ Authentication successful! Redirecting...")
                            st.rerun()
                        else:
                            st.error("❌ Invalid API key. Please check your credentials and try again.")
                            logger.warning("Authentication failed: Invalid API key")

    # Tab 2: Email/Password Login
    with tab2:
        with st.form("email_password_login_form"):
            st.markdown("### Login with Email & Password")

            # Email and password inputs
            email = st.text_input(
                "Email Address",
                placeholder="organizer@example.com",
                help="Your registered email address",
            )

            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password",
                help="Your account password",
            )

            # Optional: Allow users to override API base URL (useful for development)
            with st.expander("Advanced Settings"):
                api_base_url_email = st.text_input(
                    "API Base URL",
                    value=st.session_state["api_base_url"],
                    placeholder="http://localhost:8000",
                    help="The base URL of the VibeJudge API backend",
                    key="api_base_url_email",
                )

            # Login button
            submit_button_email = st.form_submit_button("Login with Email", type="primary", use_container_width=True)

            # Handle form submission
            if submit_button_email:
                if not email or not password:
                    st.error("Please enter both email and password")
                else:
                    # Show loading spinner while logging in
                    with st.spinner("🔐 Logging in..."):
                        # Update API base URL if changed
                        st.session_state["api_base_url"] = api_base_url_email.rstrip("/")

                        # Login with email/password
                        success, message, api_key = login_with_email_password(
                            email, password, st.session_state["api_base_url"]
                        )

                        if success and api_key:
                            # Store API key in session state
                            st.session_state["api_key"] = api_key
                            logger.info(f"User authenticated successfully with email: {email}")
                            st.success(f"✅ {message}")
                            st.info("💡 Your new API key has been generated and stored in your session.")
                            st.rerun()
                        else:
                            st.error(f"❌ {message}")

    # Links to registration
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**New user?** [Create an account](/0_📝_Register)")
    with col2:
        st.markdown("**Lost your API key?** Use email/password login to get a new one")


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
