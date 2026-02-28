"""Playwright E2E test configuration."""
import os

# Environment URLs
BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:8501")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Browser configuration
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
SLOW_MO = int(os.getenv("SLOW_MO", "0"))  # ms delay between actions (for debugging)

BROWSER_CONFIG = {
    "headless": HEADLESS,
    "slow_mo": SLOW_MO,
    "args": [
        "--disable-blink-features=AutomationControlled",  # Avoid bot detection
        "--no-sandbox",  # For CI environments
    ],
}

# Viewport sizes
DESKTOP_VIEWPORT = {"width": 1920, "height": 1080}
TABLET_VIEWPORT = {"width": 768, "height": 1024}
MOBILE_VIEWPORT = {"width": 375, "height": 667}

# Timeouts (milliseconds)
DEFAULT_TIMEOUT = 30000  # 30s
NAVIGATION_TIMEOUT = 60000  # 60s (Streamlit cold start)
EXPECT_TIMEOUT = 10000  # 10s
SPINNER_TIMEOUT = 35000  # 35s (Lambda cold starts)

# Test credentials
TEST_API_KEY = os.getenv("TEST_API_KEY", "vj_test_e2e_key_12345")
TEST_EMAIL = "e2e_test@vibejudge.ai"
TEST_PASSWORD = "TestPassword123!E2E"
TEST_ORG = "E2E Test Organization"

# Test data paths
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "test_data")
