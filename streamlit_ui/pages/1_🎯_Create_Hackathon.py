"""Create Hackathon Page

This page allows organizers to create new hackathons through a form interface.
It validates inputs and submits the data to the backend API.
"""

import logging
from datetime import datetime

import streamlit as st
from components.api_client import APIClient, APIError, ValidationError
from components.auth import is_authenticated

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Page configuration
st.set_page_config(page_title="Create Hackathon - VibeJudge AI", page_icon="🎯", layout="wide")


def validate_date_range(start_date: datetime, end_date: datetime) -> tuple[bool, str]:
    """Validate that end_date is after start_date.

    Args:
        start_date: The hackathon start date
        end_date: The hackathon end date

    Returns:
        A tuple of (is_valid, error_message). If valid, error_message is empty.
    """
    if end_date <= start_date:
        return False, "End date must be after start date"
    return True, ""


def validate_budget(budget_limit_usd: float | None) -> tuple[bool, str]:
    """Validate that budget is positive or empty.

    Args:
        budget_limit_usd: The budget limit in USD (can be None)

    Returns:
        A tuple of (is_valid, error_message). If valid, error_message is empty.
    """
    if budget_limit_usd is not None and budget_limit_usd <= 0:
        return False, "Budget must be a positive number"
    return True, ""


