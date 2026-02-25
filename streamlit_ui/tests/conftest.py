"""Pytest configuration for streamlit_ui tests."""

import sys
from pathlib import Path

# Add the streamlit_ui directory to the Python path
# This allows tests to import from components, pages, etc.
streamlit_ui_dir = Path(__file__).parent.parent
sys.path.insert(0, str(streamlit_ui_dir))
