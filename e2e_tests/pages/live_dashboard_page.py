"""Live Dashboard page object - Analysis lifecycle management."""
from playwright.sync_api import expect
from pages.base_page import BasePage
import time
import re


class LiveDashboardPage(BasePage):
    """
    Live Dashboard page object.

    Handles the complex 7-state analysis lifecycle:
    STATE 1: No active job → Button visible
    STATE 2: Click Start → Fetch cost estimate
    STATE 3: Cost estimate shown → Confirmation dialog
    STATE 3a: Cancel → Back to STATE 1
    STATE 3b: Confirm → Analysis starts
    STATE 4: Job created → Button disappears, progress appears
    STATE 5: Job running → Progress updates
    STATE 6: Job completes → Success message, button reappears
    """

    def navigate(self):
        """Navigate to Live Dashboard page."""
        super().navigate("2_📊_Live_Dashboard")

    # ========================================================================
    # HACKATHON SELECTION
    # ========================================================================

    def select_hackathon(self, name: str):
        """Select hackathon from dropdown."""
        self.select_option("Select Hackathon", name)

    def get_selected_hackathon(self) -> str:
        """Get currently selected hackathon name."""
        selectbox = self.get_selectbox("Select Hackathon")
        return selectbox.input_value()

    # ========================================================================
    # STATS SECTION
    # ========================================================================

    def get_stat(self, label: str) -> int:
        """Get statistic value as integer."""
        value_str = self.get_metric(label)
        # Remove commas and convert to int
        return int(value_str.replace(",", ""))

    def get_total_submissions(self) -> int:
        """Get Total Submissions count."""
        return self.get_stat("Total Submissions")

    def get_verified_count(self) -> int:
        """Get Verified Submissions count."""
        return self.get_stat("Verified Submissions")

    def get_pending_count(self) -> int:
        """Get Pending Submissions count."""
        return self.get_stat("Pending Submissions")

    def get_participant_count(self) -> int:
        """Get Total Participants count."""
        return self.get_stat("Total Participants")

    def get_last_refresh_time(self) -> str:
        """Get last refresh timestamp."""
        caption = self.page.locator('text=/🕐 Last refreshed:/').inner_text()
        return caption.split("Last refreshed: ")[1].split(" (")[0]

    # ========================================================================
    # ANALYSIS LIFECYCLE - STATE DETECTION
    # ========================================================================

    def is_analysis_button_visible(self) -> bool:
        """Check if Start Analysis button is visible (STATE 1)."""
        return self.is_button_visible("🚀 Start Analysis")

    def is_cost_estimate_visible(self) -> bool:
        """Check if cost estimate confirmation dialog is visible (STATE 3)."""
        return self.is_text_visible("💰 Estimated cost:")

    def is_job_in_progress(self) -> bool:
        """Check if job progress section is visible (STATE 4-5)."""
        return self.is_text_visible("📊 Analysis job in progress:")

    def is_analysis_complete(self) -> bool:
        """Check if analysis completed successfully (STATE 6)."""
        return self.is_text_visible("✅ Analysis completed successfully!")

    def get_current_state(self) -> str:
        """
        Detect current state of analysis lifecycle.

        Returns:
            "no_job", "estimating", "confirming", "running", "completed", "failed"
        """
        if self.is_analysis_complete():
            return "completed"
        elif self.is_text_visible("❌ Analysis job failed"):
            return "failed"
        elif self.is_job_in_progress():
            return "running"
        elif self.is_cost_estimate_visible():
            return "confirming"
        elif self.is_analysis_button_visible():
            return "no_job"
        else:
            return "unknown"

    # ========================================================================
    # ANALYSIS LIFECYCLE - ACTIONS
    # ========================================================================

    def start_analysis(self):
        """Click Start Analysis button (STATE 1 → STATE 2)."""
        self.click_button("🚀 Start Analysis")
        # Wait for spinner from cost estimate fetch
        self.wait_for_spinner_gone(timeout=35000)

    def get_cost_estimate(self) -> float:
        """Get displayed cost estimate (STATE 3)."""
        cost_text = self.page.locator('text=/💰 Estimated cost: \\$([0-9.]+)/').inner_text()
        match = re.search(r'\$([0-9.]+)', cost_text)
        if match:
            return float(match.group(1))
        return 0.0

    def confirm_analysis(self):
        """Click Confirm & Start button (STATE 3b → STATE 4)."""
        self.click_button("✅ Confirm & Start")
        # Wait for spinner from analysis start
        self.wait_for_spinner_gone(timeout=35000)

    def cancel_analysis(self):
        """Click Cancel button (STATE 3a → STATE 1)."""
        self.click_button("❌ Cancel")

    def get_job_id(self) -> str:
        """Extract job ID from progress section (STATE 4-5)."""
        job_text = self.page.locator('text=/📊 Analysis job in progress: ([\\w]+)/').inner_text()
        # Extract job ID (alphanumeric string after "in progress: ")
        match = re.search(r'in progress: ([A-Za-z0-9]+)', job_text)
        if match:
            return match.group(1)
        return ""

    # ========================================================================
    # ANALYSIS PROGRESS MONITORING (STATE 5)
    # ========================================================================

    def get_progress_percent(self) -> float:
        """Get progress percentage."""
        caption = self.page.locator('text=/Progress: ([0-9.]+)%/').inner_text()
        match = re.search(r'([0-9.]+)%', caption)
        if match:
            return float(match.group(1))
        return 0.0

    def get_completed_count(self) -> int:
        """Get completed submissions count."""
        return int(self.get_metric("Completed"))

    def get_failed_count(self) -> int:
        """Get failed submissions count."""
        return int(self.get_metric("Failed"))

    def get_total_count(self) -> int:
        """Get total submissions count from progress section."""
        return int(self.get_metric("Total"))

    def get_current_cost(self) -> float:
        """Get current cost."""
        cost_str = self.get_metric("Current Cost")
        # Remove $ and convert to float
        return float(cost_str.replace("$", ""))

    def has_estimated_completion(self) -> bool:
        """Check if estimated completion time is shown."""
        return self.is_text_visible("⏱️ Estimated completion:")

    def get_estimated_completion(self) -> str:
        """Get estimated completion timestamp."""
        completion_text = self.page.locator('text=/⏱️ Estimated completion:/').inner_text()
        return completion_text.split("completion: ")[1]

    def has_error_details_expander(self) -> bool:
        """Check if error details expander is present (failures occurred)."""
        try:
            self.get_expander("View Error Details")
            return True
        except:
            return False

    # ========================================================================
    # ANALYSIS COMPLETION (STATE 6)
    # ========================================================================

    def get_final_summary(self) -> dict:
        """Get final summary after completion."""
        return {
            "completed": self.get_completed_count(),
            "failed": self.get_failed_count(),
            "total": self.get_total_count(),
            "cost": self.get_current_cost()
        }

    def wait_for_analysis_complete(self, timeout: int = 300000, poll_interval: int = 10000) -> bool:
        """
        Wait for analysis to complete.

        Args:
            timeout: Maximum wait time in milliseconds (default 5 minutes)
            poll_interval: How often to check in milliseconds (default 10s)

        Returns:
            True if completed successfully, False if timeout
        """
        start_time = time.time()
        while (time.time() - start_time) * 1000 < timeout:
            if self.is_analysis_complete():
                return True

            time.sleep(poll_interval / 1000)
            self.manual_refresh()

        return False

    # ========================================================================
    # MANUAL REFRESH
    # ========================================================================

    def manual_refresh(self):
        """Click manual refresh button."""
        self.click_button("🔄 Refresh Now")

    # ========================================================================
    # ERROR HANDLING
    # ========================================================================

    def has_budget_error(self) -> bool:
        """Check if budget exceeded error is shown."""
        error = self.get_error_message()
        return error and "budget" in error.lower()

    def has_conflict_error(self) -> bool:
        """Check if conflict error (409) is shown."""
        error = self.get_error_message()
        return error and "already running" in error.lower()

    def get_failure_count_warning(self) -> str:
        """Get warning message about failed submissions."""
        warning = self.get_warning_message()
        if warning and "failed" in warning.lower():
            return warning
        return ""

    # ========================================================================
    # ASSERTIONS
    # ========================================================================

    def assert_state_no_job(self):
        """Assert in STATE 1: No active job."""
        self.assert_button_visible("🚀 Start Analysis")
        self.assert_text_hidden("📊 Analysis job in progress:")

    def assert_state_cost_estimate(self):
        """Assert in STATE 3: Cost estimate displayed."""
        self.assert_button_hidden("🚀 Start Analysis")
        self.assert_text_visible("💰 Estimated cost:")
        self.assert_button_visible("✅ Confirm & Start")
        self.assert_button_visible("❌ Cancel")

    def assert_state_job_running(self, job_id: str = None):
        """Assert in STATE 4-5: Job running."""
        self.assert_button_hidden("🚀 Start Analysis")
        self.assert_text_visible("📊 Analysis job in progress:")

        if job_id:
            self.assert_text_visible(job_id)

    def assert_state_completed(self):
        """Assert in STATE 6: Analysis completed."""
        self.assert_success("Analysis completed successfully")
        # Button should reappear on next refresh cycle
        # (depends on cache TTL)

    def assert_progress_valid(self):
        """Assert progress metrics are valid."""
        progress = self.get_progress_percent()
        assert 0 <= progress <= 100, f"Progress should be 0-100, got {progress}"

        completed = self.get_completed_count()
        failed = self.get_failed_count()
        total = self.get_total_count()

        assert completed + failed <= total, \
            f"Completed ({completed}) + Failed ({failed}) > Total ({total})"

        cost = self.get_current_cost()
        assert cost >= 0, f"Cost should be non-negative, got {cost}"

    def assert_button_hidden_job_running(self, job_id: str):
        """Assert Start Analysis button hidden when job running."""
        self.assert_button_hidden("🚀 Start Analysis")
        expect(self.page.locator(f'text="📊 Analysis job in progress: {job_id}"')).to_be_visible()

    def assert_cost_estimate_displayed(self):
        """Assert cost estimate is shown with confirmation buttons."""
        expect(self.page.locator('text=/💰 Estimated cost: \\$/')).to_be_visible()
        self.assert_button_visible("✅ Confirm & Start")
        self.assert_button_visible("❌ Cancel")
