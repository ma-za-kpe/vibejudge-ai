"""Quick script to inspect Streamlit selectors."""

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("http://localhost:8501")

    # Wait for Streamlit to load
    page.wait_for_selector('[data-testid="stAppViewContainer"]', timeout=30000)
    page.wait_for_load_state("networkidle")

    print("=== Inspecting Streamlit Selectors ===\n")

    # Check for text inputs
    print("1. Text inputs:")
    inputs = page.locator('input[type="text"], input[type="password"]').all()
    for i, inp in enumerate(inputs[:5]):
        try:
            aria_label = inp.get_attribute("aria-label")
            placeholder = inp.get_attribute("placeholder")
            print(f"   Input {i}: aria-label='{aria_label}', placeholder='{placeholder}'")
        except:
            pass

    # Check for buttons
    print("\n2. Buttons:")
    buttons = page.locator("button").all()
    for i, btn in enumerate(buttons[:10]):
        try:
            text = btn.inner_text()
            if text.strip():
                print(f"   Button {i}: '{text.strip()}'")
        except:
            pass

    # Check for tabs
    print("\n3. Tabs:")
    tabs = page.locator('[role="tab"]').all()
    for i, tab in enumerate(tabs):
        try:
            text = tab.inner_text()
            print(f"   Tab {i}: '{text.strip()}'")
        except:
            pass

    print("\n✅ Inspection complete. Press Ctrl+C to close.")
    input()

    browser.close()
