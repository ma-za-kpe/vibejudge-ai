"""Live Dashboard page for monitoring hackathon statistics in real-time.

This page allows organizers to:
- Select a hackathon from a dropdown
- View submission statistics (submission_count, verified_count, pending_count, participant_count)
- Monitor statistics with automatic refresh every 5 seconds
"""

import logging
from datetime import datetime

import streamlit as st
from components.api_client import APIClient, APIError, BudgetExceededError, ConflictError
from components.auth import is_authenticated
from components.retry_helpers import retry_button
from streamlit_autorefresh import st_autorefresh

logger = logging.getLogger(__name__)


# Page configuration
st.set_page_config(page_title="Live Dashboard", page_icon="📊", layout="wide")


# Auto-refresh every 5 seconds (5000 milliseconds)
# Returns the number of times the page has refreshed
refresh_count = st_autorefresh(interval=5000, key="live_dashboard_refresh")


# Initialize last refresh timestamp in session state
if "last_refresh" not in st.session_state:
    st.session_state["last_refresh"] = datetime.now()
else:
    # Update timestamp on each refresh
    st.session_state["last_refresh"] = datetime.now()


# Authentication check
if not is_authenticated():
    st.error("🔒 Please authenticate first")
    st.info("Go to the Home page to log in with your API key.")
    st.stop()


# Initialize API client
api_client = APIClient(st.session_state["api_base_url"], st.session_state["api_key"])


# Page header
st.title("📊 Live Dashboard")
st.markdown("Monitor your hackathon submissions in real-time.")

# Display last refresh timestamp
last_refresh_time = st.session_state["last_refresh"].strftime("%Y-%m-%d %H:%M:%S")
st.caption(f"🕐 Last refreshed: {last_refresh_time} (auto-refresh every 5 seconds)")


# Cached function to fetch hackathons list
@st.cache_data(ttl=30)
def fetch_hackathons(api_key: str) -> list[dict]:
    """Fetch list of hackathons from the backend.

    Args:
        api_key: The API key for authentication (used as cache key)

    Returns:
        List of hackathon dictionaries
    """
    client = APIClient(st.session_state["api_base_url"], api_key)
    try:
        response = client.get("/hackathons")
        # API returns {"hackathons": [...], "next_cursor": null, "has_more": false}
        if isinstance(response, dict):
            return response.get("hackathons", [])
        return response if isinstance(response, list) else []
    except APIError as e:
        logger.error(f"Failed to fetch hackathons: {e}")
        st.error(f"❌ Failed to fetch hackathons: {e}")
        retry_button(lambda: st.cache_data.clear() or st.rerun(), "🔄 Retry Loading Hackathons")
        return []


# Cached function to fetch hackathon stats
@st.cache_data(ttl=30)
def fetch_stats(api_key: str, hack_id: str) -> dict | None:
    """Fetch statistics for a specific hackathon.

    Args:
        api_key: The API key for authentication (used as cache key)
        hack_id: The hackathon ID

    Returns:
        Dictionary containing stats or None if error occurred
    """
    client = APIClient(st.session_state["api_base_url"], api_key)
    try:
        return client.get(f"/hackathons/{hack_id}/stats")
    except APIError as e:
        logger.error(f"Failed to fetch stats for {hack_id}: {e}")
        st.error(f"❌ Failed to fetch statistics: {e}")
        return None


# Fetch hackathons for dropdown
with st.spinner("🔄 Loading hackathons..."):
    hackathons = fetch_hackathons(st.session_state["api_key"])

# Filter out DRAFT and ARCHIVED hackathons (only show CONFIGURED, ANALYZING, COMPLETED)
active_hackathons = [
    h for h in hackathons 
    if h.get("status") not in ["draft", "archived"]
]

# Display hackathon selection dropdown
if not active_hackathons:
    st.warning("⚠️ No active hackathons found.")
    st.info("💡 Create a hackathon and activate it to start accepting submissions.")
    st.stop()


# Create dropdown with hackathon names
hackathon_options = {h["name"]: h["hack_id"] for h in active_hackathons}
selected_name = st.selectbox(
    "Select Hackathon",
    options=list(hackathon_options.keys()),
    help="Choose a hackathon to view its statistics",
)


# Get selected hackathon ID
selected_hack_id = hackathon_options[selected_name]


