"""Settings and profile management page.

This page allows users to view their profile, manage API keys, and view usage statistics.
"""

import logging
from datetime import datetime

import streamlit as st
from components.api_client import APIClient, APIError
from components.auth import require_authentication

logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Settings - VibeJudge AI",
    page_icon="⚙️",
    layout="wide",
)


@require_authentication
def main() -> None:
    """Main settings page."""
    st.title("⚙️ Settings & Profile")

    # Get API client
    api_client = APIClient(
        base_url=st.session_state["api_base_url"],
        api_key=st.session_state["api_key"],
    )

    # Create tabs for different sections
    tab1, tab2, tab3 = st.tabs(["👤 Profile", "🔑 API Keys", "📊 Usage Statistics"])

    # Tab 1: Profile Information
    with tab1:
        render_profile_section(api_client)

    # Tab 2: API Key Management
    with tab2:
        render_api_keys_section(api_client)

    # Tab 3: Usage Statistics
    with tab3:
        render_usage_section(api_client)


def render_profile_section(api_client: APIClient) -> None:
    """Render profile information section."""
    st.markdown("### Profile Information")

    try:
        # Fetch profile data
        profile = api_client.get("/organizers/me")

        # Display profile in columns
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Name:**")
            st.info(profile.get("name", "N/A"))

            st.markdown("**Organization:**")
            st.info(profile.get("organization", "N/A"))

        with col2:
            st.markdown("**Email:**")
            st.info(profile.get("email", "N/A"))

            st.markdown("**Tier:**")
            tier = profile.get("tier", "free").upper()
            st.info(f"🎯 {tier}")

        # Additional stats
        st.markdown("---")
        st.markdown("### Account Statistics")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Hackathons Created", profile.get("hackathon_count", 0))

        with col2:
            created_at = profile.get("created_at")
            if created_at:
                try:
                    created_date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    st.metric("Member Since", created_date.strftime("%b %Y"))
                except Exception:
                    st.metric("Member Since", "N/A")
            else:
                st.metric("Member Since", "N/A")

        with col3:
            st.metric("Account Status", "✅ Active")

    except APIError as e:
        st.error(f"Failed to load profile: {str(e)}")
        logger.error(f"Profile fetch error: {str(e)}")


def render_api_keys_section(api_client: APIClient) -> None:
    """Render API key management section."""
    st.markdown("### API Key Management")

    # Create new API key section
    with st.expander("➕ Create New API Key"), st.form("create_api_key_form"):
        st.markdown("Create a new API key for your account.")

        col1, col2 = st.columns(2)

        with col1:
            tier = st.selectbox(
                "Tier",
                options=["FREE", "STARTER", "PRO", "ENTERPRISE"],
                help="API key tier determines rate limits and quotas",
            )

        with col2:
            expires_days = st.number_input(
                "Expires in (days)",
                min_value=0,
                max_value=365,
                value=0,
                help="0 = never expires",
            )

        hackathon_id = st.text_input(
            "Hackathon ID (optional)",
            placeholder="Leave empty for account-wide key",
            help="Scope key to specific hackathon",
        )

        submit_button = st.form_submit_button("Create API Key", type="primary")

        if submit_button:
            try:
                # Calculate expiration date
                expires_at = None
                if expires_days > 0:
                    from datetime import timedelta

                    expires_at = (datetime.utcnow() + timedelta(days=expires_days)).isoformat()

                # Create API key
                payload = {"tier": tier.lower()}
                if hackathon_id:
                    payload["hackathon_id"] = hackathon_id
                if expires_at:
                    payload["expires_at"] = expires_at

                result = api_client.post("/api-keys", json=payload)

                # Display new API key
                st.success("✅ API key created successfully!")
                st.warning("⚠️ **IMPORTANT**: Save your API key now! It will not be shown again.")
                st.code(result.get("api_key"), language="text")

                # Rerun to refresh key list
                st.rerun()

            except APIError as e:
                st.error(f"Failed to create API key: {str(e)}")
                logger.error(f"API key creation error: {str(e)}")

    # List existing API keys
    st.markdown("---")
    st.markdown("### Your API Keys")

    try:
        # Fetch API keys
        response = api_client.get("/api-keys")
        api_keys = response.get("api_keys", [])

        if not api_keys:
            st.info("No API keys found. Create one above to get started.")
        else:
            for key in api_keys:
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 2])

                    with col1:
                        # Show masked key
                        key_id = key.get("api_key_id", "N/A")
                        st.markdown(f"**Key ID:** `{key_id[:16]}...`")

                    with col2:
                        # Show tier
                        tier = key.get("tier", "free").upper()
                        st.markdown(f"**Tier:** {tier}")

                    with col3:
                        # Show status
                        active = key.get("active", False)
                        deprecated = key.get("deprecated", False)
                        expired = False

                        expires_at = key.get("expires_at")
                        if expires_at:
                            try:
                                exp_date = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                                if exp_date < datetime.now(exp_date.tzinfo):
                                    expired = True
                            except Exception:
                                pass

                        if not active:
                            status = "🔴 Revoked"
                        elif expired:
                            status = "⏰ Expired"
                        elif deprecated:
                            status = "⚠️ Deprecated"
                        else:
                            status = "✅ Active"

                        st.markdown(f"**Status:** {status}")

                    with col4:
                        # Action buttons
                        if active and not expired:
                            col_a, col_b = st.columns(2)

                            with col_a:
                                if st.button(
                                    "🔄 Rotate", key=f"rotate_{key_id}", use_container_width=True
                                ):
                                    try:
                                        result = api_client.post(
                                            f"/api-keys/{key_id}/rotate", json={}
                                        )
                                        st.success("✅ Key rotated! New key:")
                                        st.code(result.get("api_key"), language="text")
                                        st.rerun()
                                    except APIError as e:
                                        st.error(f"Rotation failed: {str(e)}")

                            with col_b:
                                if st.button(
                                    "🗑️ Revoke", key=f"revoke_{key_id}", use_container_width=True
                                ):
                                    try:
                                        api_client.delete(f"/api-keys/{key_id}")
                                        st.success("✅ Key revoked")
                                        st.rerun()
                                    except APIError as e:
                                        st.error(f"Revocation failed: {str(e)}")

                    # Show additional details in expander
                    with st.expander("View Details"):
                        detail_col1, detail_col2 = st.columns(2)

                        with detail_col1:
                            st.markdown(
                                f"**Rate Limit:** {key.get('rate_limit_per_second', 0)} req/sec"
                            )
                            st.markdown(f"**Daily Quota:** {key.get('daily_quota', 0)} req/day")
                            st.markdown(f"**Budget Limit:** ${key.get('budget_limit_usd', 0):.2f}")

                        with detail_col2:
                            st.markdown(f"**Total Requests:** {key.get('total_requests', 0)}")
                            st.markdown(f"**Total Cost:** ${key.get('total_cost_usd', 0):.4f}")

                            last_used = key.get("last_used_at")
                            if last_used:
                                try:
                                    last_used_date = datetime.fromisoformat(
                                        last_used.replace("Z", "+00:00")
                                    )
                                    st.markdown(
                                        f"**Last Used:** {last_used_date.strftime('%Y-%m-%d %H:%M')}"
                                    )
                                except Exception:
                                    st.markdown("**Last Used:** N/A")
                            else:
                                st.markdown("**Last Used:** Never")

                    st.markdown("---")

    except APIError as e:
        st.error(f"Failed to load API keys: {str(e)}")
        logger.error(f"API keys fetch error: {str(e)}")


