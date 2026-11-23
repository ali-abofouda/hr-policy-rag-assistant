# Web UI & Automated UI Testing: Streamlit & AppTest Integration

## 1. Web User Interface (`app.py`)

The human-facing web interface is built using **Streamlit**, providing a modern, conversational chat experience designed for enterprise employees.

### Key UI Features:
- **Conversational Chat Canvas**: Renders multi-turn dialogue with distinct user and assistant avatars.
- **Latency & Sourcing Telemetry**: Displays exact turn execution time (e.g. *"Answered in 6.7s"* or *"Answered in 1.0s"* for cache hits) alongside explicit document source citations.
- **Quick-Start Prompts**: Pre-configured buttons for common questions (annual leave, probation periods, remote work, reimbursements).
- **Administrative Controls**: Sidebar controls to clear the semantic cache and start a new conversation thread.
- **Authentication Badge**: Shows logged-in employee email identity when Google OAuth is configured, or indicates local access.

---

## 2. Automated UI Integration Testing (`tests/test_app.py`)

Traditional UI testing with Selenium or Playwright requires running a live headless browser, introducing flakiness and high resource consumption.

The system tests the Streamlit interface using **Streamlit `AppTest`**, executing the UI in a headless Python harness directly within unit testing:

```python
import unittest
from streamlit.testing.v1 import AppTest

class TestStreamlitApp(unittest.TestCase):
    """Validate Streamlit UI components, initial state, and rendering."""

    def test_app_renders_without_exceptions(self):
        """Verify app.py compiles, initializes session state, and renders cleanly."""
        at = AppTest.from_file("app.py", default_timeout=60)
        at.run()

        # Ensure no runtime exceptions occurred during startup
        self.assertFalse(at.exception)

        # Check sidebar header and title
        sidebar_headers = [h.value for h in at.sidebar.header]
        self.assertTrue(any("HR Assistant" in h for h in sidebar_headers))

        # Check buttons in sidebar
        button_labels = [b.label for b in at.sidebar.button]
        self.assertIn("New conversation", button_labels)
        self.assertIn("Clear Cache", button_labels)

        # Check chat input widget is present
        self.assertEqual(len(at.chat_input), 1)
```

### Benefits:
- Tests compile errors, session state initialization, and component rendering in $< 2$ seconds.
- Integrated directly into the CI/CD test runner (`python -m unittest discover`).