def render_hackathon_form() -> None:
    """Render the hackathon creation form."""
    st.title("🎯 Create New Hackathon")

    st.markdown("""
    Create a new hackathon event to start accepting submissions. Fill in the details below
    and click "Create Hackathon" to get started.
    """)

    # Create the form
    with st.form("hackathon_form", clear_on_submit=False):
        st.markdown("### Hackathon Details")

        # Name input
        name = st.text_input(
            "Hackathon Name *",
            placeholder="e.g., Spring Hackathon 2025",
            help="A descriptive name for your hackathon (1-200 characters)",
            max_chars=200,
        )

        # Description input
        description = st.text_area(
            "Description *",
            placeholder="Describe your hackathon, its goals, and what participants should build...",
            help="A detailed description of your hackathon (1-2000 characters)",
            max_chars=2000,
            height=150,
        )

        # Date inputs in two columns
        col1, col2 = st.columns(2)

        with col1:
            start_date = st.date_input("Start Date *", help="The date when the hackathon begins")

        with col2:
            end_date = st.date_input("End Date *", help="The date when the hackathon ends")

        # Budget input
        budget_limit_usd = st.number_input(
            "Budget Limit (USD)",
            min_value=0.0,
            value=None,
            step=10.0,
            format="%.2f",
            help="Optional: Set a maximum budget for AI analysis costs. Leave empty for no limit.",
        )

        st.markdown("---")
        st.markdown("### Judging Configuration")

        # AI Agents selection
        st.markdown("**Select AI Agents to Enable:**")
        col1, col2 = st.columns(2)
        
        with col1:
            bug_hunter = st.checkbox("🐛 Bug Hunter", value=True, help="Code quality, security, and testing")
            performance = st.checkbox("⚡ Performance Analyzer", value=True, help="Architecture, scalability, and performance")
        
        with col2:
            innovation = st.checkbox("💡 Innovation Scorer", value=True, help="Creativity, novelty, and documentation")
            ai_detection = st.checkbox("🤖 AI Detection", value=True, help="Development authenticity and AI usage")

        # Rubric weights
        st.markdown("**Scoring Weights** (must sum to 1.0):")
        col1, col2 = st.columns(2)
        
        with col1:
            bug_hunter_weight = st.number_input(
                "Bug Hunter Weight", 
                min_value=0.0, 
                max_value=1.0, 
                value=0.3, 
                step=0.05, 
                disabled=not bug_hunter,
                help="Weight for code quality, security, and testing analysis. Higher weight = more impact on final score."
            )
            performance_weight = st.number_input(
                "Performance Weight", 
                min_value=0.0, 
                max_value=1.0, 
                value=0.3, 
                step=0.05, 
                disabled=not performance,
                help="Weight for architecture, scalability, and performance analysis. Higher weight = more impact on final score."
            )
        
        with col2:
            innovation_weight = st.number_input(
                "Innovation Weight", 
                min_value=0.0, 
                max_value=1.0, 
                value=0.3, 
                step=0.05, 
                disabled=not innovation,
                help="Weight for creativity, novelty, and documentation analysis. Higher weight = more impact on final score."
            )
            ai_detection_weight = st.number_input(
                "AI Detection Weight", 
                min_value=0.0, 
                max_value=1.0, 
                value=0.1, 
                step=0.05, 
                disabled=not ai_detection,
                help="Weight for development authenticity and AI usage analysis. Higher weight = more impact on final score."
            )

        # AI Policy Mode
        ai_policy_mode = st.selectbox(
            "AI Policy Mode",
            options=["ai_assisted", "no_ai", "ai_generated"],
            index=0,
            help="How AI-generated code should be evaluated"
        )

        st.markdown("---")

        # Submit button
        submit_button = st.form_submit_button(
            "Create Hackathon", type="primary", use_container_width=True
        )

        # Handle form submission
        if submit_button:
            # Validate required fields
            if not name:
                st.error("❌ Hackathon name is required")
                return

            if not description:
                st.error("❌ Description is required")
                return

            # Convert dates to datetime objects (start of day and end of day)
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())

            # Validate date range
            date_valid, date_error = validate_date_range(start_datetime, end_datetime)
            if not date_valid:
                st.error(f"❌ {date_error}")
                return

            # Validate budget
            budget_valid, budget_error = validate_budget(budget_limit_usd)
            if not budget_valid:
                st.error(f"❌ {budget_error}")
                return

            # Validate at least one agent is selected
            agents_enabled = []
            if bug_hunter:
                agents_enabled.append("bug_hunter")
            if performance:
                agents_enabled.append("performance")
            if innovation:
                agents_enabled.append("innovation")
            if ai_detection:
                agents_enabled.append("ai_detection")
            
            if not agents_enabled:
                st.error("❌ At least one AI agent must be enabled")
                return

            # Validate rubric weights sum to 1.0
            total_weight = 0.0
            rubric_dimensions = []
            
            if bug_hunter:
                total_weight += bug_hunter_weight
                rubric_dimensions.append({
                    "name": "Code Quality",
                    "agent": "bug_hunter",
                    "weight": bug_hunter_weight,
                    "description": "Code quality, security, and testing"
                })
            
            if performance:
                total_weight += performance_weight
                rubric_dimensions.append({
                    "name": "Architecture",
                    "agent": "performance",
                    "weight": performance_weight,
                    "description": "Architecture, scalability, and performance"
                })
            
            if innovation:
                total_weight += innovation_weight
                rubric_dimensions.append({
                    "name": "Innovation",
                    "agent": "innovation",
                    "weight": innovation_weight,
                    "description": "Creativity, novelty, and documentation"
                })
            
            if ai_detection:
                total_weight += ai_detection_weight
                rubric_dimensions.append({
                    "name": "Authenticity",
                    "agent": "ai_detection",
                    "weight": ai_detection_weight,
                    "description": "Development authenticity and AI usage"
                })
            
            # Check if weights sum to 1.0 (with small tolerance for floating point)
            if abs(total_weight - 1.0) > 0.01:
                st.error(f"❌ Rubric weights must sum to 1.0 (current sum: {total_weight:.2f})")
                return

            # Prepare request payload
            payload = {
                "name": name,
                "description": description,
                "start_date": start_datetime.isoformat(),
                "end_date": end_datetime.isoformat(),
                "rubric": {
                    "name": "Custom Rubric",
                    "version": "1.0",
                    "max_score": 100.0,
                    "dimensions": rubric_dimensions
                },
                "agents_enabled": agents_enabled,
                "ai_policy_mode": ai_policy_mode
            }

            # Add budget if provided
            if budget_limit_usd is not None and budget_limit_usd > 0:
                payload["budget_limit_usd"] = budget_limit_usd

            # Submit to API
            try:
                with st.spinner("🚀 Creating hackathon..."):
                    # Get API client
                    api_client = APIClient(
                        st.session_state["api_base_url"], st.session_state["api_key"]
                    )

                    # Send POST request
                    response = api_client.post("/hackathons", payload)

                    # Display success message with hack_id
                    st.success("✅ Hackathon created successfully!")

                    # Display hackathon details
                    st.markdown("### Hackathon Created")
                    st.info(f"**Hackathon ID**: `{response.get('hack_id', 'N/A')}`")
                    st.info(f"**Name**: {response.get('name', 'N/A')}")
                    st.info(f"**Status**: {response.get('status', 'N/A').upper()}")

                    # Store hack_id in session state for activation
                    st.session_state["created_hack_id"] = response.get('hack_id')

                    # Clear cache to ensure fresh data on other pages
                    st.cache_data.clear()

                    logger.info(f"Hackathon created successfully: {response.get('hack_id')}")

                    # Show next steps
                    st.markdown("---")
                    st.markdown("### Next Steps")
                    st.info(
                        "Your hackathon is in **DRAFT** status. "
                        "Go to the **Manage Hackathons** page to activate it before participants can submit."
                    )

            except ValidationError as e:
                # Display validation errors inline
                st.error(f"❌ Validation Error: {str(e)}")
                logger.warning(f"Validation error during hackathon creation: {e}")

            except APIError as e:
                # Display generic API errors
                st.error(f"❌ Error: {str(e)}")
                logger.error(f"API error during hackathon creation: {e}")

                # Show retry button
                if st.button("🔄 Retry"):
                    st.rerun()


def main() -> None:
    """Main entry point for the Create Hackathon page."""
    # Check authentication
    if not is_authenticated():
        st.error("⚠️ Please authenticate first")
        st.info("Go to the home page to log in with your API key")
        st.stop()

    # Render the form
    render_hackathon_form()


if __name__ == "__main__":
    main()
