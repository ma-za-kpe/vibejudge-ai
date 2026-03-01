"""Results page for viewing hackathon leaderboard and submission rankings.

Simplified version - backend is source of truth, no caching complexity.
"""

import logging

import requests
import streamlit as st
from components.auth import is_authenticated

logger = logging.getLogger(__name__)


# Page configuration
st.set_page_config(page_title="Results", page_icon="🏆", layout="wide")


# Authentication check
if not is_authenticated():
    st.error("🔒 Please authenticate first")
    st.info("Go to the Home page to log in with your API key.")
    st.stop()


# Page header
st.title("🏆 Results")
st.markdown("View ranked submissions and leaderboard for your hackathon.")


# Initialize view mode in session state
if "view_mode" not in st.session_state:
    st.session_state["view_mode"] = "leaderboard"


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

        if status == 400:
            st.error("❌ Bad request - hackathon may not have analyzed submissions yet")
        elif status == 401:
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


# Check if we're in team detail view mode
if st.session_state["view_mode"] == "team_detail":
    # Display back button
    if st.button("⬅️ Back to Leaderboard"):
        st.session_state["view_mode"] = "leaderboard"
        st.rerun()

    # Get selected submission ID
    if "selected_sub_id" not in st.session_state:
        st.error("❌ No submission selected")
        st.stop()

    sub_id = st.session_state["selected_sub_id"]
    hack_id = st.session_state.get("selected_hackathon", "")

    if not hack_id:
        st.error("❌ No hackathon selected")
        st.stop()

    # Fetch scorecard data
    with st.spinner("📋 Loading scorecard..."):
        scorecard = api_call(f"/hackathons/{hack_id}/submissions/{sub_id}/scorecard")

    if not scorecard:
        if st.button("🔄 Retry", key="retry_scorecard"):
            st.rerun()
        st.stop()

    # Display team detail scorecard
    st.subheader(f"📋 Scorecard: {scorecard.get('team_name', 'Unknown Team')}")

    # Create tabs for organizing scorecard content
    tab1, tab2, tab3, tab4 = st.tabs(
        ["📊 Overview", "🤖 Agent Analysis", "📦 Repository", "👥 Team Members"]
    )

    with tab1:
        # Overall metrics section
        st.markdown("### 🎯 Overall Evaluation")

        col1, col2, col3 = st.columns(3)

        with col1:
            overall_score = scorecard.get("overall_score", 0)
            st.metric(
                label="Overall Score",
                value=f"{overall_score:.1f}",
                help="Weighted average score across all dimensions",
            )

        with col2:
            confidence = scorecard.get("confidence", 0)
            st.metric(
                label="Confidence",
                value=f"{confidence:.0%}",
                help="AI confidence in the evaluation",
            )

        with col3:
            recommendation = scorecard.get("recommendation", "N/A").replace("_", " ").title()
            st.metric(
                label="Recommendation",
                value=recommendation,
                help="Hiring recommendation based on evaluation",
            )

        # Dimension scores section
        st.markdown("---")
        st.markdown("### 📊 Dimension Scores")

        dimension_scores = scorecard.get("dimension_scores", {})

        if dimension_scores:
            # Create table header
            header_col1, header_col2, header_col3, header_col4 = st.columns([2, 1, 1, 1])
            with header_col1:
                st.markdown("**Dimension**")
            with header_col2:
                st.markdown("**Raw Score**")
            with header_col3:
                st.markdown("**Weight**")
            with header_col4:
                st.markdown("**Weighted Score**")

            st.divider()

            # Display each dimension
            for dimension_name, scores in dimension_scores.items():
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

                with col1:
                    formatted_name = dimension_name.replace("_", " ").title()
                    st.markdown(formatted_name)

                with col2:
                    raw_score = scores.get("raw", 0)
                    st.markdown(f"{raw_score:.1f}")

                with col3:
                    weight = scores.get("weight", 0)
                    st.markdown(f"{weight:.0%}")

                with col4:
                    weighted_score = scores.get("weighted", 0)
                    st.markdown(f"{weighted_score:.1f}")

                st.divider()
        else:
            st.info("📭 No dimension scores available")

        # Cost breakdown section
        st.markdown("---")
        st.markdown("### 💰 Cost Breakdown")

        total_cost_usd = scorecard.get("total_cost_usd", 0)

        st.metric(
            label="Total Analysis Cost",
            value=f"${total_cost_usd:.4f}",
            help="Total cost for analyzing this submission",
        )

        # Display cost by agent
        agent_results = scorecard.get("agent_results", {})
        if agent_results:
            with st.expander("View Cost by Agent"):
                for agent_name, result in agent_results.items():
                    formatted_agent_name = agent_name.replace("_", " ").title()
                    cost_usd = result.get("cost_usd", 0)
                    st.caption(f"- {formatted_agent_name}: ${cost_usd:.4f}")

    with tab2:
        # Agent results section
        st.markdown("### 🤖 Agent Analysis")

        agent_results = scorecard.get("agent_results", {})

        if agent_results:
            for agent_name, result in agent_results.items():
                formatted_agent_name = agent_name.replace("_", " ").title()

                with st.expander(f"**{formatted_agent_name}**", expanded=False):
                    # Summary
                    summary = result.get("summary", "N/A")
                    st.markdown("**Summary:**")
                    st.markdown(summary)

                    st.markdown("")

                    # Strengths
                    strengths = result.get("strengths", [])
                    if strengths:
                        st.markdown("**✅ Strengths:**")
                        for strength in strengths:
                            st.markdown(f"- {strength}")
                        st.markdown("")

                    # Improvements
                    improvements = result.get("improvements", [])
                    if improvements:
                        st.markdown("**💡 Areas for Improvement:**")
                        for improvement in improvements:
                            st.markdown(f"- {improvement}")
                        st.markdown("")

                    # Cost
                    cost_usd = result.get("cost_usd", 0)
                    st.caption(f"Analysis cost: ${cost_usd:.4f}")
        else:
            st.info("📭 No agent results available")

    with tab3:
        # Repository metadata section
        st.markdown("### 📦 Repository Metadata")

        repo_meta = scorecard.get("repo_meta", {})

        if repo_meta:
            col1, col2, col3, col4, col5 = st.columns(5)

            with col1:
                primary_language = repo_meta.get("primary_language", "N/A")
                st.metric(
                    label="Primary Language",
                    value=primary_language,
                    help="Main programming language used",
                )

            with col2:
                commit_count = repo_meta.get("commit_count", 0)
                st.metric(label="Commits", value=commit_count, help="Total number of commits")

            with col3:
                contributor_count = repo_meta.get("contributor_count", 0)
                st.metric(
                    label="Contributors",
                    value=contributor_count,
                    help="Number of unique contributors",
                )

            with col4:
                has_tests = repo_meta.get("has_tests", False)
                test_status = "✅ Yes" if has_tests else "❌ No"
                st.metric(
                    label="Has Tests",
                    value=test_status,
                    help="Whether the repository includes tests",
                )

            with col5:
                has_ci = repo_meta.get("has_ci", False)
                ci_status = "✅ Yes" if has_ci else "❌ No"
                st.metric(
                    label="Has CI/CD",
                    value=ci_status,
                    help="Whether the repository has CI/CD configured",
                )
        else:
            st.info("📭 No repository metadata available")

    with tab4:
        # Individual team member scorecard section
        st.markdown("### 👥 Individual Team Member Analysis")

        # Fetch individual scorecard data
        with st.spinner("👥 Loading individual team member analysis..."):
            individual_data = api_call(
                f"/hackathons/{hack_id}/submissions/{sub_id}/individual-scorecards"
            )

        if not individual_data:
            st.info(
                "📭 Individual team member analysis is pending or unavailable. This data will be available after the analysis is complete."
            )
        else:
            # Team dynamics section
            team_dynamics = individual_data.get("team_dynamics", {})

            if team_dynamics:
                st.markdown("#### 🤝 Team Dynamics")

                col1, col2, col3 = st.columns(3)

                with col1:
                    collaboration_quality = team_dynamics.get("collaboration_quality", "N/A")
                    st.metric(
                        label="Collaboration Quality",
                        value=collaboration_quality.title()
                        if isinstance(collaboration_quality, str)
                        else "N/A",
                        help="Assessment of how well the team worked together",
                    )

                with col2:
                    role_distribution = team_dynamics.get("role_distribution", "N/A")
                    st.metric(
                        label="Role Distribution",
                        value=role_distribution.title()
                        if isinstance(role_distribution, str)
                        else "N/A",
                        help="How roles were distributed among team members",
                    )

                with col3:
                    communication_patterns = team_dynamics.get("communication_patterns", "N/A")
                    st.metric(
                        label="Communication Patterns",
                        value=communication_patterns.title()
                        if isinstance(communication_patterns, str)
                        else "N/A",
                        help="Quality and frequency of team communication",
                    )

            # Strategy analysis section
            strategy_analysis = individual_data.get("strategy_analysis", {})

            if strategy_analysis:
                st.markdown("#### 🎯 Strategy Analysis")

                col1, col2, col3 = st.columns(3)

                with col1:
                    development_approach = strategy_analysis.get("development_approach", "N/A")
                    st.metric(
                        label="Development Approach",
                        value=development_approach.title()
                        if isinstance(development_approach, str)
                        else "N/A",
                        help="The team's approach to development",
                    )

                with col2:
                    time_management = strategy_analysis.get("time_management", "N/A")
                    st.metric(
                        label="Time Management",
                        value=time_management.title() if isinstance(time_management, str) else "N/A",
                        help="How well the team managed their time",
                    )

                with col3:
                    risk_management = strategy_analysis.get("risk_management", "N/A")
                    st.metric(
                        label="Risk Management",
                        value=risk_management.title() if isinstance(risk_management, str) else "N/A",
                        help="The team's approach to managing risks",
                    )

            # Contributors section
            contributors = individual_data.get("contributors", [])

            if contributors:
                st.markdown("#### 👤 Individual Contributors")

                # Display each contributor
                for contributor in contributors:
                    member_name = contributor.get("member_name", "Unknown")
                    commit_count = contributor.get("commit_count", 0)
                    skill_assessment = contributor.get("skill_assessment", "N/A")
                    actionable_feedback = contributor.get("actionable_feedback", "")

                    with st.expander(f"**{member_name}**", expanded=False):
                        # Contributor metrics
                        col1, col2 = st.columns(2)

                        with col1:
                            st.metric(
                                label="Commits",
                                value=commit_count,
                                help="Number of commits by this contributor",
                            )

                        with col2:
                            st.metric(
                                label="Skill Assessment",
                                value=skill_assessment.title()
                                if isinstance(skill_assessment, str)
                                else "N/A",
                                help="Assessed skill level of this contributor",
                            )

                        # Actionable feedback
                        if actionable_feedback:
                            st.markdown("**💡 Actionable Feedback:**")
                            st.markdown(actionable_feedback)
                        else:
                            st.info("No actionable feedback available for this contributor.")
            else:
                st.info("📭 No individual contributor data available")

    st.stop()


