"""Live Dashboard page for monitoring hackathon statistics in real-time.

Simplified version - backend is source of truth, no caching complexity.
"""

import logging

import requests
import streamlit as st
from components.auth import is_authenticated

logger = logging.getLogger(__name__)


# Page configuration
st.set_page_config(page_title="Live Dashboard", page_icon="📊", layout="wide")


# Authentication check
if not is_authenticated():
    st.error("🔒 Please authenticate first")
    st.info("Go to the Home page to log in with your API key.")
    st.stop()


# Page header
st.title("📊 Live Dashboard")
st.markdown("Monitor your hackathon submissions in real-time.")


# Helper function for API calls
def api_call(endpoint: str, method: str = "GET", json_data: dict | None = None) -> dict | None:
    """Make API call with error handling.

    Args:
        endpoint: API endpoint path (e.g., "/hackathons")
        method: HTTP method (GET, POST)
        json_data: JSON payload for POST requests

    Returns:
        Response JSON or None if error
    """
    try:
        base_url = st.session_state["api_base_url"].rstrip("/")
        headers = {"X-API-Key": st.session_state["api_key"]}
        url = f"{base_url}{endpoint}"

        if method == "GET":
            response = requests.get(url, headers=headers, timeout=60)
        else:
            response = requests.post(url, headers=headers, json=json_data or {}, timeout=60)

        response.raise_for_status()
        return response.json()

    except requests.HTTPError as e:
        status = e.response.status_code

        if status == 401:
            st.error("❌ Invalid API key")
        elif status == 402:
            st.error("💰 Budget limit exceeded")
        elif status == 404:
            st.error("❌ Resource not found")
        elif status == 409:
            st.error("⚠️ Analysis already in progress")
        else:
            try:
                error_detail = e.response.json().get("detail", str(e))
            except:
                error_detail = str(e)
            st.error(f"❌ Error: {error_detail}")

        logger.error(f"API error: {status} - {e}")
        return None

    except requests.Timeout:
        st.error("⏱️ Request timed out. Please try again.")
        return None

    except Exception as e:
        st.error(f"❌ Unexpected error: {e}")
        logger.error(f"Unexpected error: {e}")
        return None


# Fetch hackathons
with st.spinner("🔄 Loading hackathons..."):
    hackathons_response = api_call("/hackathons")

if not hackathons_response:
    if st.button("🔄 Retry"):
        st.rerun()
    st.stop()

hackathons = hackathons_response.get("hackathons", [])

# Filter active hackathons
active_hackathons = [h for h in hackathons if h.get("status") not in ["draft", "archived"]]

if not active_hackathons:
    st.warning("⚠️ No active hackathons found.")
    st.info("💡 Create a hackathon and activate it to start accepting submissions.")
    st.stop()


# Hackathon selection
hackathon_options = {h["name"]: h["hack_id"] for h in active_hackathons}
selected_name = st.selectbox(
    "Select Hackathon",
    options=list(hackathon_options.keys()),
    help="Choose a hackathon to view its statistics",
)
selected_hack_id = hackathon_options[selected_name]


# Statistics section
st.markdown("---")
st.subheader("📈 Statistics")

with st.spinner("📊 Loading statistics..."):
    stats = api_call(f"/hackathons/{selected_hack_id}/stats")

if stats:
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Submissions", stats.get("submission_count", 0))

    with col2:
        st.metric("Verified Submissions", stats.get("verified_count", 0))

    with col3:
        st.metric("Pending Submissions", stats.get("pending_count", 0))

    with col4:
        st.metric("Total Participants", stats.get("participant_count", 0))


# Submissions section
st.markdown("---")
st.subheader("📋 Submissions")

with st.spinner("📥 Loading submissions..."):
    submissions_response = api_call(f"/hackathons/{selected_hack_id}/submissions")

if submissions_response:
    submissions = submissions_response.get("submissions", [])

    if submissions:
        # Display submissions table
        st.markdown(f"**Total: {len(submissions)} submissions**")

        # Table header
        header_col1, header_col2, header_col3, header_col4, header_col5 = st.columns(
            [2, 2, 1.5, 1.5, 1]
        )
        with header_col1:
            st.markdown("**Team Name**")
        with header_col2:
            st.markdown("**Repository**")
        with header_col3:
            st.markdown("**Status**")
        with header_col4:
            st.markdown("**Score**")
        with header_col5:
            st.markdown("**Action**")

        st.divider()

        # Display each submission
        for submission in submissions:
            col1, col2, col3, col4, col5 = st.columns([2, 2, 1.5, 1.5, 1])
            status = submission.get("status", "unknown")
            error_message = submission.get("error_message")
            disqualification_reason = submission.get("disqualification_reason")

            with col1:
                st.markdown(submission.get("team_name", "Unknown"))

            with col2:
                repo_url = submission.get("repo_url", "")
                if repo_url:
                    # Extract repo name from URL
                    repo_name = repo_url.split("/")[-1] if "/" in repo_url else repo_url
                    st.markdown(f"[{repo_name}]({repo_url})")
                else:
                    st.markdown("N/A")

            with col3:
                status_colors = {
                    "pending": "🟡",
                    "analyzing": "🔵",
                    "verified": "🟢",
                    "disqualified": "🔴",
                    "failed": "❌",
                }
                status_icon = status_colors.get(status, "⚪")
                st.markdown(f"{status_icon} {status.title()}")

            with col4:
                score = submission.get("overall_score")
                if score is not None:
                    st.markdown(f"{score:.1f}")
                else:
                    st.markdown("—")

            with col5:
                # Show analyze button only for pending submissions
                if status == "pending":
                    sub_id = submission.get("sub_id")

                    # Check if this submission is being analyzed
                    if (
                        st.session_state.get("analysis_confirmation")
                        and isinstance(st.session_state["analysis_confirmation"], dict)
                        and st.session_state["analysis_confirmation"].get("sub_id") == sub_id
                    ):
                        st.markdown("⏳")
                    else:
                        if st.button("▶️", key=f"analyze_{sub_id}", help="Analyze this submission"):
                            with st.spinner("Preparing..."):
                                st.session_state["analysis_confirmation"] = {
                                    "type": "single",
                                    "sub_id": sub_id,
                                    "team_name": submission.get("team_name"),
                                }
                                st.rerun()

            # Show error details for failed/disqualified submissions
            if status in ["failed", "disqualified"] and (error_message or disqualification_reason):
                with st.expander(f"ℹ️ {submission.get('team_name')} - Error Details"):
                    if disqualification_reason:
                        st.error(f"**Disqualified:** {disqualification_reason}")
                    if error_message:
                        st.warning(f"**Error:** {error_message}")

        st.divider()
    else:
        st.info("📭 No submissions yet.")
