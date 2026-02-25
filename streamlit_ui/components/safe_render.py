"""Safe rendering utilities for handling missing or malformed API data.

This module provides functions to safely render scorecard data with appropriate
fallbacks for missing fields, ensuring the UI remains functional even when
API responses are incomplete.
"""

from typing import Any

import streamlit as st
from components.validators import safe_get, validate_individual_scorecard, validate_scorecard


def safe_render_scorecard(scorecard: dict[str, Any]) -> None:
    """Safely render scorecard data with fallbacks for missing fields.

    This function validates the scorecard structure and renders all sections
    with appropriate fallback values when data is missing. It displays a
    warning if the scorecard is incomplete.

    Args:
        scorecard: The scorecard data dictionary from API response

    Examples:
        >>> scorecard = {
        ...     "overall_score": 92.5,
        ...     "confidence": 0.95,
        ...     "recommendation": "must_interview",
        ...     "dimension_scores": {},
        ...     "agent_results": {},
        ...     "repo_meta": {}
        ... }
        >>> safe_render_scorecard(scorecard)  # Renders complete scorecard

        >>> incomplete = {"overall_score": 92.5}
        >>> safe_render_scorecard(incomplete)  # Shows warning + partial data
    """
    # Validate scorecard structure
    if not validate_scorecard(scorecard):
        st.warning("⚠️ Scorecard data is incomplete. Some sections may be missing or unavailable.")

    # Render overall metrics
    _render_overall_metrics(scorecard)

    # Render dimension scores
    _render_dimension_scores(scorecard)

    # Render cost breakdown
    _render_cost_breakdown(scorecard)


def safe_render_individual_scorecard(individual_data: dict[str, Any] | None) -> None:
    """Safely render individual scorecard data with fallbacks.

    This function handles the case where individual scorecard data may be
    unavailable (None) or incomplete, displaying appropriate messages.

    Args:
        individual_data: The individual scorecard data dictionary or None

    Examples:
        >>> data = {
        ...     "team_dynamics": {"collaboration_quality": "excellent"},
        ...     "strategy_analysis": {"development_approach": "iterative"},
        ...     "contributors": []
        ... }
        >>> safe_render_individual_scorecard(data)  # Renders complete data

        >>> safe_render_individual_scorecard(None)  # Shows pending message
    """
    if not individual_data:
        st.info(
            "📭 Individual team member analysis is pending or unavailable. "
            "This data will be available after the analysis is complete."
        )
        return

    # Validate individual scorecard structure
    if not validate_individual_scorecard(individual_data):
        st.warning("⚠️ Individual scorecard data is incomplete. Some sections may be missing.")

    # Render team dynamics
    _render_team_dynamics(individual_data)

    # Render strategy analysis
    _render_strategy_analysis(individual_data)

    # Render contributors
    _render_contributors(individual_data)


def _render_overall_metrics(scorecard: dict[str, Any]) -> None:
    """Render overall metrics section with safe fallbacks."""
    col1, col2, col3 = st.columns(3)

    with col1:
        overall_score = safe_get(scorecard, "overall_score", 0)
        st.metric(
            label="Overall Score",
            value=f"{overall_score:.1f}" if overall_score else "N/A",
            help="Weighted average score across all dimensions",
        )

    with col2:
        confidence = safe_get(scorecard, "confidence", 0)
        st.metric(
            label="Confidence",
            value=f"{confidence:.0%}" if confidence else "N/A",
            help="AI confidence in the evaluation",
        )

    with col3:
        recommendation = safe_get(scorecard, "recommendation", "N/A")
        formatted_rec = (
            recommendation.replace("_", " ").title() if recommendation != "N/A" else "N/A"
        )
        st.metric(
            label="Recommendation",
            value=formatted_rec,
            help="Hiring recommendation based on evaluation",
        )


def _render_dimension_scores(scorecard: dict[str, Any]) -> None:
    """Render dimension scores section with safe fallbacks."""
    st.markdown("---")
    st.markdown("### 📊 Dimension Scores")

    dimension_scores = safe_get(scorecard, "dimension_scores", {})

    if not dimension_scores:
        st.info("📭 No dimension scores available")
        return

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
            raw_score = safe_get(scores, "raw", 0)
            st.markdown(f"{raw_score:.1f}" if raw_score else "N/A")

        with col3:
            weight = safe_get(scores, "weight", 0)
            st.markdown(f"{weight:.0%}" if weight else "N/A")

        with col4:
            weighted_score = safe_get(scores, "weighted", 0)
            st.markdown(f"{weighted_score:.1f}" if weighted_score else "N/A")

        st.divider()


