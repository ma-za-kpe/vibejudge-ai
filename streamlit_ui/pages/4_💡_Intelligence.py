"""Intelligence page for viewing hiring insights and technology trends.

Simplified version - backend is source of truth, no caching complexity.
"""

import logging

import requests
import streamlit as st
from components.auth import is_authenticated
from components.charts import create_technology_trends_chart

logger = logging.getLogger(__name__)


# Page configuration
st.set_page_config(page_title="Intelligence", page_icon="💡", layout="wide")


# Authentication check
if not is_authenticated():
    st.error("🔒 Please authenticate first")
    st.info("Go to the Home page to log in with your API key.")
    st.stop()


# Page header
st.title("💡 Intelligence")
st.markdown("View hiring insights and technology trends from your hackathon submissions.")


# Helper function for API calls
def api_call(endpoint: str) -> dict | None:
    """Make API call with error handling.

    Args:
        endpoint: API endpoint path (e.g., "/hackathons")

    Returns:
        Response JSON or None if error
    """
    try:
        base_url = st.session_state["api_base_url"].rstrip("/")
        headers = {"X-API-Key": st.session_state["api_key"]}
        url = f"{base_url}{endpoint}"

        response = requests.get(url, headers=headers, timeout=60)
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


# Fetch hackathons for dropdown
with st.spinner("🔄 Loading hackathons..."):
    hackathons_response = api_call("/hackathons")

if not hackathons_response:
    if st.button("🔄 Retry"):
        st.rerun()
    st.stop()

hackathons = hackathons_response.get("hackathons", [])

if not hackathons:
    st.warning("⚠️ No hackathons found. Create a hackathon first!")
    st.stop()


# Create dropdown with hackathon names
hackathon_options = {h["name"]: h["hack_id"] for h in hackathons}
selected_name = st.selectbox(
    "Select Hackathon",
    options=list(hackathon_options.keys()),
    help="Choose a hackathon to view its intelligence insights",
)

# Get selected hackathon ID
selected_hack_id = hackathon_options[selected_name]

# Store selected hackathon in session state
st.session_state["selected_hackathon"] = selected_hack_id


# Fetch and display intelligence data
st.markdown("---")

with st.spinner("💡 Loading intelligence insights..."):
    intelligence_data = api_call(f"/hackathons/{selected_hack_id}/intelligence")

if not intelligence_data:
    st.info(
        "📭 Intelligence insights are pending or unavailable. This data will be available after the analysis is complete."
    )
    st.caption("Start an analysis from the Live Dashboard to generate intelligence insights.")
else:
    # Create tabs for organizing intelligence content
    tab1, tab2, tab3 = st.tabs(
        ["🎯 Must-Interview Candidates", "📊 Technology Trends", "🔌 Sponsor APIs"]
    )

    with tab1:
        # Must-interview candidates section
        st.markdown("### 🎯 Must-Interview Candidates")

        must_interview = intelligence_data.get("must_interview", [])

        if not must_interview:
            st.info("📭 No must-interview candidates identified yet.")
        else:
            # Display candidates table header
            header_col1, header_col2, header_col3, header_col4 = st.columns([2, 2, 3, 1])
            with header_col1:
                st.markdown("**Name**")
            with header_col2:
                st.markdown("**Team Name**")
            with header_col3:
                st.markdown("**Skills**")
            with header_col4:
                st.markdown("**Hiring Score**")

            st.divider()

            # Display each candidate
            for candidate in must_interview:
                col1, col2, col3, col4 = st.columns([2, 2, 3, 1])

                with col1:
                    name = candidate.get("name", "Unknown")
                    st.markdown(name)

                with col2:
                    team_name = candidate.get("team_name", "Unknown")
                    st.markdown(team_name)

                with col3:
                    skills = candidate.get("skills", [])
                    if skills:
                        skills_str = ", ".join(skills)
                        st.markdown(skills_str)
                    else:
                        st.markdown("N/A")

                with col4:
                    hiring_score = candidate.get("hiring_score", 0)
                    st.markdown(f"{hiring_score:.1f}")

                st.divider()

            st.caption(f"Total must-interview candidates: {len(must_interview)}")

    with tab2:
        # Technology trends section
        st.markdown("### 📊 Technology Trends")

        technology_trends = intelligence_data.get("technology_trends", [])

        if not technology_trends:
            st.info("📭 No technology trends data available yet.")
        else:
            # Display technology trends chart
            fig = create_technology_trends_chart(technology_trends)
            st.plotly_chart(fig, use_container_width=True)

            # Display technology trends table
            with st.expander("📋 View Detailed Technology Breakdown", expanded=False):
                # Table header
                header_col1, header_col2, header_col3 = st.columns([2, 2, 1])
                with header_col1:
                    st.markdown("**Technology**")
                with header_col2:
                    st.markdown("**Category**")
                with header_col3:
                    st.markdown("**Usage Count**")

                st.divider()

                # Display each technology
                for trend in technology_trends:
                    col1, col2, col3 = st.columns([2, 2, 1])

                    with col1:
                        technology = trend.get("technology", "Unknown")
                        st.markdown(technology)

                    with col2:
                        category = trend.get("category", "N/A")
                        st.markdown(category.title() if isinstance(category, str) else "N/A")

                    with col3:
                        usage_count = trend.get("usage_count", 0)
                        st.markdown(str(usage_count))

                    st.divider()

                st.caption(f"Total technologies tracked: {len(technology_trends)}")

    with tab3:
        # Sponsor API usage section
        st.markdown("### 🔌 Sponsor API Usage")

        sponsor_api_usage = intelligence_data.get("sponsor_api_usage", {})

        if not sponsor_api_usage:
            st.info("📭 No sponsor API usage data available yet.")
        else:
            # Display sponsor API usage as metrics
            st.markdown("**API Usage Statistics:**")

            # Create columns for metrics (max 4 per row)
            sponsors = list(sponsor_api_usage.items())
            num_sponsors = len(sponsors)

            # Display in rows of 4 columns
            for i in range(0, num_sponsors, 4):
                cols = st.columns(min(4, num_sponsors - i))

                for j, col in enumerate(cols):
                    if i + j < num_sponsors:
                        sponsor_name, usage_count = sponsors[i + j]
                        with col:
                            st.metric(
                                label=sponsor_name.title(),
                                value=usage_count,
                                help=f"Number of teams using {sponsor_name} API",
                            )

            st.caption(f"Total sponsor APIs tracked: {len(sponsor_api_usage)}")


# Manual refresh button
st.markdown("---")
if st.button("🔄 Refresh Data"):
    st.rerun()