else:
    st.warning("⚠️ Could not load submissions.")


# Analysis section
st.markdown("---")
st.subheader("🚀 Bulk Analysis")

# Initialize session state for confirmation workflow
if "analysis_confirmation" not in st.session_state:
    st.session_state["analysis_confirmation"] = None

# Check for active job (backend is source of truth)
job_status = api_call(f"/hackathons/{selected_hack_id}/analyze/status")

if job_status and job_status.get("status") in ["queued", "running"]:
    # Show progress
    st.info(f"📊 Analysis job in progress: {job_status.get('job_id')}")

    progress_data = job_status.get("progress", {})
    progress_percent = progress_data.get("percent_complete", 0)

    st.progress(progress_percent / 100.0)
    st.caption(f"Progress: {progress_percent:.1f}%")

    # Show metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Completed", progress_data.get("completed", 0))

    with col2:
        st.metric("Failed", progress_data.get("failed", 0))

    with col3:
        st.metric("Total", progress_data.get("total_submissions", 0))

    if job_status.get("status") == "completed":
        st.success("✅ Analysis completed!")
        st.balloons()

else:
    # Check if we're in confirmation state
    if st.session_state["analysis_confirmation"]:
        confirmation_data = st.session_state["analysis_confirmation"]

        # Handle both single and bulk analysis confirmations
        if isinstance(confirmation_data, dict) and confirmation_data.get("type") == "single":
            # Single submission analysis
            sub_id = confirmation_data["sub_id"]
            team_name = confirmation_data["team_name"]

            st.info(f"🎯 Analyze submission: **{team_name}**")
            st.caption(f"Submission ID: {sub_id}")

            col1, col2 = st.columns(2)

            with col1:
                if st.button("✅ Confirm & Analyze", type="primary", key="confirm_single_analysis"):
                    with st.spinner("🚀 Starting analysis..."):
                        # Trigger analysis for single submission
                        analysis_response = api_call(
                            f"/hackathons/{selected_hack_id}/analyze",
                            method="POST",
                            json_data={"submission_ids": [sub_id]},
                        )

                    if analysis_response:
                        job_id = analysis_response.get("job_id")
                        st.success("✅ Analysis started!")
                        st.info(f"**Job ID:** {job_id}")
                        st.session_state["analysis_confirmation"] = None
                        st.rerun()
                    else:
                        st.session_state["analysis_confirmation"] = None

            with col2:
                if st.button("❌ Cancel", key="cancel_single_analysis"):
                    st.session_state["analysis_confirmation"] = None
                    st.rerun()

        else:
            # Bulk analysis (all submissions)
            estimated_cost = confirmation_data
            st.info(f"💰 Estimated cost: ${estimated_cost:.2f}")
            st.warning("⚠️ This will analyze ALL pending submissions.")

            col1, col2 = st.columns(2)

            with col1:
                if st.button("✅ Confirm & Start All", type="primary", key="confirm_bulk_analysis"):
                    with st.spinner("🚀 Starting bulk analysis..."):
                        analysis_response = api_call(
                            f"/hackathons/{selected_hack_id}/analyze", method="POST"
                        )

                    if analysis_response:
                        job_id = analysis_response.get("job_id")
                        cost = analysis_response.get("estimated_cost_usd", 0.0)

                        st.success("✅ Bulk analysis started!")
                        st.info(f"**Job ID:** {job_id}")
                        st.info(f"**Estimated Cost:** ${cost:.2f}")
                        st.session_state["analysis_confirmation"] = None
                        st.rerun()
                    else:
                        st.session_state["analysis_confirmation"] = None

            with col2:
                if st.button("❌ Cancel", key="cancel_bulk_analysis"):
                    st.session_state["analysis_confirmation"] = None
                    st.rerun()

    else:
        # No active job - show bulk analyze button
        if st.button("🚀 Analyze All Pending", help="Trigger analysis for all pending submissions"):
            # Get cost estimate
            with st.spinner("💰 Fetching cost estimate..."):
                estimate_response = api_call(
                    f"/hackathons/{selected_hack_id}/analyze/estimate", method="POST"
                )

            if estimate_response:
                # Extract cost and store in session state
                estimate_detail = estimate_response.get("estimate", {})
                total_cost_range = estimate_detail.get("total_cost_usd", {})
                estimated_cost = total_cost_range.get("expected", 0.0)

                st.session_state["analysis_confirmation"] = estimated_cost
                st.rerun()


# Refresh button
st.markdown("---")
if st.button("🔄 Refresh Data"):
    st.rerun()