def _render_cost_breakdown(scorecard: dict[str, Any]) -> None:
    """Render cost breakdown section with safe fallbacks."""
    st.markdown("---")
    st.markdown("### 💰 Cost Breakdown")

    total_cost_usd = safe_get(scorecard, "total_cost_usd", 0)

    st.metric(
        label="Total Analysis Cost",
        value=f"${total_cost_usd:.4f}" if total_cost_usd else "$0.0000",
        help="Total cost for analyzing this submission",
    )

    # Display cost by agent
    agent_results = safe_get(scorecard, "agent_results", {})
    if agent_results:
        with st.expander("View Cost by Agent"):
            for agent_name, result in agent_results.items():
                formatted_agent_name = agent_name.replace("_", " ").title()
                cost_usd = safe_get(result, "cost_usd", 0)
                st.caption(f"- {formatted_agent_name}: ${cost_usd:.4f}")


def _render_team_dynamics(individual_data: dict[str, Any]) -> None:
    """Render team dynamics section with safe fallbacks."""
    team_dynamics = safe_get(individual_data, "team_dynamics", {})

    if not team_dynamics:
        return

    st.markdown("#### 🤝 Team Dynamics")

    col1, col2, col3 = st.columns(3)

    with col1:
        collaboration_quality = safe_get(team_dynamics, "collaboration_quality", "N/A")
        formatted_value = (
            collaboration_quality.title()
            if isinstance(collaboration_quality, str) and collaboration_quality != "N/A"
            else "N/A"
        )
        st.metric(
            label="Collaboration Quality",
            value=formatted_value,
            help="Assessment of how well the team worked together",
        )

    with col2:
        role_distribution = safe_get(team_dynamics, "role_distribution", "N/A")
        formatted_value = (
            role_distribution.title()
            if isinstance(role_distribution, str) and role_distribution != "N/A"
            else "N/A"
        )
        st.metric(
            label="Role Distribution",
            value=formatted_value,
            help="How roles were distributed among team members",
        )

    with col3:
        communication_patterns = safe_get(team_dynamics, "communication_patterns", "N/A")
        formatted_value = (
            communication_patterns.title()
            if isinstance(communication_patterns, str) and communication_patterns != "N/A"
            else "N/A"
        )
        st.metric(
            label="Communication Patterns",
            value=formatted_value,
            help="Quality and frequency of team communication",
        )


def _render_strategy_analysis(individual_data: dict[str, Any]) -> None:
    """Render strategy analysis section with safe fallbacks."""
    strategy_analysis = safe_get(individual_data, "strategy_analysis", {})

    if not strategy_analysis:
        return

    st.markdown("#### 🎯 Strategy Analysis")

    col1, col2, col3 = st.columns(3)

    with col1:
        development_approach = safe_get(strategy_analysis, "development_approach", "N/A")
        formatted_value = (
            development_approach.title()
            if isinstance(development_approach, str) and development_approach != "N/A"
            else "N/A"
        )
        st.metric(
            label="Development Approach",
            value=formatted_value,
            help="The team's approach to development",
        )

    with col2:
        time_management = safe_get(strategy_analysis, "time_management", "N/A")
        formatted_value = (
            time_management.title()
            if isinstance(time_management, str) and time_management != "N/A"
            else "N/A"
        )
        st.metric(
            label="Time Management",
            value=formatted_value,
            help="How well the team managed their time",
        )

    with col3:
        risk_management = safe_get(strategy_analysis, "risk_management", "N/A")
        formatted_value = (
            risk_management.title()
            if isinstance(risk_management, str) and risk_management != "N/A"
            else "N/A"
        )
        st.metric(
            label="Risk Management",
            value=formatted_value,
            help="The team's approach to managing risks",
        )


def _render_contributors(individual_data: dict[str, Any]) -> None:
    """Render contributors section with safe fallbacks."""
    contributors = safe_get(individual_data, "contributors", [])

    if not contributors:
        st.info("📭 No individual contributor data available")
        return

    st.markdown("#### 👤 Individual Contributors")

    for contributor in contributors:
        member_name = safe_get(contributor, "member_name", "Unknown")
        commit_count = safe_get(contributor, "commit_count", 0)
        skill_assessment = safe_get(contributor, "skill_assessment", "N/A")
        actionable_feedback = safe_get(contributor, "actionable_feedback", "")

        with st.expander(f"**{member_name}**", expanded=False):
            col1, col2 = st.columns(2)

            with col1:
                st.metric(
                    label="Commits",
                    value=commit_count,
                    help="Number of commits by this contributor",
                )

            with col2:
                formatted_skill = (
                    skill_assessment.title()
                    if isinstance(skill_assessment, str) and skill_assessment != "N/A"
                    else "N/A"
                )
                st.metric(
                    label="Skill Assessment",
                    value=formatted_skill,
                    help="Assessed skill level of this contributor",
                )

            if actionable_feedback:
                st.markdown("**💡 Actionable Feedback:**")
                st.markdown(actionable_feedback)
            else:
                st.info("No actionable feedback available for this contributor.")
