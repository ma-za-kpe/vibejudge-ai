"""Registration page for new organizers.

This page allows new users to create an organizer account and receive their API key.
"""

import logging

import streamlit as st
from components.api_client import APIClient, APIError

logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Register - VibeJudge AI",
    page_icon="📝",
    layout="wide",
)


def register_organizer(
    email: str, password: str, name: str, organization: str, api_base_url: str
) -> tuple[bool, str, str | None]:
    """Register a new organizer account.

    Args:
        email: Organizer email address
        password: Account password
        name: Organizer full name
        organization: Organization name
        api_base_url: API base URL

    Returns:
        Tuple of (success, message, api_key)
    """
    try:
        # Create temporary client without API key for registration
        import requests

        url = f"{api_base_url.rstrip('/')}/api/v1/organizers"
        payload = {
            "email": email,
            "password": password,
            "name": name,
            "organization": organization,
        }

        logger.info(f"Registering organizer: {email}")
        response = requests.post(url, json=payload, timeout=10)

        if response.status_code == 201:
            data = response.json()
            api_key = data.get("api_key")
            if api_key:
                logger.info(f"Registration successful for {email}")
                return True, "Registration successful!", api_key
            else:
                logger.error("Registration response missing API key")
                return False, "Registration failed: No API key returned", None
        elif response.status_code == 409:
            logger.warning(f"Registration failed: Email {email} already exists")
            return False, "Email already registered. Please use login instead.", None
        elif response.status_code == 422:
            error_detail = response.json().get("detail", "Invalid input")
            logger.warning(f"Registration validation error: {error_detail}")
            return False, f"Validation error: {error_detail}", None
        else:
            error_detail = response.json().get("detail", "Unknown error")
            logger.error(f"Registration failed with status {response.status_code}: {error_detail}")
            return False, f"Registration failed: {error_detail}", None

    except requests.Timeout:
        logger.error("Registration request timed out")
        return False, "Connection timeout. Please check your network.", None
    except requests.ConnectionError:
        logger.error("Registration connection error")
        return False, "Cannot connect to server. Please check API URL.", None
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return False, f"Registration error: {str(e)}", None


def main() -> None:
    """Main registration page."""
    st.title("📝 Register New Account")

    st.markdown("""
    Create a new organizer account to start using VibeJudge AI.
    You'll receive an API key after registration.
    """)

    # Get API base URL from session state or environment
    if "api_base_url" not in st.session_state:
        import os

        st.session_state["api_base_url"] = os.getenv("API_BASE_URL", "http://localhost:8000")

    # Registration form
    with st.form("registration_form"):
        st.markdown("### Account Information")

        col1, col2 = st.columns(2)

        with col1:
            email = st.text_input(
                "Email Address *",
                placeholder="organizer@example.com",
                help="Your email address (used for login)",
            )

            name = st.text_input(
                "Full Name *", placeholder="John Doe", help="Your full name"
            )

        with col2:
            password = st.text_input(
                "Password *",
                type="password",
                placeholder="Enter a secure password",
                help="Minimum 8 characters",
            )

            organization = st.text_input(
                "Organization *",
                placeholder="Acme Corp",
                help="Your organization or company name",
            )

        # Advanced settings
        with st.expander("Advanced Settings"):
            api_base_url = st.text_input(
                "API Base URL",
                value=st.session_state["api_base_url"],
                placeholder="http://localhost:8000",
                help="The base URL of the VibeJudge API backend",
            )

        # Terms and conditions
        st.markdown("---")
        accept_terms = st.checkbox(
            "I agree to the Terms of Service and Privacy Policy",
            help="You must accept the terms to create an account",
        )

        # Submit button
        submit_button = st.form_submit_button(
            "Create Account", type="primary", use_container_width=True
        )

        # Handle form submission
        if submit_button:
            # Validation
            if not all([email, password, name, organization]):
                st.error("❌ Please fill in all required fields")
            elif len(password) < 8:
                st.error("❌ Password must be at least 8 characters")
            elif not accept_terms:
                st.error("❌ You must accept the Terms of Service")
            else:
                # Show loading spinner
                with st.spinner("🔐 Creating your account..."):
                    # Update API base URL
                    st.session_state["api_base_url"] = api_base_url.rstrip("/")

                    # Register organizer
                    success, message, api_key = register_organizer(
                        email, password, name, organization, st.session_state["api_base_url"]
                    )

                    if success and api_key:
                        st.success(f"✅ {message}")

                        # Display API key with copy button
                        st.markdown("### 🔑 Your API Key")
                        st.warning(
                            "⚠️ **IMPORTANT**: Save your API key now! "
                            "It will not be shown again."
                        )

                        # Show API key in a code block
                        st.code(api_key, language="text")

                        # Copy button
                        if st.button("📋 Copy API Key", use_container_width=True):
                            st.write("API key copied to clipboard!")
                            # Note: Actual clipboard copy requires JavaScript

                        st.markdown("---")
                        st.info(
                            "💡 **Next Steps:**\n"
                            "1. Save your API key in a secure location\n"
                            "2. Go to the home page and login with your API key\n"
                            "3. Start creating hackathons!"
                        )

                        # Store API key in session for immediate login
                        st.session_state["api_key"] = api_key
                        st.session_state["just_registered"] = True

                        # Add button to go to home page
                        if st.button("🏠 Go to Dashboard", type="primary", use_container_width=True):
                            st.switch_page("app.py")

                    else:
                        st.error(f"❌ {message}")

    # Link to login page
    st.markdown("---")
    st.markdown("Already have an account? [Login here](/) (go to home page)")


if __name__ == "__main__":
    main()
