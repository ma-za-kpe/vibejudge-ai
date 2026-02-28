"""Settings page object."""
from playwright.sync_api import expect
from pages.base_page import BasePage


class SettingsPage(BasePage):
    """Settings & Configuration page object."""

    def navigate(self):
        """Navigate to Settings page."""
        super().navigate("5_⚙️_Settings")

    # ========================================================================
    # HACKATHON SELECTION
    # ========================================================================

    def select_hackathon(self, name: str):
        """Select hackathon to edit."""
        self.select_option("Select Hackathon to Edit", name)
        self.wait_for_streamlit_ready()

    # ========================================================================
    # SCORING WEIGHTS
    # ========================================================================

    def get_weight(self, dimension: str) -> float:
        """Get current weight for a scoring dimension."""
        # Map friendly names to input labels
        weight_map = {
            "code_quality": "Bug Hunter Weight",
            "performance": "Performance Weight",
            "innovation": "Innovation Weight",
            "ai_detection": "AI Detection Weight"
        }
        label = weight_map.get(dimension, dimension)
        input_elem = self.page.get_by_label(label)
        return float(input_elem.input_value())

    def set_weight(self, dimension: str, weight: float):
        """Set weight for scoring dimension."""
        weight_map = {
            "code_quality": "Bug Hunter Weight",
            "performance": "Performance Weight",
            "innovation": "Innovation Weight",
            "ai_detection": "AI Detection Weight"
        }
        label = weight_map.get(dimension, dimension)
        input_elem = self.page.get_by_label(label)
        input_elem.fill(str(weight))

    def get_weights_sum(self) -> float:
        """Get sum of all weights."""
        total = 0.0
        for dim in ["code_quality", "performance", "innovation", "ai_detection"]:
            total += self.get_weight(dim)
        return total

    # ========================================================================
    # AI POLICY
    # ========================================================================

    def get_ai_policy(self) -> str:
        """Get current AI policy mode."""
        # Look for selected radio button or dropdown value
        policy_select = self.page.get_by_label("AI Policy Mode")
        return policy_select.input_value()

    def set_ai_policy(self, policy: str):
        """Set AI policy mode."""
        self.select_option("AI Policy Mode", policy)
        self.wait_for_streamlit_ready()

    # ========================================================================
    # BUDGET LIMITS
    # ========================================================================

    def get_budget_limit(self) -> float:
        """Get current budget limit."""
        budget_input = self.page.get_by_label("Budget Limit (USD)")
        value = budget_input.input_value()
        return float(value) if value else 0.0

    def set_budget_limit(self, amount: float):
        """Set budget limit."""
        budget_input = self.page.get_by_label("Budget Limit (USD)")
        budget_input.fill(str(amount))

    def get_current_spend(self) -> float:
        """Get current spend amount."""
        value = self.get_metric("Current Spend")
        # Remove $ and convert
        return float(value.replace("$", ""))

    def get_remaining_budget(self) -> float:
        """Get remaining budget amount."""
        value = self.get_metric("Remaining Budget")
        return float(value.replace("$", ""))

    # ========================================================================
    # HACKATHON STATUS
    # ========================================================================

    def get_hackathon_status(self) -> str:
        """Get current hackathon status."""
        # Look for status badge or text
        status_elem = self.page.locator('text=/Status:\\s+(\\w+)/').first
        if status_elem.count() > 0:
            text = status_elem.inner_text()
            return text.split(":")[1].strip().lower()
        return ""

    def activate_hackathon(self):
        """Activate hackathon (DRAFT → ACTIVE)."""
        self.click_button("🟢 Activate Hackathon")
        self.wait_for_streamlit_ready()

    def pause_hackathon(self):
        """Pause hackathon (ACTIVE → PAUSED)."""
        self.click_button("⏸️ Pause Hackathon")
        self.wait_for_streamlit_ready()

    def resume_hackathon(self):
        """Resume hackathon (PAUSED → ACTIVE)."""
        self.click_button("▶️ Resume Hackathon")
        self.wait_for_streamlit_ready()

    def complete_hackathon(self):
        """Complete hackathon (ACTIVE → COMPLETED)."""
        self.click_button("🏁 Complete Hackathon")
        self.wait_for_streamlit_ready()

    # ========================================================================
    # SAVE CHANGES
    # ========================================================================

    def save_settings(self):
        """Save settings changes."""
        self.click_button("💾 Save Settings")
        self.wait_for_streamlit_ready()

    def has_unsaved_changes_warning(self) -> bool:
        """Check if unsaved changes warning is shown."""
        return self.is_text_visible("⚠️ You have unsaved changes")

    # ========================================================================
    # AGENT CONFIGURATION
    # ========================================================================

    def is_agent_enabled(self, agent_name: str) -> bool:
        """Check if specific agent is enabled."""
        agent_map = {
            "bug_hunter": "🐛 Bug Hunter",
            "performance": "⚡ Performance Analyzer",
            "innovation": "💡 Innovation Scorer",
            "ai_detection": "🤖 AI Detection"
        }
        label = agent_map.get(agent_name, agent_name)
        checkbox = self.page.get_by_label(label)
        return checkbox.is_checked()

    def toggle_agent(self, agent_name: str, enabled: bool):
        """Enable or disable an agent."""
        agent_map = {
            "bug_hunter": "🐛 Bug Hunter",
            "performance": "⚡ Performance Analyzer",
            "innovation": "💡 Innovation Scorer",
            "ai_detection": "🤖 AI Detection"
        }
        label = agent_map.get(agent_name, agent_name)
        self.check_checkbox(label, enabled)

    # ========================================================================
    # VALIDATION
    # ========================================================================

    def assert_weights_sum_to_one(self):
        """Assert that weights sum to 1.0."""
        total = self.get_weights_sum()
        assert abs(total - 1.0) < 0.01, f"Weights should sum to 1.0, got {total}"

    def assert_weights_validation_error(self):
        """Assert that weights validation error is shown."""
        self.assert_error("Weights must sum to 1.0")

    def assert_budget_validation_error(self):
        """Assert that budget validation error is shown."""
        self.assert_error("Budget limit must be positive")

    def assert_settings_saved(self):
        """Assert that settings were saved successfully."""
        self.assert_success("Settings saved successfully")

    # ========================================================================
    # DANGER ZONE
    # ========================================================================

    def has_delete_section(self) -> bool:
        """Check if delete hackathon section exists."""
        return self.is_text_visible("🚨 Danger Zone")

    def delete_hackathon(self, confirm: bool = True):
        """Delete hackathon (with confirmation)."""
        self.click_button("🗑️ Delete Hackathon")

        if confirm:
            # Look for confirmation dialog
            self.wait_for_text("Are you sure?")
            confirm_button = self.page.get_by_role("button", name="Confirm Delete")
            confirm_button.click()
        else:
            # Cancel
            cancel_button = self.page.get_by_role("button", name="Cancel")
            cancel_button.click()

        self.wait_for_streamlit_ready()

    # ========================================================================
    # DATES
    # ========================================================================

    def update_dates(self, start_date: str, end_date: str):
        """Update hackathon start and end dates."""
        start_input = self.page.get_by_label("Start Date")
        start_input.fill(start_date)

        end_input = self.page.get_by_label("End Date")
        end_input.fill(end_date)

    def assert_date_validation_error(self):
        """Assert that date validation error is shown."""
        self.assert_error("End date must be after start date")
