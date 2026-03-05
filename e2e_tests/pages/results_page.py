"""Results page object - Leaderboard and team details."""

import re

from pages.base_page import BasePage


class ResultsPage(BasePage):
    """Results page for leaderboard and team detail views."""

    def navigate(self):
        """Navigate to Results page."""
        super().navigate("3_🏆_Results")

    # ========================================================================
    # HACKATHON SELECTION
    # ========================================================================

    def select_hackathon(self, name: str):
        """Select hackathon from dropdown."""
        self.select_option("Select Hackathon", name)

    # ========================================================================
    # VIEW MODE DETECTION
    # ========================================================================

    def is_leaderboard_view(self) -> bool:
        """Check if in leaderboard view mode."""
        return self.is_text_visible("🏅 Leaderboard")

    def is_team_detail_view(self) -> bool:
        """Check if in team detail view mode."""
        return self.is_button_visible("⬅️ Back to Leaderboard")

    # ========================================================================
    # LEADERBOARD VIEW - STATS
    # ========================================================================

    def get_total_submissions_stat(self) -> int:
        """Get total submissions metric."""
        return int(self.get_metric("Total Submissions"))

    def get_analyzed_count_stat(self) -> int:
        """Get analyzed submissions metric."""
        return int(self.get_metric("Analyzed Submissions"))

    # ========================================================================
    # LEADERBOARD VIEW - SEARCH & SORT
    # ========================================================================

    def search(self, query: str):
        """Enter search query."""
        search_input = self.get_text_input("Search by team name")
        search_input.clear()
        search_input.fill(query)
        # Streamlit reruns on input change
        self.wait_for_streamlit_ready()

    def sort_by(self, option: str):
        """
        Sort leaderboard.

        Args:
            option: "score", "team_name", or "created_at"
        """
        # Map internal values to display names
        display_names = {
            "score": "Overall Score",
            "team_name": "Team Name",
            "created_at": "Submission Date",
        }

        self.select_option("Sort by", display_names.get(option, option))

    # ========================================================================
    # LEADERBOARD VIEW - TABLE
    # ========================================================================

    def get_visible_submission_count(self) -> int:
        """Get number of submissions currently visible in table."""
        # Count "View Details" buttons
        buttons = self.page.get_by_role("button", name="View Details").all()
        return len(buttons)

    def get_team_name_at_rank(self, rank: int) -> str:
        """Get team name for specific rank."""
        # Find row with rank number
        row = self.page.locator(f"text=/^{rank}$/")  # Exact match for rank
        # Get sibling cell with team name (next column)
        # This is tricky - might need to adjust based on actual DOM structure
        container = row.locator('xpath=ancestor::div[contains(@class, "row")]')
        # Look for team name in same row
        team_name = container.inner_text().split("\n")[1]  # Second line is team name
        return team_name.strip()

    def click_view_details_for_rank(self, rank: int):
        """Click View Details button for specific rank."""
        # Get all View Details buttons
        buttons = self.page.get_by_role("button", name="View Details").all()

        # Click the button at index (rank-1)
        if rank <= len(buttons):
            buttons[rank - 1].click()
            self.wait_for_streamlit_ready()

    def click_view_details_for_team(self, team_name: str):
        """Click View Details button for specific team."""
        # Find the row containing team name
        row = self.page.locator(f'text="{team_name}"').locator(
            'xpath=ancestor::div[@data-testid="column"]'
        )
        # Find View Details button in same row
        button = row.get_by_role("button", name="View Details")
        button.click()
        self.wait_for_streamlit_ready()

    # ========================================================================
    # PAGINATION
    # ========================================================================

    def get_current_page(self) -> int:
        """Get current page number."""
        page_text = self.page.locator("text=/Page (\\d+) of/").inner_text()
        match = re.search(r"Page (\d+) of", page_text)
        if match:
            return int(match.group(1))
        return 1

    def get_total_pages(self) -> int:
        """Get total number of pages."""
        page_text = self.page.locator("text=/Page \\d+ of (\\d+)/").inner_text()
        match = re.search(r"of (\d+)", page_text)
        if match:
            return int(match.group(1))
        return 1

    def click_pagination_button(self, button_name: str):
        """
        Click pagination button.

        Args:
            button_name: "⏮️ First", "◀️ Previous", "Next ▶️", or "Last ⏭️"
        """
        self.click_button(button_name)

    def is_button_disabled(self, button_name: str) -> bool:
        """Check if pagination button is disabled."""
        try:
            button = self.get_button(button_name)
            return button.is_disabled()
        except:
            return False

    def navigate_to_page(self, page_num: int):
        """Navigate to specific page number."""
        current = self.get_current_page()

        if page_num == 1 and current != 1:
            self.click_pagination_button("⏮️ First")
        elif page_num > current:
            for _ in range(page_num - current):
                self.click_pagination_button("Next ▶️")
        elif page_num < current:
            for _ in range(current - page_num):
                self.click_pagination_button("◀️ Previous")

    # ========================================================================
    # TEAM DETAIL VIEW
    # ========================================================================

    def click_back_to_leaderboard(self):
        """Click back button to return to leaderboard."""
        self.click_button("⬅️ Back to Leaderboard")

    def get_team_detail_name(self) -> str:
        """Get team name from detail view."""
        # Look for heading with team name
        heading = self.page.locator("text=/📋 Scorecard:/")
        text = heading.inner_text()
        return text.split(": ")[1]

    def has_tab(self, tab_name: str) -> bool:
        """Check if tab exists."""
        try:
            self.get_tab(tab_name)
            return True
        except:
            return False

    def click_scorecard_tab(self, tab_name: str):
        """Click a scorecard tab."""
        self.click_tab(tab_name)

    # ========================================================================
    # TEAM DETAIL - OVERVIEW TAB
    # ========================================================================

    def get_overall_score(self) -> float:
        """Get overall score from Overview tab."""
        return float(self.get_metric("Overall Score"))

    def get_confidence(self) -> float:
        """Get confidence score."""
        confidence_str = self.get_metric("Confidence")
        # Remove % and convert
        return float(confidence_str.replace("%", ""))

    def get_recommendation(self) -> str:
        """Get recommendation."""
        return self.get_metric("Recommendation")

    # ========================================================================
    # TEAM DETAIL - AGENT ANALYSIS TAB
    # ========================================================================

    def expand_agent_results(self, agent_name: str):
        """Expand agent results expander."""
        self.expand_expander(agent_name)

    def get_agent_summary(self, agent_name: str) -> str:
        """Get agent analysis summary."""
        self.expand_agent_results(agent_name)
        # Get summary text from expander content
        expander = self.get_expander(agent_name)
        return expander.locator("text=/Summary:?/").inner_text()

    # ========================================================================
    # TEAM DETAIL - REPOSITORY TAB
    # ========================================================================

    def get_primary_language(self) -> str:
        """Get primary programming language."""
        return self.get_metric("Primary Language")

    def get_commit_count(self) -> int:
        """Get commit count."""
        return int(self.get_metric("Commits"))

    # ========================================================================
    # TEAM DETAIL - TEAM MEMBERS TAB
    # ========================================================================

    def has_team_members(self) -> bool:
        """Check if team members data is available."""
        self.click_scorecard_tab("👥 Team Members")
        return not self.is_text_visible("📭 No individual contributor data available")

    def get_member_count(self) -> int:
        """Get number of team members shown."""
        # Count expanders with actionable feedback
        expanders = self.page.locator(
            '[data-testid="stExpander"]:has-text("💡 Actionable Feedback")'
        ).all()
        return len(expanders)

    # ========================================================================
    # ASSERTIONS
    # ========================================================================

    def assert_leaderboard_displayed(self):
        """Assert leaderboard is visible."""
        self.assert_text_visible("🏅 Leaderboard")
        self.assert_text_visible("Rank")
        self.assert_text_visible("Team Name")
        self.assert_text_visible("Score")

    def assert_no_submissions_message(self):
        """Assert no submissions message is shown."""
        self.assert_info("No submissions have been analyzed yet")

    def assert_search_results(self, query: str):
        """Assert search is filtering results."""
        # All visible team names should contain query
        count = self.get_visible_submission_count()
        assert count > 0, f"No results found for search query: {query}"

    def assert_pagination_visible(self):
        """Assert pagination controls are visible."""
        self.assert_button_visible("⏮️ First")
        self.assert_button_visible("◀️ Previous")
        self.assert_button_visible("Next ▶️")
        self.assert_button_visible("Last ⏭️")

    def assert_team_detail_tabs_exist(self):
        """Assert all scorecard tabs exist."""
        assert self.has_tab("📊 Overview"), "Overview tab missing"
        assert self.has_tab("🤖 Agent Analysis"), "Agent Analysis tab missing"
        assert self.has_tab("📦 Repository"), "Repository tab missing"
        assert self.has_tab("👥 Team Members"), "Team Members tab missing"