# Store selected hackathon in session state
st.session_state["selected_hackathon"] = selected_hack_id


# Fetch and display stats
st.markdown("---")
st.subheader("📈 Statistics")


with st.spinner("📊 Loading statistics..."):
    stats = fetch_stats(st.session_state["api_key"], selected_hack_id)


if stats:
    # Display stats in columns
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Total Submissions",
            value=stats.get("submission_count", 0),
            help="Total number of submissions received",
        )

    with col2:
        st.metric(
            label="Verified Submissions",
            value=stats.get("verified_count", 0),
            help="Number of submissions with valid repositories",
        )

    with col3:
        st.metric(
            label="Pending Submissions",
            value=stats.get("pending_count", 0),
            help="Number of submissions awaiting verification",
        )

    with col4:
        st.metric(
            label="Total Participants",
            value=stats.get("participant_count", 0),
            help="Total number of participants across all teams",
        )

    # Display additional info if available
    if "analysis_status" in stats:
        st.markdown("---")
        st.info(f"**Analysis Status:** {stats['analysis_status']}")

    if "last_updated" in stats:
        from components.formatters import format_timestamp

        st.caption(f"Last updated: {format_timestamp(stats['last_updated'])}")
else:
    st.error("❌ Failed to load statistics. Please try again.")


# Analysis triggering section
st.markdown("---")
st.subheader("🚀 Analysis")

# Initialize analysis job ID in session state if not present
if "analysis_job_id" not in st.session_state:
    st.session_state["analysis_job_id"] = None

# Initialize cost estimate in session state
if "cost_estimate" not in st.session_state:
    st.session_state["cost_estimate"] = None

# Check if there's an active analysis job
if st.session_state["analysis_job_id"]:
    st.info(f"📊 Analysis job running: {st.session_state['analysis_job_id']}")
    st.caption("View progress in the analysis monitoring section below.")

# Start Analysis button - Step 1: Fetch cost estimate
if st.session_state["cost_estimate"] is None:
    if st.button(
        "🚀 Start Analysis", help="Trigger analysis for all submissions in this hackathon"
    ):
        try:
            # Fetch cost estimate
            with st.spinner("💰 Fetching cost estimate..."):
                estimate_response = api_client.post(
                    f"/hackathons/{selected_hack_id}/estimate", json={}
                )

            estimated_cost = estimate_response.get("estimated_cost_usd", 0.0)

            # Store estimate in session state
            st.session_state["cost_estimate"] = estimated_cost
            st.rerun()

        except BudgetExceededError as e:
            # Handle HTTP 402 during estimate
            st.error(f"💰 {e}")
            st.warning("Cannot estimate cost - budget limit would be exceeded.")

        except APIError as e:
            # Handle errors during cost estimate
            st.error(f"❌ Failed to fetch cost estimate: {e}")
            logger.error(f"Failed to fetch cost estimate for {selected_hack_id}: {e}")

# Step 2: Display cost estimate and confirmation dialog
else:
    estimated_cost = st.session_state["cost_estimate"]
    st.info(f"💰 Estimated cost: ${estimated_cost:.2f}")
    st.warning("⚠️ This will start the analysis process. Do you want to continue?")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ Confirm & Start", type="primary"):
            try:
                # Send POST to start analysis
                with st.spinner("🚀 Starting analysis..."):
                    analysis_response = api_client.post(
                        f"/hackathons/{selected_hack_id}/analyze", json={}
                    )

                # Display job_id and estimated_cost_usd on success (HTTP 202)
                job_id = analysis_response.get("job_id")
                estimated_cost_usd = analysis_response.get("estimated_cost_usd", 0.0)

                # Store job_id in session state
                st.session_state["analysis_job_id"] = job_id

                # Clear cost estimate
                st.session_state["cost_estimate"] = None

                st.success("✅ Analysis started successfully!")
                st.info(f"**Job ID:** {job_id}")
                st.info(f"**Estimated Cost:** ${estimated_cost_usd:.2f}")

                # Clear cache to refresh stats
                st.cache_data.clear()
                st.rerun()

            except BudgetExceededError as e:
                # Handle HTTP 402 - Budget exceeded
                st.error(f"💰 {e}")
                st.warning("Please increase your budget limit or reduce the number of submissions.")
                # Clear cost estimate to allow retry
                st.session_state["cost_estimate"] = None

            except ConflictError as e:
                # Handle HTTP 409 - Analysis already running
                st.error(f"⚠️ {e}")
                st.info(
                    "Please wait for the current analysis to complete before starting a new one."
                )
                # Clear cost estimate
                st.session_state["cost_estimate"] = None

            except APIError as e:
                # Handle other API errors
                st.error(f"❌ Failed to start analysis: {e}")
                logger.error(f"Failed to start analysis for {selected_hack_id}: {e}")
                # Clear cost estimate to allow retry
                st.session_state["cost_estimate"] = None

    with col2:
        if st.button("❌ Cancel"):
            # Clear cost estimate and return to initial state
            st.session_state["cost_estimate"] = None
            st.info("Analysis cancelled.")
            st.rerun()

