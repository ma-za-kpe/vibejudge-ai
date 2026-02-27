"""Public Team Submission Portal (No Authentication Required).

This page allows teams to submit their GitHub repositories to hackathons.
No authentication is required - this is a public-facing form.
"""

import logging

import streamlit as st
from components.api_client import APIClient, APIError

logger = logging.getLogger(__name__)


def _validate_github_url(url: str) -> bool:
    """Validate GitHub repository URL format.
    
    Args:
        url: GitHub repository URL to validate
        
    Returns:
        True if URL matches expected format, False otherwise
    """
    import re
    # Match: https://github.com/username/repository (with optional trailing slash)
    pattern = r'^https://github\.com/[\w-]+/[\w.-]+/?$'
    return bool(re.match(pattern, url))


# Page configuration
st.set_page_config(page_title="Submit Your Project", page_icon="🚀", layout="wide")

# Page header
st.title("Submit Your Project")
st.markdown("Submit your team's GitHub repository to participate in the hackathon.")

# Get API base URL from environment or session state
import os

api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")

# Initialize API client without authentication (public endpoint)
api_client = APIClient(api_base_url, api_key="")  # No API key needed for public submission


# Cached function to fetch public hackathons (configured status only)
@st.cache_data(ttl=60)
def fetch_public_hackathons() -> list[dict]:
    """Fetch list of active hackathons accepting submissions."""
    import requests

    try:
        # Use the new public endpoint - no authentication required
        response = requests.get(f"{api_base_url}/public/hackathons", timeout=10)
        if response.ok:
            data = response.json()
            # Handle both list and dict responses
            if isinstance(data, dict):
                hackathons = data.get("hackathons", [])
            else:
                hackathons = data if isinstance(data, list) else []
            return hackathons
        return []
    except Exception as e:
        logger.error(f"Failed to fetch hackathons: {e}")
        return []


# Fetch available hackathons
with st.spinner("Loading available hackathons..."):
    hackathons = fetch_public_hackathons()

if not hackathons:
    st.warning("No hackathons are currently accepting submissions.")
    st.info("Please check back later or contact the organizer for more information.")
    st.stop()

# Display submission form
st.markdown("---")
st.subheader("Submission Form")

with st.form("submission_form"):
    # Hackathon selection
    hackathon_options = {h["name"]: h["hack_id"] for h in hackathons}
    selected_name = st.selectbox(
        "Select Hackathon",
        options=list(hackathon_options.keys()),
        help="Choose the hackathon you're submitting to",
    )

    selected_hack_id = hackathon_options[selected_name]

    # Display hackathon details
    selected_hackathon = next(h for h in hackathons if h["hack_id"] == selected_hack_id)
    with st.expander("View Hackathon Details"):
        st.markdown(f"**Name:** {selected_hackathon.get('name')}")
        st.markdown(f"**Description:** {selected_hackathon.get('description', 'N/A')}")

        # Display dates if available
        start_date = selected_hackathon.get("start_date")
        end_date = selected_hackathon.get("end_date")
        if start_date and end_date:
            st.markdown(f"**Duration:** {start_date} to {end_date}")

    st.markdown("---")

    # Team information
    st.markdown("### Team Information")

    team_name = st.text_input(
        "Team Name *",
        placeholder="Enter your team name",
        help="The name of your team",
    )

    repo_url = st.text_input(
        "GitHub Repository URL *",
        placeholder="https://github.com/username/repository",
        help="Full URL to your GitHub repository (must be public)",
    )

    team_members = st.text_area(
        "Team Members (one per line) *",
        placeholder="Alice Smith\nBob Johnson\nCarol Williams",
        help="Enter team member names, one per line",
        height=150,
    )

    # Optional: Additional information
    with st.expander("Additional Information (Optional)"):
        project_description = st.text_area(
            "Project Description",
            placeholder="Brief description of your project...",
            help="Optional: Describe what your project does",
            height=100,
        )

        technologies_used = st.text_input(
            "Technologies Used",
            placeholder="Python, React, AWS, etc.",
            help="Optional: List the main technologies used in your project",
        )

    st.markdown("---")

    # Terms and conditions
    agree_terms = st.checkbox(
        "I confirm that this submission is our team's original work and complies with the hackathon rules.",
        help="You must agree to submit",
    )

    # Submit button
    submit_button = st.form_submit_button("Submit Project", type="primary", use_container_width=True)

    if submit_button:
        # Validation
        if not team_name or not repo_url or not team_members:
            st.error("Please fill in all required fields (marked with *)")
        elif not agree_terms:
            st.error("You must agree to the terms before submitting")
        elif not repo_url.startswith("https://github.com/"):
            st.error("Please provide a valid GitHub repository URL (must start with https://github.com/)")
        else:
            # Parse team members
            members = [m.strip() for m in team_members.split("\n") if m.strip()]

            if not members:
                st.error("Please enter at least one team member")
            else:
                try:
                    with st.spinner("Submitting your project..."):
                        # Make direct POST request to PUBLIC endpoint (no authentication)
                        import requests

                        response = requests.post(
                            f"{api_base_url}/public/hackathons/{selected_hack_id}/submissions",
                            json={
                                "submissions": [
                                    {
                                        "team_name": team_name,
                                        "repo_url": repo_url,
                                    }
                                ]
                            },
                            timeout=30,
                        )

                        if response.ok:
                            st.success("🎉 Submission successful!")
                            st.balloons()

                            st.markdown("### What's Next?")
                            st.info(
                                """
                                Your submission has been received! Here's what happens next:
                                
                                1. The organizers will verify your repository
                                2. Your project will be analyzed by AI agents
                                3. Results will be published on the leaderboard
                                
                                Thank you for participating!
                                """
                            )

                            # Clear cache to refresh hackathon list
                            st.cache_data.clear()
                        else:
                            error_detail = response.json().get("detail", "Unknown error")
                            st.error(f"Failed to submit: {error_detail}")

                except Exception as e:
                    st.error(f"Failed to submit: {str(e)}")
                    logger.error(f"Submission error: {e}")

# Help section
st.markdown("---")
st.subheader("Need Help?")

with st.expander("Submission Guidelines"):
    st.markdown("""
    **Repository Requirements:**
    - Must be a public GitHub repository
    - Should contain your hackathon project code
    - Include a README.md with project description
    
    **Team Information:**
    - Provide accurate team member names
    - All team members should have contributed to the repository
    
    **After Submission:**
    - You'll receive confirmation immediately
    - Analysis results will be available on the leaderboard
    - Contact the organizer if you need to update your submission
    """)

with st.expander("Frequently Asked Questions"):
    st.markdown("""
    **Q: Can I submit multiple times?**
    A: Contact the hackathon organizer for their specific policy on resubmissions.
    
    **Q: Does my repository need to be public?**
    A: Yes, the repository must be publicly accessible for analysis.
    
    **Q: How long does analysis take?**
    A: Analysis typically completes within a few hours after the submission deadline.
    
    **Q: Can I edit my submission after submitting?**
    A: Contact the hackathon organizer to request changes to your submission.
    """)

st.markdown("---")
st.caption("VibeJudge AI - Automated Hackathon Judging Platform")
