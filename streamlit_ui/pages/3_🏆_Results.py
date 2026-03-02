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

        if status == 401:
            st.error("❌ Invalid API key")
        elif status == 404:
            st.error("❌ Resource not found")
        else:
            try:
                error_detail = e.response.json().get("detail", str(e))
            except:
                error_detail = str(e)
            st.error(f"❌ {error_detail}")

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
        scorecard = api_call(f"/submissions/{sub_id}/scorecard")

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

        dimension_scores = scorecard.get("weighted_scores", {})

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

        # Display cost by agent (if available in future)
        agent_scores_list = scorecard.get("agent_scores", [])
        if agent_scores_list:
            with st.expander("View Cost by Agent"):
                st.caption("Cost breakdown by agent will be available soon.")

        # Advanced details expander
        with st.expander("🔍 Advanced Details", expanded=False):
            st.markdown("**Additional Metrics**")

            col1, col2 = st.columns(2)

            with col1:
                # Rank
                rank = scorecard.get("rank")
                if rank:
                    st.markdown(f"**Leaderboard Rank:** #{rank}")

                # Total tokens
                total_tokens = scorecard.get("total_tokens")
                if total_tokens:
                    st.markdown(f"**Total Tokens:** {total_tokens:,}")

                # Analysis timestamp
                analyzed_at = scorecard.get("analyzed_at")
                if analyzed_at:
                    st.markdown(f"**Analyzed At:** {analyzed_at}")

            with col2:
                # Analysis duration
                analysis_duration_ms = scorecard.get("analysis_duration_ms")
                if analysis_duration_ms:
                    duration_sec = analysis_duration_ms / 1000
                    st.markdown(f"**Analysis Duration:** {duration_sec:.2f}s")

    with tab2:
        # Agent results section
        st.markdown("### 🤖 Agent Analysis")

        agent_scores = scorecard.get("agent_scores", [])

        if agent_scores:
            for agent_result in agent_scores:
                agent_name = agent_result.get("agent_name", "Unknown")
                formatted_agent_name = agent_name.replace("_", " ").title()

                with st.expander(f"**{formatted_agent_name}**", expanded=False):
                    # Display overall score and confidence
                    col1, col2 = st.columns(2)
                    with col1:
                        agent_score = agent_result.get("overall_score", 0)
                        st.metric("Score", f"{agent_score:.1f}/10")
                    with col2:
                        agent_confidence = agent_result.get("confidence", 0)
                        st.metric("Confidence", f"{agent_confidence:.0%}")

                    st.markdown("---")

                    # Summary
                    summary = agent_result.get("summary", "N/A")
                    st.markdown("**Summary:**")
                    st.markdown(summary)

                    st.markdown("")

                    # Sub-scores breakdown
                    scores = agent_result.get("scores", {})
                    if scores:
                        st.markdown("**📊 Detailed Scores:**")
                        for score_name, score_value in scores.items():
                            formatted_name = score_name.replace("_", " ").title()
                            if isinstance(score_value, (int, float)):
                                st.caption(f"- {formatted_name}: {score_value:.1f}/10")
                            else:
                                st.caption(f"- {formatted_name}: {score_value}")
                        st.markdown("")

                    # Evidence/findings
                    evidence = agent_result.get("evidence", [])
                    if evidence:
                        st.markdown("**🔍 Key Findings:**")
                        for ev in evidence[:5]:  # Limit to top 5
                            finding = ev.get("finding", "")
                            file_path = ev.get("file", "")
                            if finding:
                                st.markdown(f"- {finding}")
                                if file_path:
                                    st.caption(f"  _File: {file_path}_")
                        if len(evidence) > 5:
                            st.caption(f"_...and {len(evidence) - 5} more findings_")
                        st.markdown("")

            # Advanced details expander for Tab 2
            with st.expander("🔍 Advanced Details", expanded=False):
                st.markdown("**Additional Agent Data**")

                # Check for additional fields that might not be displayed
                additional_fields = [
                    "ci_observations",
                    "tech_stack_assessment",
                    "innovation_highlights",
                    "development_story",
                    "hackathon_context_assessment",
                    "commit_analysis",
                    "ai_policy_observation",
                ]

                displayed_any = False
                for agent_result in agent_scores:
                    agent_name = agent_result.get("agent_name", "Unknown")
                    formatted_agent_name = agent_name.replace("_", " ").title()

                    agent_additional = {}
                    for field in additional_fields:
                        if field in agent_result and agent_result[field]:
                            agent_additional[field] = agent_result[field]

                    if agent_additional:
                        displayed_any = True
                        st.markdown(f"**{formatted_agent_name}:**")
                        for field, value in agent_additional.items():
                            formatted_field = field.replace("_", " ").title()
                            if isinstance(value, (list, dict)):
                                st.json(value)
                            else:
                                st.markdown(f"- **{formatted_field}:** {value}")

                if not displayed_any:
                    st.caption("No additional agent data available beyond what's displayed above.")
        else:
            st.info("📭 No agent analysis available")

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

            # Advanced details expander for Tab 3
            with st.expander("🔍 Advanced Details", expanded=False):
                st.markdown("**Additional Repository Data**")

                col1, col2 = st.columns(2)

                with col1:
                    # Branch count
                    branch_count = repo_meta.get("branch_count")
                    if branch_count is not None:
                        st.markdown(f"**Branches:** {branch_count}")

                    # Total files
                    total_files = repo_meta.get("total_files")
                    if total_files is not None:
                        st.markdown(f"**Total Files:** {total_files:,}")

                    # Total lines
                    total_lines = repo_meta.get("total_lines")
                    if total_lines is not None:
                        st.markdown(f"**Total Lines:** {total_lines:,}")

                    # Has README
                    has_readme = repo_meta.get("has_readme")
                    if has_readme is not None:
                        readme_status = "✅ Yes" if has_readme else "❌ No"
                        st.markdown(f"**Has README:** {readme_status}")

                    # Has Dockerfile
                    has_dockerfile = repo_meta.get("has_dockerfile")
                    if has_dockerfile is not None:
                        docker_status = "✅ Yes" if has_dockerfile else "❌ No"
                        st.markdown(f"**Has Dockerfile:** {docker_status}")

                with col2:
                    # First commit
                    first_commit = repo_meta.get("first_commit_at")
                    if first_commit:
                        st.markdown(f"**First Commit:** {first_commit}")

                    # Last commit
                    last_commit = repo_meta.get("last_commit_at")
                    if last_commit:
                        st.markdown(f"**Last Commit:** {last_commit}")

                    # Development duration
                    dev_duration = repo_meta.get("development_duration_hours")
                    if dev_duration:
                        st.markdown(f"**Dev Duration:** {dev_duration:.1f} hours")

                    # Workflow runs
                    workflow_runs = repo_meta.get("workflow_run_count")
                    if workflow_runs is not None:
                        st.markdown(f"**Workflow Runs:** {workflow_runs}")

                    # Workflow success rate
                    workflow_success = repo_meta.get("workflow_success_rate")
                    if workflow_success is not None:
                        st.markdown(f"**CI Success Rate:** {workflow_success:.1%}")

                # Languages breakdown
                languages = repo_meta.get("languages")
                if languages and isinstance(languages, dict):
                    st.markdown("---")
                    st.markdown("**Language Breakdown:**")
                    for lang, percentage in languages.items():
                        st.markdown(f"- {lang}: {percentage}%")
        else:
            st.info("📭 No repository metadata available")

    with tab4:
        # Team dynamics and strategy section
        st.markdown("### 👥 Team Dynamics & Strategy Analysis")

        # Use team_dynamics and strategy_analysis from the main scorecard response
        team_dynamics = scorecard.get("team_dynamics", {})
        strategy_analysis = scorecard.get("strategy_analysis", {})
        actionable_feedback = scorecard.get("actionable_feedback", [])

        if team_dynamics:
            st.markdown("#### 🤝 Team Dynamics")

            # Display team dynamics metrics
            col1, col2 = st.columns(2)
            with col1:
                team_grade = team_dynamics.get("team_dynamics_grade", "N/A")
                st.metric("Team Dynamics Grade", team_grade if team_grade else "N/A")
            with col2:
                commit_quality = team_dynamics.get("commit_message_quality", 0)
                # Convert to float if it's a string
                if isinstance(commit_quality, str):
                    try:
                        commit_quality = float(commit_quality)
                    except (ValueError, TypeError):
                        commit_quality = None

                if commit_quality is not None and commit_quality != 0:
                    st.metric("Commit Message Quality", f"{commit_quality:.1f}/10")
                else:
                    st.metric("Commit Message Quality", "N/A")

            # Red flags
            red_flags = team_dynamics.get("red_flags", [])
            if red_flags:
                st.markdown("**⚠️ Red Flags:**")
                for flag in red_flags:
                    flag_type = flag.get("type", "Unknown") if isinstance(flag, dict) else str(flag)
                    st.warning(f"- {flag_type}")

            st.markdown("---")

        if strategy_analysis:
            st.markdown("#### 🎯 Strategy Analysis")

            col1, col2 = st.columns(2)
            with col1:
                test_strategy = strategy_analysis.get("test_strategy", "N/A")
                st.metric("Test Strategy", test_strategy if test_strategy else "N/A")
            with col2:
                maturity = strategy_analysis.get("maturity_level", "N/A")
                st.metric("Maturity Level", maturity if maturity else "N/A")

            # Strategic context
            context = strategy_analysis.get("strategic_context", "")
            if context:
                st.markdown("**Strategic Context:**")
                st.info(context)

            st.markdown("---")

        if actionable_feedback:
            st.markdown("#### 💡 Actionable Feedback")
            for idx, feedback_item in enumerate(actionable_feedback[:5], 1):  # Limit to top 5
                if isinstance(feedback_item, dict):
                    finding = feedback_item.get("finding", "General")
                    business_impact = feedback_item.get("business_impact", "")
                    acknowledgment = feedback_item.get("acknowledgment", "")
                    priority = feedback_item.get("priority", 3)  # Default to medium (3)

                    # Map priority number (1-5) to emoji: 1-2=high, 3=medium, 4-5=low
                    if priority <= 2:
                        priority_emoji = "🔴"
                        priority_label = "High"
                    elif priority == 3:
                        priority_emoji = "🟡"
                        priority_label = "Medium"
                    else:
                        priority_emoji = "🟢"
                        priority_label = "Low"

                    with st.expander(f"{priority_emoji} {finding}", expanded=False):
                        # Show acknowledgment if available
                        if acknowledgment and acknowledgment != "N/A - This is a strength":
                            st.success(f"**✅ {acknowledgment}**")
                            st.markdown("")

                        # Show business impact/suggestion
                        if business_impact:
                            st.markdown(business_impact)
                            st.markdown("")

                        # Show code example if available
                        code_example = feedback_item.get("code_example", None)
                        if code_example and code_example is not None:
                            if isinstance(code_example, dict):
                                code_text = code_example.get("code", "")
                                language = code_example.get("language", "python")
                                if code_text:
                                    st.markdown("**Example:**")
                                    st.code(code_text, language=language)
                            elif isinstance(code_example, str):
                                st.markdown("**Example:**")
                                st.code(code_example, language="python")

            if len(actionable_feedback) > 5:
                st.caption(f"_...and {len(actionable_feedback) - 5} more feedback items_")

        # Advanced details expander for Tab 4
        if team_dynamics or strategy_analysis:
            with st.expander("🔍 Advanced Details", expanded=False):
                st.markdown("**Additional Team & Strategy Data**")

                # Individual scorecards (per-contributor analysis)
                individual_scorecards = team_dynamics.get("individual_scorecards", [])
                if individual_scorecards:
                    st.markdown("---")
                    st.markdown("**👤 Individual Contributor Scorecards:**")
                    for scorecard_item in individual_scorecards[:10]:  # Limit to 10
                        contributor_name = scorecard_item.get("name", "Unknown")
                        role = scorecard_item.get("role", "N/A")
                        commit_count = scorecard_item.get("commit_count", 0)

                        st.markdown(f"**{contributor_name}** ({role}) - {commit_count} commits")

                    if len(individual_scorecards) > 10:
                        st.caption(f"_...and {len(individual_scorecards) - 10} more contributors_")

                # Collaboration metrics
                collaboration_metrics = team_dynamics.get("collaboration_metrics", {})
                if collaboration_metrics and isinstance(collaboration_metrics, dict):
                    st.markdown("---")
                    st.markdown("**🤝 Collaboration Metrics:**")
                    for metric_name, metric_value in collaboration_metrics.items():
                        formatted_name = metric_name.replace("_", " ").title()
                        if isinstance(metric_value, (int, float)):
                            st.markdown(f"- {formatted_name}: {metric_value:.2f}")
                        else:
                            st.markdown(f"- {formatted_name}: {metric_value}")

                # Strategic tradeoffs
                tradeoffs = strategy_analysis.get("tradeoffs", [])
                if tradeoffs:
                    st.markdown("---")
                    st.markdown("**⚖️ Strategic Tradeoffs:**")
                    for tradeoff in tradeoffs:
                        if isinstance(tradeoff, dict):
                            st.markdown(f"- {tradeoff.get('description', str(tradeoff))}")
                        else:
                            st.markdown(f"- {tradeoff}")

                # Strategy recommendations
                recommendations = strategy_analysis.get("recommendations", [])
                if recommendations:
                    st.markdown("---")
                    st.markdown("**💡 Strategy Recommendations:**")
                    for rec in recommendations[:5]:  # Limit to 5
                        if isinstance(rec, dict):
                            st.markdown(f"- {rec.get('recommendation', str(rec))}")
                        else:
                            st.markdown(f"- {rec}")
                    if len(recommendations) > 5:
                        st.caption(f"_...and {len(recommendations) - 5} more recommendations_")

        if not team_dynamics and not strategy_analysis and not actionable_feedback:
            st.info(
                "📭 Team dynamics and strategy analysis are not yet available for this submission."
            )

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
hackathon_info = leaderboard_data.get("hackathon", {})
total_submissions = hackathon_info.get("submission_count", 0)
analyzed_count = hackathon_info.get("analyzed_count", 0)

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

submissions = leaderboard_data.get("leaderboard", [])

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
