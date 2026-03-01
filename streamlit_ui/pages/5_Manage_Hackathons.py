"""Hackathon Management page for viewing and managing all hackathons.

Simplified version - backend is source of truth, no caching complexity.
"""

import logging
from datetime import datetime

import requests
import streamlit as st
from components.auth import is_authenticated

logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(page_title="Manage Hackathons", page_icon="⚙️", layout="wide")

# Authentication check
if not is_authenticated():
    st.error("Please authenticate first")
    st.info("Go to the Home page to log in with your API key.")
    st.stop()

# Page header
st.title("Manage Hackathons")
st.markdown("View and manage all your hackathons.")


# Helper function for API calls
def api_call(endpoint: str, method: str = "GET", json_data: dict | None = None) -> dict | None:
    """Make API call with error handling."""
    try:
        base_url = st.session_state["api_base_url"].rstrip("/")
        headers = {"X-API-Key": st.session_state["api_key"]}
        url = f"{base_url}{endpoint}"

        if method == "GET":
            response = requests.get(url, headers=headers, timeout=60)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=json_data or {}, timeout=60)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=60)
            if response.ok:
                return {"success": True}
            response.raise_for_status()
        else:
            raise ValueError(f"Unsupported method: {method}")

        response.raise_for_status()
        return response.json()

    except requests.HTTPError as e:
        status = e.response.status_code
        if status == 401:
            st.error("❌ Invalid API key")
        elif status == 404:
            st.error("❌ Resource not found")
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


# Check if we're in detail view mode
if st.session_state.get("view_mode") == "detail" and st.session_state.get(
    "selected_hackathon_detail"
):
    hack_id = st.session_state["selected_hackathon_detail"]

    # Fetch full hackathon details
    hackathon_detail = api_call(f"/hackathons/{hack_id}")

    if hackathon_detail:
        # Back button
        if st.button("← Back to List"):
            st.session_state.pop("view_mode", None)
            st.session_state.pop("selected_hackathon_detail", None)
            st.rerun()

        st.divider()

        # Display hackathon details
        st.subheader(hackathon_detail.get("name", "Unknown"))

        col1, col2, col3 = st.columns(3)
        with col1:
            status = hackathon_detail.get("status", "unknown")
            status_colors = {
                "draft": "🟡",
                "configured": "🟢",
                "analyzing": "🔵",
                "completed": "✅",
                "archived": "⚫",
            }
            status_icon = status_colors.get(status, "⚪")
            st.metric("Status", f"{status_icon} {status.title()}")

        with col2:
            st.metric("Submissions", hackathon_detail.get("submission_count", 0))

        with col3:
            budget = hackathon_detail.get("budget_limit_usd")
            st.metric("Budget Limit", f"${budget:.2f}" if budget else "No limit")

        st.divider()

        # Description
        st.markdown("**Description:**")
        st.write(hackathon_detail.get("description", "No description provided"))

        # Dates
        col1, col2 = st.columns(2)
        with col1:
            start_date = hackathon_detail.get("start_date")
            if start_date:
                try:
                    start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                    st.markdown(f"**Start Date:** {start_dt.strftime('%Y-%m-%d %H:%M')}")
                except Exception:
                    st.markdown(f"**Start Date:** {start_date}")
            else:
                st.markdown("**Start Date:** Not set")

        with col2:
            end_date = hackathon_detail.get("end_date")
            if end_date:
                try:
                    end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                    st.markdown(f"**End Date:** {end_dt.strftime('%Y-%m-%d %H:%M')}")
                except Exception:
                    st.markdown(f"**End Date:** {end_date}")
            else:
                st.markdown("**End Date:** Not set")

        st.divider()

        # Rubric configuration
        st.markdown("**Rubric Configuration:**")
        rubric = hackathon_detail.get("rubric", {})
        st.write(f"Name: {rubric.get('name', 'N/A')}")
        st.write(f"Max Score: {rubric.get('max_score', 100)}")

        dimensions = rubric.get("dimensions", [])
        if dimensions:
            st.markdown("**Dimensions:**")
            for dim in dimensions:
                st.write(
                    f"- {dim.get('name')}: {dim.get('weight') * 100:.1f}% (Agent: {dim.get('agent')})"
                )

        # Agents enabled
        st.divider()
        st.markdown("**Enabled Agents:**")
        agents = hackathon_detail.get("agents_enabled", [])
        st.write(", ".join(agents) if agents else "None")

        # AI Policy
        st.markdown(f"**AI Policy Mode:** {hackathon_detail.get('ai_policy_mode', 'N/A')}")

    else:
        if st.button("← Back to List"):
            st.session_state.pop("view_mode", None)
            st.session_state.pop("selected_hackathon_detail", None)
            st.rerun()

    st.stop()


