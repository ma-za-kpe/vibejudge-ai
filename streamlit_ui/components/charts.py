"""
Plotly chart generators for the Streamlit Organizer Dashboard.

This module provides functions to create visualizations for technology trends
and progress monitoring using Plotly and Streamlit components.
"""

from typing import Any

import plotly.graph_objects as go
import streamlit as st


def create_technology_trends_chart(trends: list[dict[str, Any]]) -> go.Figure:
    """
    Create a bar chart for technology trends.

    Args:
        trends: List of technology trend dictionaries with keys:
            - technology: str (name of the technology)
            - usage_count: int (number of times used)
            - category: str (optional, e.g., "language", "framework")

    Returns:
        Plotly Figure object with configured bar chart

    Example:
        >>> trends = [
        ...     {"technology": "Python", "usage_count": 120},
        ...     {"technology": "JavaScript", "usage_count": 95}
        ... ]
        >>> fig = create_technology_trends_chart(trends)
        >>> fig.show()
    """
    if not trends:
        # Return empty figure with message
        fig = go.Figure()
        fig.add_annotation(
            text="No technology trends data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font={"size": 14, "color": "gray"},
        )
        fig.update_layout(
            title="Technology Trends",
            height=400,
            xaxis={"visible": False},
            yaxis={"visible": False},
        )
        return fig

    # Extract data for chart
    technologies = [t["technology"] for t in trends]
    usage_counts = [t["usage_count"] for t in trends]

    # Create bar chart
    fig = go.Figure(
        data=[
            go.Bar(
                x=technologies,
                y=usage_counts,
                marker_color="lightblue",
                text=usage_counts,
                textposition="auto",
                hovertemplate="<b>%{x}</b><br>Usage Count: %{y}<extra></extra>",
            )
        ]
    )

    # Configure layout
    fig.update_layout(
        title={
            "text": "Technology Trends",
            "x": 0.5,
            "xanchor": "center",
            "font": {"size": 18, "color": "#262730"},
        },
        xaxis_title="Technology",
        yaxis_title="Usage Count",
        height=400,
        template="plotly_white",
        hovermode="x unified",
        showlegend=False,
        margin={"l": 50, "r": 50, "t": 80, "b": 50},
    )

    # Style axes
    fig.update_xaxes(
        tickangle=-45, tickfont={"size": 12}, title_font={"size": 14, "color": "#262730"}
    )
    fig.update_yaxes(
        tickfont={"size": 12}, title_font={"size": 14, "color": "#262730"}, gridcolor="lightgray"
    )

    return fig


def create_progress_bar(progress_percent: float) -> None:
    """
    Display a progress bar using Streamlit's st.progress component.

    Args:
        progress_percent: Progress percentage (0-100)

    Example:
        >>> create_progress_bar(45.5)  # Shows 45.5% progress
        >>> create_progress_bar(100.0)  # Shows complete progress

    Note:
        This function directly renders to Streamlit and returns None.
        The progress_percent is clamped to [0, 100] range.
    """
    # Clamp progress to valid range [0, 100]
    clamped_progress = max(0.0, min(100.0, progress_percent))

    # Convert to 0-1 range for st.progress
    progress_value = clamped_progress / 100.0

    # Display progress bar
    st.progress(progress_value)

    # Display percentage text below progress bar
    st.caption(f"Progress: {clamped_progress:.1f}%")
