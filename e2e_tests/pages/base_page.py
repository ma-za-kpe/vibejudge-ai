"""Base page object with Streamlit-specific utilities."""
from playwright.sync_api import Page, expect, Locator
from typing import Optional
import time
import sys
import os

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from playwright_config import BASE_URL, NAVIGATION_TIMEOUT, SPINNER_TIMEOUT


class BasePage:
    """Base page object with common Streamlit utilities."""

    def __init__(self, page: Page):
        self.page = page
        self.base_url = BASE_URL

    # ========================================================================
    # NAVIGATION
    # ========================================================================

    def navigate(self, path: str = ""):
        """Navigate to page and wait for Streamlit to be ready."""
        url = f"{self.base_url}/{path}" if path else self.base_url
        self.page.goto(url, timeout=NAVIGATION_TIMEOUT)
        self.wait_for_streamlit_ready()

    def wait_for_streamlit_ready(self, timeout: int = NAVIGATION_TIMEOUT):
        """Wait for Streamlit app to be fully loaded and interactive."""
        # Wait for main container
        self.page.wait_for_selector(
            '[data-testid="stAppViewContainer"]',
            timeout=timeout,
            state="visible"
        )

        # Wait for script runner to finish
        self.page.wait_for_load_state("networkidle", timeout=timeout)

        # Wait for any initial spinners to disappear
        self.wait_for_spinner_gone(timeout=5000)

    def wait_for_spinner_gone(self, timeout: int = SPINNER_TIMEOUT):
        """Wait for loading spinner to disappear."""
        try:
            spinner = self.page.locator('[data-testid="stSpinner"]')
            spinner.wait_for(state="hidden", timeout=timeout)
        except Exception:
            pass  # No spinner present or already gone

    def reload(self):
        """Reload page and wait for ready."""
        self.page.reload(timeout=NAVIGATION_TIMEOUT)
        self.wait_for_streamlit_ready()

    # ========================================================================
    # STREAMLIT-SPECIFIC SELECTORS
    # ========================================================================

    def get_button(self, text: str) -> Locator:
        """Find button by text (exact or partial match)."""
        # Try exact match first
        button = self.page.get_by_role("button", name=text, exact=True)
        if button.count() > 0:
            return button.first
        # Fallback to partial match
        return self.page.get_by_role("button", name=text).first

    def get_text_input(self, label: str) -> Locator:
        """Find text input by label."""
        return self.page.get_by_label(label, exact=False).first

    def get_selectbox(self, label: str) -> Locator:
        """Find selectbox by label."""
        return self.page.get_by_label(label, exact=False).first

    def get_checkbox(self, label: str) -> Locator:
        """Find checkbox by label."""
        return self.page.get_by_role("checkbox", name=label).first

    def get_metric(self, label: str) -> str:
        """Get metric value by label."""
        metric_container = self.page.locator(f'[data-testid="stMetric"]:has-text("{label}")')
        value_locator = metric_container.locator('[data-testid="stMetricValue"]')
        return value_locator.inner_text()

    def get_sidebar(self) -> Locator:
        """Get sidebar container."""
        return self.page.locator('[data-testid="stSidebar"]')

    def get_tab(self, name: str) -> Locator:
        """Get tab by name."""
        return self.page.get_by_role("tab", name=name)

    def get_expander(self, title: str) -> Locator:
        """Get expander by title."""
        return self.page.locator(f'[data-testid="stExpander"]:has-text("{title}")')

    # ========================================================================
    # MESSAGE GETTERS
    # ========================================================================

    def get_error_message(self) -> Optional[str]:
        """Get error message text if present."""
        try:
            alert = self.page.locator('[data-testid="stAlert"]').first
            if alert.is_visible(timeout=2000):
                return alert.inner_text()
        except:
            pass
        return None

    def get_success_message(self) -> Optional[str]:
        """Get success message text if present."""
        try:
            success = self.page.locator('[data-testid="stSuccess"]').first
            if success.is_visible(timeout=2000):
                return success.inner_text()
        except:
            pass
        return None

    def get_warning_message(self) -> Optional[str]:
        """Get warning message text if present."""
        try:
            warning = self.page.locator('[data-testid="stWarning"]').first
            if warning.is_visible(timeout=2000):
                return warning.inner_text()
        except:
            pass
        return None

    def get_info_message(self) -> Optional[str]:
        """Get info message text if present."""
        try:
            info = self.page.locator('[data-testid="stInfo"]').first
            if info.is_visible(timeout=2000):
                return info.inner_text()
        except:
            pass
        return None

    # ========================================================================
    # INTERACTIONS
    # ========================================================================

    def click_button(self, text: str, wait_for_rerun: bool = True):
        """Click button and optionally wait for Streamlit rerun."""
        button = self.get_button(text)
        button.click()

        if wait_for_rerun:
            self.wait_for_streamlit_ready()

    def fill_input(self, label: str, value: str):
        """Fill text input by label."""
        input_field = self.get_text_input(label)
        input_field.clear()
        input_field.fill(value)

    def select_option(self, label: str, value: str):
        """Select option from selectbox."""
        selectbox = self.get_selectbox(label)
        selectbox.click()

        # Wait for dropdown to appear
        time.sleep(0.5)

        # Click the option
        option = self.page.get_by_text(value, exact=True)
        option.click()

        # Wait for rerun
        self.wait_for_streamlit_ready()

    def check_checkbox(self, label: str, checked: bool = True):
        """Check or uncheck checkbox."""
        checkbox = self.get_checkbox(label)

        if checked:
            checkbox.check()
        else:
            checkbox.uncheck()

    def click_tab(self, name: str):
        """Click tab to switch to it."""
        tab = self.get_tab(name)
        tab.click()
        time.sleep(0.3)  # Wait for tab content to render

    def expand_expander(self, title: str):
        """Expand an expander section."""
        expander = self.get_expander(title)
        expander.click()
        time.sleep(0.3)

    def submit_form(self, button_text: str = "Submit"):
        """Submit form and wait for response."""
        self.click_button(button_text)

    # ========================================================================
    # ASSERTIONS
    # ========================================================================

    def assert_on_page(self, title: str):
        """Assert we're on the correct page by checking h1."""
        heading = self.page.get_by_role("heading", level=1)
        expect(heading).to_contain_text(title, timeout=10000)

    def assert_button_visible(self, text: str):
        """Assert button is visible."""
        button = self.get_button(text)
        expect(button).to_be_visible(timeout=5000)

    def assert_button_hidden(self, text: str):
        """Assert button is not visible."""
        try:
            button = self.get_button(text)
            expect(button).not_to_be_visible(timeout=5000)
        except:
            pass  # Button doesn't exist at all, which is also acceptable

    def assert_button_disabled(self, text: str):
        """Assert button is disabled."""
        button = self.get_button(text)
        expect(button).to_be_disabled()

    def assert_button_enabled(self, text: str):
        """Assert button is enabled."""
        button = self.get_button(text)
        expect(button).to_be_enabled()

    def assert_error(self, message: str):
        """Assert error message contains text."""
        error = self.page.locator('[data-testid="stAlert"]')
        expect(error).to_contain_text(message, timeout=10000)

    def assert_success(self, message: str):
        """Assert success message contains text."""
        success = self.page.locator('[data-testid="stSuccess"]')
        expect(success).to_contain_text(message, timeout=10000)

    def assert_warning(self, message: str):
        """Assert warning message contains text."""
        warning = self.page.locator('[data-testid="stWarning"]')
        expect(warning).to_contain_text(message, timeout=10000)

    def assert_info(self, message: str):
        """Assert info message contains text."""
        info = self.page.locator('[data-testid="stInfo"]')
        expect(info).to_contain_text(message, timeout=10000)

    def assert_text_visible(self, text: str):
        """Assert text is visible somewhere on page."""
        locator = self.page.get_by_text(text)
        expect(locator).to_be_visible(timeout=5000)

    def assert_text_hidden(self, text: str):
        """Assert text is not visible on page."""
        locator = self.page.get_by_text(text)
        expect(locator).not_to_be_visible(timeout=2000)

    # ========================================================================
    # SCREENSHOTS & DEBUGGING
    # ========================================================================

    def take_screenshot(self, name: str):
        """Take screenshot for visual regression or debugging."""
        screenshot_dir = "e2e_tests/visual_regression"
        os.makedirs(screenshot_dir, exist_ok=True)
        path = f"{screenshot_dir}/{name}.png"
        self.page.screenshot(path=path, full_page=True)
        return path

    def debug_print_page_content(self):
        """Print page content for debugging (use sparingly)."""
        print("\n" + "="*80)
        print("PAGE CONTENT DEBUG")
        print("="*80)
        print(f"URL: {self.page.url}")
        print(f"Title: {self.page.title()}")
        print("\nButtons:")
        for button in self.page.get_by_role("button").all():
            try:
                print(f"  - {button.inner_text()}")
            except:
                pass
        print("\nErrors/Warnings:")
        if error := self.get_error_message():
            print(f"  ERROR: {error}")
        if warning := self.get_warning_message():
            print(f"  WARNING: {warning}")
        print("="*80 + "\n")

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def wait_for_text(self, text: str, timeout: int = 10000):
        """Wait for specific text to appear on page."""
        locator = self.page.get_by_text(text)
        locator.wait_for(state="visible", timeout=timeout)

    def wait_for_url(self, url_pattern: str, timeout: int = 10000):
        """Wait for URL to match pattern."""
        self.page.wait_for_url(url_pattern, timeout=timeout)

    def is_button_visible(self, text: str) -> bool:
        """Check if button is visible without assertion."""
        try:
            button = self.get_button(text)
            return button.is_visible(timeout=2000)
        except:
            return False

    def is_text_visible(self, text: str) -> bool:
        """Check if text is visible without assertion."""
        try:
            locator = self.page.get_by_text(text)
            return locator.is_visible(timeout=2000)
        except:
            return False