# Fetch hackathons
with st.spinner("Loading hackathons..."):
    hackathons_response = api_call("/hackathons")

if not hackathons_response:
    if st.button("🔄 Retry"):
        st.rerun()
    st.stop()

hackathons = hackathons_response.get("hackathons", [])

if not hackathons:
    st.info("No hackathons found. Create your first hackathon to get started.")
    st.stop()

# Display hackathons in a table
st.subheader("Your Hackathons")

# Search and filter controls
col1, col2 = st.columns([2, 1])

with col1:
    search_query = st.text_input(
        "Search by name",
        placeholder="Enter hackathon name...",
        help="Filter hackathons by name (case-insensitive)",
    )

with col2:
    status_filter = st.selectbox(
        "Filter by status",
        options=["all", "draft", "configured", "analyzing", "completed", "archived"],
        format_func=lambda x: x.title(),
        help="Filter hackathons by status",
    )

# Apply filters
filtered_hackathons = hackathons
if search_query:
    filtered_hackathons = [
        h for h in filtered_hackathons if search_query.lower() in h.get("name", "").lower()
    ]
if status_filter != "all":
    filtered_hackathons = [h for h in filtered_hackathons if h.get("status") == status_filter]

if not filtered_hackathons:
    st.warning("No hackathons found matching your filters.")
else:
    # Display table header
    header_col1, header_col2, header_col3, header_col4, header_col5 = st.columns(
        [2, 1.5, 1, 1, 1.5]
    )
    with header_col1:
        st.markdown("**Name**")
    with header_col2:
        st.markdown("**Status**")
    with header_col3:
        st.markdown("**Submissions**")
    with header_col4:
        st.markdown("**Created**")
    with header_col5:
        st.markdown("**Actions**")

    st.divider()

    # Display each hackathon
    for hackathon in filtered_hackathons:
        hack_id = hackathon.get("hack_id", "")
        name = hackathon.get("name", "Unknown")
        status = hackathon.get("status", "unknown")
        submission_count = hackathon.get("submission_count", 0)
        created_at = hackathon.get("created_at", "")

        # Format created date
        try:
            created_date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            formatted_date = created_date.strftime("%Y-%m-%d")
        except Exception:
            formatted_date = "N/A"

        col1, col2, col3, col4, col5 = st.columns([2, 1.5, 1, 1, 1.5])

        with col1:
            st.markdown(f"{name}")

        with col2:
            # Status badge with color
            status_colors = {
                "draft": "🟡",
                "configured": "🟢",
                "analyzing": "🔵",
                "completed": "✅",
                "archived": "⚫",
            }
            status_icon = status_colors.get(status, "⚪")
            st.markdown(f"{status_icon} {status.title()}")

        with col3:
            st.markdown(f"{submission_count}")

        with col4:
            st.markdown(f"{formatted_date}")

        with col5:
            # Action buttons
            action_col1, action_col2, action_col3 = st.columns(3)

            with action_col1:
                if st.button("View", key=f"view_{hack_id}"):
                    st.session_state["selected_hackathon_detail"] = hack_id
                    st.session_state["view_mode"] = "detail"
                    st.rerun()

            with action_col2:
                if status == "draft":
                    if st.button("Activate", key=f"activate_{hack_id}"):
                        with st.spinner("Activating..."):
                            result = api_call(f"/hackathons/{hack_id}/activate", method="POST")
                        if result:
                            st.success("Hackathon activated!")
                            st.rerun()

            with action_col3:
                if st.button("Delete", key=f"delete_{hack_id}"):
                    st.session_state["confirm_delete"] = hack_id
                    st.rerun()

        st.divider()

# Handle delete confirmation
if "confirm_delete" in st.session_state and st.session_state["confirm_delete"]:
    hack_id = st.session_state["confirm_delete"]
    hackathon = next((h for h in hackathons if h.get("hack_id") == hack_id), None)

    if hackathon:
        st.warning(
            f"Are you sure you want to delete '{hackathon.get('name')}'? This action cannot be undone."
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Confirm Delete", type="primary", key="confirm_delete_btn"):
                with st.spinner("Deleting..."):
                    result = api_call(f"/hackathons/{hack_id}", method="DELETE")
                if result:
                    st.success("Hackathon deleted successfully!")
                    st.session_state.pop("confirm_delete", None)
                    st.rerun()

        with col2:
            if st.button("Cancel", key="cancel_delete_btn"):
                st.session_state.pop("confirm_delete", None)
                st.rerun()

# Manual refresh button
st.markdown("---")
if st.button("🔄 Refresh Data"):
    st.rerun()
