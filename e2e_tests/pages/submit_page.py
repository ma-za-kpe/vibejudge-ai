"""Public Submission page object (for participants)."""
from playwright.sync_api import expect
from pages.base_page import BasePage


class SubmitPage(BasePage):
    """Public submission form page object."""

    def navigate(self, hack_id: str = None):
        """
        Navigate to public submission page.

        Args:
            hack_id: Optional hack_id to navigate to specific hackathon submission
        """
        if hack_id:
            # Navigate to specific hackathon submission page
            self.page.goto(f"{self.base_url}/?page=submit&hack_id={hack_id}")
        else:
            # Navigate to general submit page
            super().navigate("Submit")

        self.wait_for_streamlit_ready()

    # ========================================================================
    # HACKATHON SELECTION
    # ========================================================================

    def has_hackathon_selector(self) -> bool:
        """Check if hackathon selector is visible."""
        return self.page.get_by_label("Select Hackathon").count() > 0

    def select_hackathon(self, name: str):
        """Select hackathon to submit to."""
        self.select_option("Select Hackathon", name)
        self.wait_for_streamlit_ready()

    def get_available_hackathons(self) -> list[str]:
        """Get list of available hackathons."""
        # Get all options from select box
        select = self.page.get_by_label("Select Hackathon")
        options = select.locator('option').all()
        return [opt.inner_text() for opt in options if opt.inner_text()]

    # ========================================================================
    # SUBMISSION FORM
    # ========================================================================

    def fill_team_name(self, name: str):
        """Fill team name."""
        self.fill_input("Team Name", name)

    def fill_repository_url(self, url: str):
        """Fill repository URL."""
        self.fill_input("Repository URL", url)

    def fill_email(self, email: str):
        """Fill contact email."""
        self.fill_input("Contact Email", email)

    def fill_description(self, description: str):
        """Fill project description."""
        textarea = self.page.get_by_label("Project Description")
        textarea.fill(description)

    def add_team_member(self, name: str, github_username: str):
        """Add a team member."""
        # Click add member button
        self.click_button("➕ Add Team Member")

        # Fill last row
        member_inputs = self.page.get_by_label("Member Name").all()
        github_inputs = self.page.get_by_label("GitHub Username").all()

        member_inputs[-1].fill(name)
        github_inputs[-1].fill(github_username)

    def remove_team_member(self, index: int):
        """Remove team member at index."""
        remove_buttons = self.page.get_by_role("button", name="🗑️").all()
        if index < len(remove_buttons):
            remove_buttons[index].click()
            self.wait_for_streamlit_ready(timeout=2000)

    def get_team_member_count(self) -> int:
        """Get number of team members."""
        return self.page.get_by_label("Member Name").count()

    # ========================================================================
    # SUBMISSION
    # ========================================================================

    def submit(self):
        """Submit the form."""
        self.click_button("🚀 Submit Project")
        self.wait_for_streamlit_ready()

    def get_submission_id(self) -> str:
        """Get submission ID from success message."""
        import re
        # Look for text like "Submission ID: sub_abc123"
        text = self.page.locator('text=/Submission ID:\\s+(sub_\\w+)/').first.inner_text()
        match = re.search(r'sub_\w+', text)
        if match:
            return match.group(0)
        return ""

    # ========================================================================
    # VALIDATION
    # ========================================================================

    def assert_submission_success(self):
        """Assert submission was successful."""
        self.assert_success("Submission received")
        self.assert_text_visible("Submission ID")

    def assert_duplicate_submission_error(self):
        """Assert duplicate submission error."""
        self.assert_error("already submitted")

    def assert_hackathon_closed_error(self):
        """Assert hackathon closed error."""
        self.assert_error("Hackathon is not accepting submissions")

    def assert_invalid_repo_error(self):
        """Assert invalid repository URL error."""
        self.assert_error("Invalid repository URL")

    def assert_required_field_error(self, field: str):
        """Assert required field validation error."""
        self.assert_error(f"{field} is required")

    def assert_email_validation_error(self):
        """Assert email validation error."""
        self.assert_error("Invalid email address")

    # ========================================================================
    # HACKATHON INFO DISPLAY
    # ========================================================================

    def get_hackathon_name(self) -> str:
        """Get displayed hackathon name."""
        return self.page.locator('h1, h2').first.inner_text()

    def get_hackathon_deadline(self) -> str:
        """Get submission deadline."""
        deadline_elem = self.page.locator('text=/Deadline:\\s+.+/').first
        if deadline_elem.count() > 0:
            text = deadline_elem.inner_text()
            return text.split("Deadline:")[1].strip()
        return ""

    def is_deadline_warning_visible(self) -> bool:
        """Check if deadline warning is visible."""
        return self.is_text_visible("⚠️ Deadline approaching")

    def is_hackathon_closed(self) -> bool:
        """Check if hackathon is closed for submissions."""
        return self.is_text_visible("🔒 Submissions closed")

    # ========================================================================
    # CONFIRMATION
    # ========================================================================

    def has_confirmation_checkbox(self) -> bool:
        """Check if terms/confirmation checkbox exists."""
        return self.page.get_by_label("I confirm").count() > 0

    def accept_terms(self):
        """Check the terms/confirmation checkbox."""
        checkbox = self.page.get_by_label("I confirm")
        if not checkbox.is_checked():
            checkbox.check()

    # ========================================================================
    # PREVIEW
    # ========================================================================

    def has_preview_mode(self) -> bool:
        """Check if preview mode is available."""
        return self.is_button_visible("👁️ Preview Submission")

    def open_preview(self):
        """Open submission preview."""
        self.click_button("👁️ Preview Submission")
        self.wait_for_streamlit_ready()

    def close_preview(self):
        """Close preview."""
        self.click_button("✖️ Close Preview")
        self.wait_for_streamlit_ready()
