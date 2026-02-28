"""Login/authentication page object."""
from playwright.sync_api import expect
from pages.base_page import BasePage


class LoginPage(BasePage):
    """Login and authentication page object."""

    def navigate(self):
        """Navigate to home/login page."""
        super().navigate("")

    # ========================================================================
    # LOGIN ACTIONS
    # ========================================================================

    def login_with_api_key(self, api_key: str):
        """Login using API key tab."""
        # Select API Key tab
        self.click_tab("🔑 API Key Login")

        # Fill API key
        self.fill_input("API Key", api_key)

        # Submit
        self.click_button("Login with API Key")

        # Assert authenticated
        self.assert_authenticated()

    def login_with_email(self, email: str, password: str) -> bool:
        """
        Login using email/password tab.

        Returns:
            True if login successful, False otherwise
        """
        # Select Email tab
        self.click_tab("📧 Email/Password Login")

        # Fill credentials
        self.fill_input("Email Address", email)
        self.fill_input("Password", password)

        # Submit
        self.click_button("Login with Email")

        # Check for errors
        error = self.get_error_message()
        if error:
            return False

        # Check for success
        self.assert_authenticated()
        return True

    def logout(self):
        """Logout from sidebar."""
        logout_button = self.get_sidebar().get_by_role("button", name="🚪 Logout")
        logout_button.click()
        self.wait_for_streamlit_ready()

        # Assert back on login page
        self.assert_not_authenticated()

    # ========================================================================
    # ADVANCED SETTINGS
    # ========================================================================

    def set_api_base_url(self, url: str, tab: str = "api_key"):
        """Set custom API base URL in advanced settings."""
        if tab == "api_key":
            # Already on API Key tab
            pass
        else:
            self.click_tab("📧 Email/Password Login")

        # Expand advanced settings
        self.expand_expander("Advanced Settings")

        # Set URL
        self.fill_input("API Base URL", url)

    # ========================================================================
    # ASSERTIONS
    # ========================================================================

    def assert_authenticated(self):
        """Assert user is authenticated (check sidebar)."""
        sidebar = self.get_sidebar()
        expect(sidebar).to_contain_text("✅ Authenticated", timeout=10000)

    def assert_not_authenticated(self):
        """Assert user is not authenticated."""
        sidebar = self.get_sidebar()
        expect(sidebar).to_contain_text("⚠️ Not authenticated", timeout=10000)

    def assert_login_error(self, message: str):
        """Assert login failed with specific error."""
        self.assert_error(message)

    def assert_on_login_page(self):
        """Assert we're on the login page."""
        self.assert_on_page("VibeJudge AI")
        expect(self.page.get_by_text("Organizer Dashboard")).to_be_visible()

    # ========================================================================
    # HELPERS
    # ========================================================================

    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        sidebar = self.get_sidebar()
        try:
            return "✅ Authenticated" in sidebar.inner_text()
        except:
            return False