def render_usage_section(api_client: APIClient) -> None:
    """Render usage statistics section."""
    st.markdown("### Usage Statistics")

    # Date range selector
    col1, col2 = st.columns(2)

    with col1:
        start_date = st.date_input(
            "Start Date",
            value=datetime.now().replace(day=1),
            help="Start date for usage statistics",
        )

    with col2:
        end_date = st.date_input(
            "End Date",
            value=datetime.now(),
            help="End date for usage statistics",
        )

    # Fetch usage statistics
    if st.button("📊 Load Usage Statistics", type="primary"):
        try:
            # Format dates
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")

            # Fetch usage summary
            response = api_client.get(f"/usage/summary?start_date={start_str}&end_date={end_str}")

            # Display summary metrics
            st.markdown("---")
            st.markdown("### Summary")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Total Requests", response.get("total_requests", 0))

            with col2:
                st.metric("Successful", response.get("successful_requests", 0))

            with col3:
                st.metric("Failed", response.get("failed_requests", 0))

            with col4:
                total_cost = response.get("total_cost_usd", 0)
                st.metric("Total Cost", f"${total_cost:.4f}")

            # Display daily breakdown
            daily_usage = response.get("daily_usage", [])
            if daily_usage:
                st.markdown("---")
                st.markdown("### Daily Breakdown")

                for day in daily_usage:
                    with st.expander(f"📅 {day.get('date', 'N/A')}"):
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            st.metric("Requests", day.get("request_count", 0))

                        with col2:
                            st.metric("Successful", day.get("successful_requests", 0))

                        with col3:
                            cost = day.get("total_cost_usd", 0)
                            st.metric("Cost", f"${cost:.4f}")

            # Export button
            st.markdown("---")
            if st.button("📥 Export to CSV", use_container_width=True):
                try:
                    # Note: This would need to handle the streaming response properly
                    st.info("CSV export functionality requires download handling")
                    export_url = f"{st.session_state['api_base_url']}/usage/export?start_date={start_str}&end_date={end_str}"
                    st.markdown(f"[Download CSV]({export_url})")
                except Exception as e:
                    st.error(f"Export failed: {str(e)}")

        except APIError as e:
            st.error(f"Failed to load usage statistics: {str(e)}")
            logger.error(f"Usage statistics fetch error: {str(e)}")


if __name__ == "__main__":
    main()