# Analysis progress monitoring section
if st.session_state["analysis_job_id"]:
    st.markdown("---")
    st.subheader("📊 Analysis Progress")

    try:
        # Poll job status
        with st.spinner("📊 Fetching analysis progress..."):
            job_status = api_client.get(
                f"/hackathons/{selected_hack_id}/jobs/{st.session_state['analysis_job_id']}"
            )

        # Extract job status fields
        status = job_status.get("status", "unknown")
        progress_percent = job_status.get("progress_percent", 0.0)
        completed_submissions = job_status.get("completed_submissions", 0)
        failed_submissions = job_status.get("failed_submissions", 0)
        total_submissions = job_status.get("total_submissions", 0)
        current_cost_usd = job_status.get("current_cost_usd", 0.0)
        estimated_completion = job_status.get("estimated_completion")

        # Display progress bar
        st.progress(progress_percent / 100.0)
        st.caption(f"Progress: {progress_percent:.1f}%")

        # Display submission counts and cost in columns
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                label="Completed",
                value=completed_submissions,
                help="Number of submissions analyzed successfully",
            )

        with col2:
            st.metric(
                label="Failed",
                value=failed_submissions,
                delta=f"-{failed_submissions}" if failed_submissions > 0 else None,
                delta_color="inverse",
                help="Number of submissions that failed analysis",
            )

        with col3:
            st.metric(
                label="Total",
                value=total_submissions,
                help="Total number of submissions to analyze",
            )

        with col4:
            from components.formatters import format_currency

            st.metric(
                label="Current Cost",
                value=format_currency(current_cost_usd),
                help="Cost incurred so far",
            )

        # Display estimated completion time
        if estimated_completion:
            from components.formatters import format_timestamp

            st.info(f"⏱️ Estimated completion: {format_timestamp(estimated_completion)}")

        # Check if analysis is completed
        if status == "completed":
            st.success("✅ Analysis completed successfully!")
            st.balloons()

            # Clear job ID from session state
            st.session_state["analysis_job_id"] = None

            # Clear cache to refresh stats
            st.cache_data.clear()

            # Display final summary
            st.markdown("### 📋 Final Summary")
            st.write(f"- **Total Analyzed:** {completed_submissions}/{total_submissions}")
            st.write(f"- **Failed:** {failed_submissions}")
            st.write(f"- **Total Cost:** {format_currency(current_cost_usd)}")

        # Display error details if there are failures
        elif failed_submissions > 0:
            st.warning(f"⚠️ {failed_submissions} submission(s) failed during analysis")

            # Check if error details are available in the response
            if "error_details" in job_status:
                with st.expander("View Error Details"):
                    error_details = job_status["error_details"]
                    if isinstance(error_details, list):
                        for error in error_details:
                            st.error(f"- {error}")
                    else:
                        st.error(str(error_details))

        # Display status badge
        if status == "running":
            st.info("🔄 Analysis is currently running...")
        elif status == "failed":
            st.error("❌ Analysis job failed")
            # Clear job ID to allow retry
            st.session_state["analysis_job_id"] = None

    except APIError as e:
        st.error(f"❌ Failed to fetch job status: {e}")
        logger.error(f"Failed to fetch job status for {st.session_state['analysis_job_id']}: {e}")

        # Offer retry button
        if st.button("🔄 Retry Job Status"):
            st.rerun()

# Manual refresh button
st.markdown("---")
if st.button("🔄 Refresh Now"):
    # Clear cache to force refresh
    st.cache_data.clear()
    st.rerun()
