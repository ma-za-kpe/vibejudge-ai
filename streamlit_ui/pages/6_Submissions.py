"""Submissions Management page for viewing and managing submissions.

This page allows organizers to:
- View all submissions for a hackathon
- See submission status (pending, analyzing, completed, failed)
- Manually add submissions
- Delete submissions
- Filter by status, sort by date/team name
"""

import logging
from datetime import datetime

import streamlit as st
from components.api_client import APIClient, APIError
from components.auth import is_authenticated

logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(page_title="Submissions", page_icon="📝", layout="wide")

# Authentication check
if not is_authenticated():
    st.error("Please authenticate first")
    st.info("Go to the Home page to log in with your API key.")
    st.stop()

# Initialize API client
api_client = APIClient(st.session_state["api_base_url"], st.session_state["api_key"])

# Page header
st.title("Submissions Management")
st.markdown("View and manage submissions for your hackathons.")


# Cached function to fetch hackathons list
@st.cache_data(ttl=30)
def fetch_hackathons(api_key: str) -> list[dict]:
    """Fetch list of hackathons from the backend."""
    client = APIClient(st.session_state["api_base_url"], api_key)
    try:
        response = client.get("/hackathons")
        # API returns {"hackathons": [...], "next_cursor": null, "has_more": false}
        if isinstance(response, dict):
            return response.get("hackathons", [])
        return response if isinstance(response, list) else []
    except APIError as e:
        logger.error(f"Failed to fetch hackathons: {e}")
        st.error(f"Failed to fetch hackathons: {e}")
        return []


# Cached function to fetch submissions
@st.cache_data(ttl=30)
def fetch_submissions(api_key: str, hack_id: str) -> list[dict]:
    """Fetch submissions for a specific hackathon."""
    # Use longer timeout for submissions endpoint (can be slow with many submissions)
    client = APIClient(st.session_state["api_base_url"], api_key, timeout=30)
    try:
        response = client.get(f"/hackathons/{hack_id}/submissions")
        return response.get("submissions", []) if isinstance(response, dict) else []
    except APIError as e:
        logger.error(f"Failed to fetch submissions: {e}")
        st.error(f"Failed to fetch submissions: {e}")
        return []


# Fetch hackathons for dropdown
with st.spinner("Loading hackathons..."):
    hackathons = fetch_hackathons(st.session_state["api_key"])

# Filter active hackathons
active_hackathons = [h for h in hackathons if h.get("status") not in ["draft", "archived"]]

if not active_hackathons:
    st.warning("No active hackathons found.")
    st.info("Create a hackathon and activate it to start accepting submissions.")
    st.stop()

# Hackathon selection
hackathon_options = {h["name"]: h["hack_id"] for h in active_hackathons}
selected_name = st.selectbox(
    "Select Hackathon",
    options=list(hackathon_options.keys()),
    help="Choose a hackathon to view its submissions",
)

selected_hack_id = hackathon_options[selected_name]

# Add submission section
st.markdown("---")
st.subheader("Add New Submission")

with st.form("add_submission_form"):
    col1, col2 = st.columns(2)

    with col1:
        team_name = st.text_input(
            "Team Name",
            placeholder="Enter team name",
            help="Name of the team submitting",
        )

    with col2:
        repo_url = st.text_input(
            "GitHub Repository URL",
            placeholder="https://github.com/username/repo",
            help="Full URL to the GitHub repository",
        )

    team_members = st.text_area(
        "Team Members (one per line)",
        placeholder="Alice Smith\nBob Johnson\nCarol Williams",
        help="Enter team member names, one per line",
    )

    submit_button = st.form_submit_button("Add Submission", type="primary")

    if submit_button:
        if not team_name or not repo_url:
            st.error("Team name and repository URL are required")
        else:
            # Parse team members
            members = [m.strip() for m in team_members.split("\n") if m.strip()]

            try:
                with st.spinner("Adding submission..."):
                    api_client.post(
                        f"/hackathons/{selected_hack_id}/submissions",
                        json={
                            "submissions": [
                                {
                                    "team_name": team_name,
                                    "repo_url": repo_url,
                                    "team_members": members,
                                }
                            ]
                        },
                    )
                st.success("Submission added successfully!")
                st.cache_data.clear()
                st.rerun()
            except APIError as e:
                st.error(f"Failed to add submission: {e}")

# View submissions section
st.markdown("---")
st.subheader("Submissions")

# Fetch submissions
with st.spinner("Loading submissions..."):
    submissions = fetch_submissions(st.session_state["api_key"], selected_hack_id)

if not submissions:
    st.info("No submissions found for this hackathon.")
    st.stop()

# Filter and sort controls
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    search_query = st.text_input(
        "Search by team name",
        placeholder="Enter team name...",
        help="Filter submissions by team name (case-insensitive)",
    )

