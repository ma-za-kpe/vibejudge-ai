"""Intelligence Insights page object."""

from pages.base_page import BasePage


class IntelligencePage(BasePage):
    """Intelligence Insights page object."""

    def navigate(self):
        """Navigate to Intelligence page."""
        super().navigate("4_🧠_Intelligence")

    # ========================================================================
    # HACKATHON SELECTION
    # ========================================================================

    def select_hackathon(self, name: str):
        """Select hackathon from dropdown."""
        self.select_option("Select Hackathon", name)
        self.wait_for_streamlit_ready()

    # ========================================================================
    # INSIGHTS SECTIONS
    # ========================================================================

    def has_top_teams_section(self) -> bool:
        """Check if Top Teams section exists."""
        return self.is_text_visible("🏆 Top Teams")

    def has_score_distribution_chart(self) -> bool:
        """Check if score distribution chart exists."""
        return self.is_text_visible("📊 Score Distribution")

    def has_tech_stack_analysis(self) -> bool:
        """Check if tech stack analysis exists."""
        return self.is_text_visible("🔧 Technology Stack Analysis")

    def has_team_size_analysis(self) -> bool:
        """Check if team size analysis exists."""
        return self.is_text_visible("👥 Team Size Analysis")

    def has_ai_usage_insights(self) -> bool:
        """Check if AI usage insights exist."""
        return self.is_text_visible("🤖 AI Usage Insights")

    # ========================================================================
    # TOP TEAMS
    # ========================================================================

    def get_top_teams_count(self) -> int:
        """Get number of top teams displayed."""
        # Look for team cards in top teams section
        teams = self.page.locator('[data-testid="stMetric"]').all()
        return len(teams)

    def get_top_team_name(self, rank: int) -> str:
        """Get team name at specific rank in top teams."""
        teams = self.page.locator('[data-testid="stMetric"]').all()
        if rank <= len(teams):
            return teams[rank - 1].locator('[data-testid="stMetricLabel"]').inner_text()
        return ""

    def get_top_team_score(self, rank: int) -> float:
        """Get score for team at specific rank."""
        teams = self.page.locator('[data-testid="stMetric"]').all()
        if rank <= len(teams):
            value_text = teams[rank - 1].locator('[data-testid="stMetricValue"]').inner_text()
            return float(value_text)
        return 0.0

    # ========================================================================
    # TECHNOLOGY STACK
    # ========================================================================

    def get_most_popular_language(self) -> str:
        """Get the most popular programming language."""
        # Look for text like "Python (45%)"
        lang_element = self.page.locator("text=/^[A-Za-z+#]+\\s+\\(\\d+%\\)$/").first
        if lang_element.count() > 0:
            text = lang_element.inner_text()
            return text.split("(")[0].strip()
        return ""

    def get_language_percentage(self, language: str) -> float:
        """Get percentage for specific language."""
        import re

        lang_element = self.page.locator(f"text=/{language}\\s+\\((\\d+)%\\)/").first
        if lang_element.count() > 0:
            text = lang_element.inner_text()
            match = re.search(r"\((\d+)%\)", text)
            if match:
                return float(match.group(1))
        return 0.0

    # ========================================================================
    # TEAM SIZE ANALYSIS
    # ========================================================================

    def get_average_team_size(self) -> float:
        """Get average team size metric."""
        # Look for metric with label "Average Team Size"
        value = self.get_metric("Average Team Size")
        return float(value)

    def get_largest_team_size(self) -> int:
        """Get largest team size."""
        value = self.get_metric("Largest Team")
        return int(value)

    def get_smallest_team_size(self) -> int:
        """Get smallest team size."""
        value = self.get_metric("Smallest Team")
        return int(value)

    # ========================================================================
    # AI USAGE INSIGHTS
    # ========================================================================

    def get_ai_usage_percentage(self) -> float:
        """Get percentage of submissions flagged as AI-assisted."""
        value = self.get_metric("AI-Assisted Submissions")
        # Remove % sign and convert
        return float(value.replace("%", ""))

    def get_ai_policy_mode(self) -> str:
        """Get the hackathon's AI policy mode."""
        # Look for text like "Policy: AI Assisted"
        policy_element = self.page.locator("text=/Policy:\\s+.+/").first
        if policy_element.count() > 0:
            text = policy_element.inner_text()
            return text.split("Policy:")[1].strip()
        return ""

    # ========================================================================
    # DOWNLOAD ACTIONS
    # ========================================================================

    def has_export_button(self) -> bool:
        """Check if export/download button exists."""
        return self.is_button_visible("📥 Export Insights")

    def click_export(self):
        """Click export insights button."""
        self.click_button("📥 Export Insights")
        self.wait_for_streamlit_ready()

    # ========================================================================
    # FILTERS
    # ========================================================================

    def filter_by_score_range(self, min_score: float, max_score: float):
        """Apply score range filter."""
        min_input = self.page.get_by_label("Minimum Score")
        min_input.fill(str(min_score))

        max_input = self.page.get_by_label("Maximum Score")
        max_input.fill(str(max_score))

        self.wait_for_streamlit_ready()

    def filter_by_recommendation(self, recommendation: str):
        """Filter by recommendation tier."""
        self.select_option("Recommendation Filter", recommendation)
        self.wait_for_streamlit_ready()

    # ========================================================================
    # EMPTY STATE
    # ========================================================================

    def assert_no_data_message(self):
        """Assert that no data message is shown."""
        self.assert_text_visible("No submissions analyzed yet")

    def assert_insufficient_data_message(self):
        """Assert that insufficient data message is shown."""
        self.assert_text_visible("Not enough data for insights")
