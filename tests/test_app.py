"""Automated integration tests for app.py using Streamlit AppTest."""

import os
import unittest
from streamlit.testing.v1 import AppTest

APP_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app.py"))


class TestStreamlitApp(unittest.TestCase):
    """Validate Streamlit UI components, initial state, and rendering."""

    def test_app_renders_without_exceptions(self):
        """Verify app.py compiles, initializes session state, and renders cleanly."""
        at = AppTest.from_file(APP_FILE, default_timeout=30)
        at.run()

        # Ensure no runtime exceptions occurred during startup
        self.assertFalse(at.exception, f"AppTest raised unexpected exception: {at.exception}")

        # Check sidebar header and title
        sidebar_headers = [h.value for h in at.sidebar.header]
        self.assertTrue(any("HR Assistant" in h for h in sidebar_headers))

        # Check buttons in sidebar
        button_labels = [b.label for b in at.sidebar.button]
        self.assertIn("New conversation", button_labels)
        self.assertIn("Clear Cache", button_labels)

        # Check chat input widget is present
        self.assertEqual(len(at.chat_input), 1)
        self.assertEqual(at.chat_input[0].placeholder, "Ask a question about HR policy...")

    def test_clear_cache_button_action(self):
        """Verify clicking Clear Cache triggers clear action without crashing."""
        at = AppTest.from_file(APP_FILE, default_timeout=30)
        at.run()

        # Find and click the Clear Cache button
        clear_cache_buttons = [b for b in at.sidebar.button if "Clear Cache" in b.label]
        self.assertEqual(len(clear_cache_buttons), 1)

        clear_cache_buttons[0].click().run()
        self.assertFalse(at.exception)

        # Check success message appears
        success_messages = [s.value for s in at.sidebar.success]
        self.assertIn("Semantic cache cleared!", success_messages)


if __name__ == "__main__":
    unittest.main()
