"""Manage Hackathons page object."""

from pages.base_page import BasePage


class ManageHackathonsPage(BasePage):
    """Manage Hackathons page object (list view)."""

    def navigate(self):
        """Navigate to home page / hackathon list."""
        super().navigate("VibeJudge_AI_Dashboard")  # Home page

    # ========================================================================
    # HACKATHON LIST
    # ========================================================================

    def get_hackathon_count(self) -> int:
        """Get number of hackathons displayed."""
        # Look for hackathon cards or list items
        cards = self.page.locator('[data-testid="stExpander"]').all()
        return len(cards)

    def get_hackathon_names(self) -> list[str]:
        """Get list of all hackathon names."""
        cards = self.page.locator('[data-testid="stExpander"]').all()
        names = []
        for card in cards:
            # Extract name from expander header
            header = card.locator("summary").inner_text()
            names.append(header)
        return names

    def has_hackathon(self, name: str) -> bool:
        """Check if hackathon with given name exists."""
        return name in self.get_hackathon_names()

    def expand_hackathon(self, name: str):
        """Expand hackathon details."""
        expander = self.page.locator(f'[data-testid="stExpander"]:has-text("{name}")').first
        summary = expander.locator("summary")
        summary.click()
        self.wait_for_streamlit_ready(timeout=2000)

    # ========================================================================
    # HACKATHON DETAILS
    # ========================================================================

    def get_hackathon_status(self, name: str) -> str:
        """Get status for specific hackathon."""
        self.expand_hackathon(name)
        # Look for status badge
        status_elem = self.page.locator("text=/Status:\\s+(\\w+)/").first
        if status_elem.count() > 0:
            text = status_elem.inner_text()
            return text.split(":")[1].strip().lower()
        return ""

    def get_hackathon_submission_count(self, name: str) -> int:
        """Get submission count for hackathon."""
        self.expand_hackathon(name)
        value = self.get_metric("Submissions")
        return int(value)

    def get_hackathon_participant_count(self, name: str) -> int:
        """Get participant count for hackathon."""
        self.expand_hackathon(name)
        value = self.get_metric("Participants")
        return int(value)

    # ========================================================================
    # ACTIONS
    # ========================================================================

    def navigate_to_hackathon(self, name: str, page_name: str):
        """
        Navigate to specific page for a hackathon.

        Args:
            name: Hackathon name
            page_name: Page to navigate to (e.g., "Live Dashboard", "Results", "Settings")
        """
        self.expand_hackathon(name)

        # Look for navigation button
        button_text = f"Go to {page_name}"
        self.click_button(button_text)
        self.wait_for_streamlit_ready()

    def quick_view_results(self, name: str):
        """Quick view results for hackathon."""
        self.navigate_to_hackathon(name, "Results")

    def quick_view_dashboard(self, name: str):
        """Quick view dashboard for hackathon."""
        self.navigate_to_hackathon(name, "Live Dashboard")

    # ========================================================================
    # FILTERING & SORTING
    # ========================================================================

    def filter_by_status(self, status: str):
        """Filter hackathons by status."""
        self.select_option("Filter by Status", status)
        self.wait_for_streamlit_ready()

    def sort_by(self, field: str):
        """
        Sort hackathons.

        Args:
            field: "name", "created_at", "start_date", "submission_count"
        """
        sort_map = {
            "name": "Name (A-Z)",
            "created_at": "Created Date",
            "start_date": "Start Date",
            "submission_count": "Submissions",
        }
        option = sort_map.get(field, field)
        self.select_option("Sort by", option)
        self.wait_for_streamlit_ready()

    # ========================================================================
    # SEARCH
    # ========================================================================

    def search(self, query: str):
        """Search hackathons by name."""
        search_input = self.page.get_by_placeholder("Search hackathons...")
        search_input.fill(query)
        self.wait_for_streamlit_ready()

    def clear_search(self):
        """Clear search query."""
        search_input = self.page.get_by_placeholder("Search hackathons...")
        search_input.fill("")
        self.wait_for_streamlit_ready()

    # ========================================================================
    # PAGINATION
    # ========================================================================

    def has_pagination(self) -> bool:
        """Check if pagination controls are visible."""
        return self.is_button_visible("Next ▶️") or self.is_button_visible("◀️ Previous")

    def get_current_page(self) -> int:
        """Get current page number."""
        import re

        page_text = self.page.locator("text=/Page \\d+ of/").inner_text()
        match = re.search(r"Page (\d+) of", page_text)
        if match:
            return int(match.group(1))
        return 1

    def get_total_pages(self) -> int:
        """Get total number of pages."""
        import re

        page_text = self.page.locator("text=/Page \\d+ of \\d+/").inner_text()
        match = re.search(r"of (\d+)", page_text)
        if match:
            return int(match.group(1))
        return 1

    def next_page(self):
        """Go to next page."""
        self.click_button("Next ▶️")
        self.wait_for_streamlit_ready()

    def previous_page(self):
        """Go to previous page."""
        self.click_button("◀️ Previous")
        self.wait_for_streamlit_ready()

    # ========================================================================
    # EMPTY STATE
    # ========================================================================

    def assert_no_hackathons_message(self):
        """Assert no hackathons message is shown."""
        self.assert_text_visible("No hackathons found")

    def assert_create_hackathon_prompt(self):
        """Assert create hackathon prompt is shown."""
        self.assert_text_visible("Create your first hackathon")

    # ========================================================================
    # QUICK STATS
    # ========================================================================

    def get_total_hackathons_stat(self) -> int:
        """Get total hackathons count from stats."""
        value = self.get_metric("Total Hackathons")
        return int(value)

    def get_active_hackathons_stat(self) -> int:
        """Get active hackathons count."""
        value = self.get_metric("Active")
        return int(value)

    def get_completed_hackathons_stat(self) -> int:
        """Get completed hackathons count."""
        value = self.get_metric("Completed")
        return int(value)
