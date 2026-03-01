"""Submissions Management page object (for organizers)."""

from pages.base_page import BasePage


class SubmissionsPage(BasePage):
    """Submissions management page for organizers."""

    def navigate(self):
        """Navigate to Submissions page."""
        super().navigate("Submissions")

    # ========================================================================
    # HACKATHON SELECTION
    # ========================================================================

    def select_hackathon(self, name: str):
        """Select hackathon."""
        self.select_option("Select Hackathon", name)
        self.wait_for_streamlit_ready()

    # ========================================================================
    # SUBMISSIONS LIST
    # ========================================================================

    def get_submission_count(self) -> int:
        """Get number of submissions displayed."""
        rows = self.page.locator('[data-testid="stDataFrame"] tbody tr').all()
        return len(rows)

    def get_total_submissions_stat(self) -> int:
        """Get total submissions from stats."""
        value = self.get_metric("Total Submissions")
        return int(value)

    def get_verified_submissions_stat(self) -> int:
        """Get verified submissions count."""
        value = self.get_metric("Verified")
        return int(value)

    def get_pending_submissions_stat(self) -> int:
        """Get pending submissions count."""
        value = self.get_metric("Pending")
        return int(value)

    # ========================================================================
    # SUBMISSION DETAILS
    # ========================================================================

    def get_submission_status(self, row: int) -> str:
        """Get status for submission at row."""
        rows = self.page.locator('[data-testid="stDataFrame"] tbody tr').all()
        if row < len(rows):
            # Look for status column (usually has badge)
            status_cell = rows[row].locator("td").nth(3)  # Adjust index based on table structure
            return status_cell.inner_text().strip().lower()
        return ""

    def get_team_name_at_row(self, row: int) -> str:
        """Get team name at specific row."""
        rows = self.page.locator('[data-testid="stDataFrame"] tbody tr').all()
        if row < len(rows):
            team_cell = rows[row].locator("td").first
            return team_cell.inner_text()
        return ""

    # ========================================================================
    # ACTIONS
    # ========================================================================

    def verify_submission(self, row: int):
        """Verify submission at row."""
        rows = self.page.locator('[data-testid="stDataFrame"] tbody tr').all()
        if row < len(rows):
            # Look for verify button in row
            verify_btn = rows[row].get_by_role("button", name="✅ Verify")
            verify_btn.click()
            self.wait_for_streamlit_ready()

    def reject_submission(self, row: int, reason: str = ""):
        """Reject submission at row."""
        rows = self.page.locator('[data-testid="stDataFrame"] tbody tr').all()
        if row < len(rows):
            reject_btn = rows[row].get_by_role("button", name="❌ Reject")
            reject_btn.click()

            if reason:
                # Fill rejection reason
                reason_input = self.page.get_by_label("Rejection Reason")
                reason_input.fill(reason)

            # Confirm
            self.click_button("Confirm Rejection")
            self.wait_for_streamlit_ready()

    def view_submission_details(self, row: int):
        """View details for submission."""
        rows = self.page.locator('[data-testid="stDataFrame"] tbody tr').all()
        if row < len(rows):
            details_btn = rows[row].get_by_role("button", name="👁️ View")
            details_btn.click()
            self.wait_for_streamlit_ready()

    def delete_submission(self, row: int):
        """Delete submission (admin action)."""
        rows = self.page.locator('[data-testid="stDataFrame"] tbody tr').all()
        if row < len(rows):
            delete_btn = rows[row].get_by_role("button", name="🗑️")
            delete_btn.click()

            # Confirm deletion
            confirm_btn = self.page.get_by_role("button", name="Confirm Delete")
            confirm_btn.click()
            self.wait_for_streamlit_ready()

    # ========================================================================
    # FILTERING
    # ========================================================================

    def filter_by_status(self, status: str):
        """Filter by submission status."""
        self.select_option("Filter by Status", status)
        self.wait_for_streamlit_ready()

    def filter_by_verification(self, verified: bool):
        """Filter by verification status."""
        option = "Verified Only" if verified else "Pending Only"
        self.select_option("Filter", option)
        self.wait_for_streamlit_ready()

    def search_by_team_name(self, query: str):
        """Search submissions by team name."""
        search_input = self.page.get_by_placeholder("Search by team name...")
        search_input.fill(query)
        self.wait_for_streamlit_ready()

    # ========================================================================
    # SORTING
    # ========================================================================

    def sort_by(self, field: str):
        """Sort submissions."""
        sort_map = {"created_at": "Submission Date", "team_name": "Team Name", "status": "Status"}
        option = sort_map.get(field, field)
        self.select_option("Sort by", option)
        self.wait_for_streamlit_ready()

    # ========================================================================
    # BULK ACTIONS
    # ========================================================================

    def select_submission(self, row: int):
        """Select submission checkbox."""
        checkboxes = self.page.locator('[data-testid="stCheckbox"]').all()
        if row < len(checkboxes):
            checkboxes[row].check()

    def select_all_submissions(self):
        """Select all submissions."""
        select_all = self.page.get_by_label("Select All")
        select_all.check()

    def bulk_verify(self):
        """Verify all selected submissions."""
        self.click_button("✅ Verify Selected")
        self.wait_for_streamlit_ready()

    def bulk_delete(self):
        """Delete all selected submissions."""
        self.click_button("🗑️ Delete Selected")

        # Confirm
        confirm_btn = self.page.get_by_role("button", name="Confirm Bulk Delete")
        confirm_btn.click()
        self.wait_for_streamlit_ready()

    def get_selected_count(self) -> int:
        """Get number of selected submissions."""
        # Look for text like "3 submissions selected"
        import re

        text = self.page.locator("text=/\\d+ submission.*selected/").first.inner_text()
        match = re.search(r"(\d+)", text)
        if match:
            return int(match.group(1))
        return 0

    # ========================================================================
    # PAGINATION
    # ========================================================================

    def has_pagination(self) -> bool:
        """Check if pagination exists."""
        return self.is_button_visible("Next ▶️")

    def next_page(self):
        """Go to next page."""
        self.click_button("Next ▶️")
        self.wait_for_streamlit_ready()

    def previous_page(self):
        """Go to previous page."""
        self.click_button("◀️ Previous")
        self.wait_for_streamlit_ready()

    # ========================================================================
    # EXPORT
    # ========================================================================

    def export_submissions(self, format: str = "csv"):
        """Export submissions."""
        if format == "csv":
            self.click_button("📥 Export CSV")
        elif format == "excel":
            self.click_button("📥 Export Excel")
        else:
            self.click_button("📥 Export")

        self.wait_for_streamlit_ready()

    # ========================================================================
    # EMPTY STATE
    # ========================================================================

    def assert_no_submissions_message(self):
        """Assert no submissions message."""
        self.assert_text_visible("No submissions yet")

    # ========================================================================
    # VALIDATION
    # ========================================================================

    def assert_verification_success(self):
        """Assert verification successful."""
        self.assert_success("Submission verified")

    def assert_rejection_success(self):
        """Assert rejection successful."""
        self.assert_success("Submission rejected")

    def assert_deletion_success(self):
        """Assert deletion successful."""
        self.assert_success("Submission deleted")