with col2:
    status_filter = st.selectbox(
        "Filter by status",
        options=["all", "pending", "analyzing", "completed", "failed"],
        format_func=lambda x: x.title(),
        help="Filter submissions by status",
    )

with col3:
    sort_option = st.selectbox(
        "Sort by",
        options=["created_at", "team_name", "status"],
        format_func=lambda x: {
            "created_at": "Date",
            "team_name": "Team Name",
            "status": "Status",
        }[x],
        help="Sort submissions by selected field",
    )

# Apply filters
filtered_submissions = submissions
if search_query:
    filtered_submissions = [
        s for s in filtered_submissions if search_query.lower() in s.get("team_name", "").lower()
    ]
if status_filter != "all":
    filtered_submissions = [s for s in filtered_submissions if s.get("status") == status_filter]

# Apply sorting
if sort_option == "created_at":
    filtered_submissions = sorted(
        filtered_submissions, key=lambda x: x.get("created_at", ""), reverse=True
    )
elif sort_option == "team_name":
    filtered_submissions = sorted(
        filtered_submissions, key=lambda x: x.get("team_name", "").lower()
    )
elif sort_option == "status":
    filtered_submissions = sorted(filtered_submissions, key=lambda x: x.get("status", ""))

if not filtered_submissions:
    st.warning("No submissions found matching your filters.")
else:
    # Display table header
    header_col1, header_col2, header_col3, header_col4, header_col5, header_col6 = st.columns(
        [2, 1.5, 1, 1, 1, 1]
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
        st.markdown("**Submitted**")
    with header_col6:
        st.markdown("**Actions**")

    st.divider()

    # Display each submission
    for submission in filtered_submissions:
        sub_id = submission.get("sub_id", "")
        team_name = submission.get("team_name", "Unknown")
        repo_url = submission.get("repo_url", "")
        status = submission.get("status", "unknown")
        overall_score = submission.get("overall_score")
        created_at = submission.get("created_at", "")

        # Format created date
        try:
            created_date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            formatted_date = created_date.strftime("%Y-%m-%d")
        except Exception:
            formatted_date = "N/A"

        # Extract repo name from URL
        repo_name = repo_url.split("/")[-1] if repo_url else "N/A"

        col1, col2, col3, col4, col5, col6 = st.columns([2, 1.5, 1, 1, 1, 1])

        with col1:
            st.markdown(f"{team_name}")

        with col2:
            if repo_url:
                st.markdown(f"[{repo_name}]({repo_url})")
            else:
                st.markdown("N/A")

        with col3:
            # Status badge with color
            status_colors = {
                "pending": "🟡",
                "analyzing": "🔵",
                "completed": "✅",
                "failed": "❌",
            }
            status_icon = status_colors.get(status, "⚪")
            st.markdown(f"{status_icon} {status.title()}")

        with col4:
            if overall_score is not None:
                st.markdown(f"{overall_score:.1f}")
            else:
                st.markdown("—")

        with col5:
            st.markdown(f"{formatted_date}")

        with col6:
            if st.button("Delete", key=f"delete_{sub_id}"):
                st.session_state["confirm_delete_sub"] = sub_id
                st.rerun()

        st.divider()

# Handle delete confirmation
if "confirm_delete_sub" in st.session_state and st.session_state["confirm_delete_sub"]:
    sub_id = st.session_state["confirm_delete_sub"]
    submission = next((s for s in submissions if s.get("sub_id") == sub_id), None)

    if submission:
        st.warning(
            f"Are you sure you want to delete submission from '{submission.get('team_name')}'? This action cannot be undone."
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Confirm Delete", type="primary"):
                try:
                    with st.spinner("Deleting..."):
                        api_client.delete(f"/submissions/{sub_id}")
                    st.success("Submission deleted successfully!")
                    st.session_state.pop("confirm_delete_sub", None)
                    st.cache_data.clear()
                    st.rerun()
                except APIError as e:
                    st.error(f"Failed to delete: {e}")

        with col2:
            if st.button("Cancel"):
                st.session_state.pop("confirm_delete_sub", None)
                st.rerun()

# Display summary statistics
st.markdown("---")
st.subheader("Summary")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Submissions", len(submissions))

with col2:
    completed_count = len([s for s in submissions if s.get("status") == "completed"])
    st.metric("Completed", completed_count)

with col3:
    pending_count = len([s for s in submissions if s.get("status") == "pending"])
    st.metric("Pending", pending_count)

with col4:
    failed_count = len([s for s in submissions if s.get("status") == "failed"])
    st.metric("Failed", failed_count)

# Manual refresh button
st.markdown("---")
if st.button("Refresh"):
    st.cache_data.clear()
    st.rerun()