# Continue with leaderboard view
# Fetch hackathons for dropdown
with st.spinner("🔄 Loading hackathons..."):
    hackathons_response = api_call("/hackathons")

if not hackathons_response:
    if st.button("🔄 Retry", key="retry_hackathons"):
        st.rerun()
    st.stop()

hackathons = hackathons_response.get("hackathons", [])

# Filter out DRAFT and ARCHIVED hackathons
active_hackathons = [h for h in hackathons if h.get("status") not in ["draft", "archived"]]

if not active_hackathons:
    st.warning("⚠️ No active hackathons found.")
    st.info("💡 Create a hackathon and activate it to start accepting submissions.")
    st.stop()


# Create dropdown with hackathon names
hackathon_options = {h["name"]: h["hack_id"] for h in active_hackathons}
selected_name = st.selectbox(
    "Select Hackathon",
    options=list(hackathon_options.keys()),
    help="Choose a hackathon to view its leaderboard",
)

# Get selected hackathon ID
selected_hack_id = hackathon_options[selected_name]

# Store selected hackathon in session state
st.session_state["selected_hackathon"] = selected_hack_id


# Fetch and display leaderboard
st.markdown("---")

with st.spinner("🏆 Loading leaderboard..."):
    leaderboard_data = api_call(f"/hackathons/{selected_hack_id}/leaderboard")

