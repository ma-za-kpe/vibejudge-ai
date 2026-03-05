"""Create Hackathon page object."""

from datetime import datetime, timedelta

from pages.base_page import BasePage


class CreateHackathonPage(BasePage):
    """Create Hackathon form page object."""

    def navigate(self):
        """Navigate to Create Hackathon page."""
        super().navigate("1_🎯_Create_Hackathon")

    # ========================================================================
    # FORM FILLING
    # ========================================================================

    def fill_basic_info(self, name: str, description: str, start_date: str, end_date: str):
        """Fill basic hackathon information."""
        self.fill_input("Hackathon Name", name)
        self.fill_input("Description", description)

        # Dates - format: YYYY-MM-DD
        start_input = self.page.get_by_label("Start Date")
        start_input.fill(start_date)

        end_input = self.page.get_by_label("End Date")
        end_input.fill(end_date)

    def set_budget(self, budget: float):
        """Set budget limit."""
        budget_input = self.page.get_by_label("Budget Limit (USD)")
        budget_input.fill(str(budget))

    def select_agents(self, bug_hunter=True, performance=True, innovation=True, ai_detection=True):
        """Select which AI agents to enable."""
        if bug_hunter:
            self.check_checkbox("🐛 Bug Hunter", True)
        if performance:
            self.check_checkbox("⚡ Performance Analyzer", True)
        if innovation:
            self.check_checkbox("💡 Innovation Scorer", True)
        if ai_detection:
            self.check_checkbox("🤖 AI Detection", True)

    def set_weights(self, bug_hunter=0.3, performance=0.3, innovation=0.3, ai_detection=0.1):
        """Set scoring weights."""
        # Fill weight inputs
        self.page.get_by_label("Bug Hunter Weight").fill(str(bug_hunter))
        self.page.get_by_label("Performance Weight").fill(str(performance))
        self.page.get_by_label("Innovation Weight").fill(str(innovation))
        self.page.get_by_label("AI Detection Weight").fill(str(ai_detection))

    def set_ai_policy(self, policy: str = "ai_assisted"):
        """Set AI policy mode."""
        self.select_option("AI Policy Mode", policy)

    def submit_form(self):
        """Submit the create hackathon form."""
        self.click_button("Create Hackathon")

    # ========================================================================
    # COMPLETE FLOWS
    # ========================================================================

    def create_hackathon(
        self,
        name: str,
        description: str,
        start_date: str = None,
        end_date: str = None,
        budget: float = None,
        agents: dict = None,
        weights: dict = None,
    ) -> str:
        """
        Complete flow to create a hackathon.

        Returns:
            hack_id if successful
        """
        # Default dates if not provided
        if not start_date:
            start_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

        # Fill form
        self.fill_basic_info(name, description, start_date, end_date)

        if budget:
            self.set_budget(budget)

        if agents:
            self.select_agents(**agents)

        if weights:
            self.set_weights(**weights)

        # Submit
        self.submit_form()

        # Wait for success
        self.wait_for_text("✅ Hackathon created successfully!")

        # Extract hack_id
        return self.get_created_hack_id()

    def create_default_hackathon(self) -> str:
        """Create a hackathon with default settings."""
        return self.create_hackathon(
            name="E2E Test Hackathon", description="Automated end-to-end test hackathon"
        )

    # ========================================================================
    # RESULT EXTRACTION
    # ========================================================================

    def get_created_hack_id(self) -> str:
        """Extract hack_id from success message."""
        # Look for code block with hack_id
        hack_id_element = self.page.locator("text=/Hackathon ID.*`(\\w+)`/").first
        text = hack_id_element.inner_text()
        # Extract hack_id from text
        import re

        match = re.search(r"`(\w+)`", text)
        if match:
            return match.group(1)
        return ""

    # ========================================================================
    # VALIDATION
    # ========================================================================

    def assert_validation_error(self, message: str):
        """Assert validation error is shown."""
        self.assert_error(message)

    def assert_creation_success(self):
        """Assert hackathon was created successfully."""
        self.assert_success("Hackathon created successfully")
        self.assert_text_visible("Hackathon ID")
        self.assert_text_visible("Status: DRAFT")
