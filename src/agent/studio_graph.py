"""Entry point for LangGraph Studio (langgraph dev).

Exposes the agent's compiled graph so Studio can visualize and step
through it in the browser.
"""

from hr_assistant.logging_config import configure_logging
from hr_assistant.pipeline import build_hr_assistant

configure_logging()

# نمرر checkpointer=False لأن استوديو يدير الذاكرة وتخزين الجلسات بنفسه
agent = build_hr_assistant(checkpointer=False)

# يشير ملف langgraph.json إلى هذا المتغير الصريح
graph = agent