if not leaderboard_data:
    if st.button("🔄 Retry", key="retry_leaderboard"):
        st.rerun()
    st.stop()

# Display summary statistics
total_submissions = leaderboard_data.get("total_submissions", 0)
analyzed_count = leaderboard_data.get("analyzed_count", 0)

st.subheader("📊 Summary")

col1, col2 = st.columns(2)

with col1:
    st.metric(
        label="Total Submissions",
        value=total_submissions,
        help="Total number of submissions received",
    )

with col2:
    st.metric(
        label="Analyzed Submissions",
        value=analyzed_count,
        help="Number of submissions that have been analyzed",
    )

# Display leaderboard table
st.markdown("---")
st.subheader("🏅 Leaderboard")

submissions = leaderboard_data.get("submissions", [])

if not submissions:
    st.info("📭 No submissions have been analyzed yet.")
    st.caption("Start an analysis from the Live Dashboard to generate results.")
else:
    # Search and sort controls
    col1, col2 = st.columns([2, 1])

    with col1:
        search_query = st.text_input(
            "🔍 Search by team name",
            placeholder="Enter team name...",
            help="Filter submissions by team name (case-insensitive)",
            key="search_query_input",
        )

    with col2:
        sort_option = st.selectbox(
            "Sort by",
            options=["score", "team_name", "created_at"],
            format_func=lambda x: {
                "score": "Overall Score",
                "team_name": "Team Name",
                "created_at": "Submission Date",
            }[x],
            help="Sort leaderboard by selected field",
            key="sort_option_select",
        )

    # Reset page number when search or sort changes
    if "last_search_query" not in st.session_state:
        st.session_state["last_search_query"] = ""
    if "last_sort_option" not in st.session_state:
        st.session_state["last_sort_option"] = "score"

    if (
        search_query != st.session_state["last_search_query"]
        or sort_option != st.session_state["last_sort_option"]
    ):
        st.session_state["results_page_number"] = 1
        st.session_state["last_search_query"] = search_query
        st.session_state["last_sort_option"] = sort_option

    # Apply search filter (case-insensitive)
    filtered_submissions = submissions
    if search_query:
        filtered_submissions = [
            s for s in submissions if search_query.lower() in s.get("team_name", "").lower()
        ]

    # Apply sorting
    if sort_option == "score":
        # Sort by overall_score descending (highest first)
        filtered_submissions = sorted(
            filtered_submissions, key=lambda x: x.get("overall_score", 0), reverse=True
        )
    elif sort_option == "team_name":
        # Sort by team_name ascending (A-Z)
        filtered_submissions = sorted(
            filtered_submissions, key=lambda x: x.get("team_name", "").lower()
        )
    elif sort_option == "created_at":
        # Sort by created_at descending (newest first)
        filtered_submissions = sorted(
            filtered_submissions, key=lambda x: x.get("created_at", ""), reverse=True
        )

    # Display filtered and sorted results
    if not filtered_submissions:
        st.warning(f"⚠️ No submissions found matching '{search_query}'")
    else:
        # Pagination setup
        ITEMS_PER_PAGE = 50
        total_items = len(filtered_submissions)
        total_pages = (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

        # Initialize page number in session state
        if "results_page_number" not in st.session_state:
            st.session_state["results_page_number"] = 1

        # Ensure page number is within valid range
        if st.session_state["results_page_number"] > total_pages:
            st.session_state["results_page_number"] = total_pages
        if st.session_state["results_page_number"] < 1:
            st.session_state["results_page_number"] = 1

        current_page = st.session_state["results_page_number"]

        # Calculate pagination slice
        start_idx = (current_page - 1) * ITEMS_PER_PAGE
        end_idx = min(start_idx + ITEMS_PER_PAGE, total_items)
        paginated_submissions = filtered_submissions[start_idx:end_idx]

        # Display table header
        header_col1, header_col2, header_col3, header_col4, header_col5 = st.columns(
            [0.5, 2, 1, 1.5, 1]
        )
        with header_col1:
            st.markdown("**Rank**")
        with header_col2:
            st.markdown("**Team Name**")
        with header_col3:
            st.markdown("**Score**")
        with header_col4:
            st.markdown("**Recommendation**")
        with header_col5:
            st.markdown("**Actions**")

        st.divider()

        # Display submissions as clickable rows
        for submission in paginated_submissions:
            rank = submission.get("rank", "N/A")
            team_name = submission.get("team_name", "Unknown")
            overall_score = submission.get("overall_score", 0)
            recommendation = submission.get("recommendation", "N/A").replace("_", " ").title()
            sub_id = submission.get("sub_id", "")

            # Create a container for each row
            col1, col2, col3, col4, col5 = st.columns([0.5, 2, 1, 1.5, 1])

            with col1:
                st.markdown(f"{rank}")

            with col2:
                st.markdown(f"{team_name}")

            with col3:
                st.markdown(f"{overall_score:.1f}")

            with col4:
                st.markdown(f"{recommendation}")

            with col5:
                # Make the row clickable with a button
                if st.button("View Details", key=f"view_{sub_id}"):
                    # Store selected sub_id in session state
                    st.session_state["selected_sub_id"] = sub_id
                    st.session_state["view_mode"] = "team_detail"
                    st.rerun()

            st.divider()

        # Pagination controls
        if total_pages > 1:
            col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])

            with col1:
                if st.button("⏮️ First", disabled=(current_page == 1), key="page_first"):
                    st.session_state["results_page_number"] = 1
                    st.rerun()

            with col2:
                if st.button("◀️ Previous", disabled=(current_page == 1), key="page_prev"):
                    st.session_state["results_page_number"] = current_page - 1
                    st.rerun()

            with col3:
                st.markdown(
                    f"<div style='text-align: center; padding: 5px;'>Page {current_page} of {total_pages}</div>",
                    unsafe_allow_html=True,
                )

            with col4:
                if st.button("Next ▶️", disabled=(current_page == total_pages), key="page_next"):
                    st.session_state["results_page_number"] = current_page + 1
                    st.rerun()

            with col5:
                if st.button("Last ⏭️", disabled=(current_page == total_pages), key="page_last"):
                    st.session_state["results_page_number"] = total_pages
                    st.rerun()

        st.caption(f"Showing {start_idx + 1}-{end_idx} of {total_items} submission(s)")


# Manual refresh button
st.markdown("---")
if st.button("🔄 Refresh Data", key="refresh_main"):
    st.rerun()
