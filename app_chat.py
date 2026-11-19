"""app_chat.py — Chainlit chat UI for the HR Policy RAG Assistant.

Run with:  chainlit run app_chat.py
"""

import uuid
import time
import chainlit as cl

from hr_assistant.logging_config import configure_logging
from hr_assistant.pipeline import ask, build_hr_assistant
from hr_assistant.tracing import check_langsmith_tracing

# ── Bootstrap ────────────────────────────────────────────────────────────────
configure_logging()
check_langsmith_tracing()
agent = build_hr_assistant()


@cl.set_starters
async def set_starters():
    """Clickable starter prompt cards shown on an empty chat, just like ChatGPT/Claude."""
    return [
        cl.Starter(
            label="🏖️ Annual Leave",
            message="How many paid annual leave days do I get?",
        ),
        cl.Starter(
            label="⏳ Probation Notice",
            message="What is the notice period during probation?",
        ),
        cl.Starter(
            label="🏠 Remote Work",
            message="Can I work from home every day?",
        ),
        cl.Starter(
            label="💰 Expense Claims",
            message="How much can I claim as internet reimbursement for working from home?",
        ),
    ]


@cl.on_chat_start
async def start():
    """Called once when a new user session begins."""
    # Store a unique thread_id per session for agent memory
    cl.user_session.set("thread_id", str(uuid.uuid4()))

    await cl.Message(
        content=(
            "Welcome! I'm your **HR Policy Assistant**.\n\n"
            "Ask me anything about company policies — "
            "annual leave, remote work, probation, notice periods, "
            "reimbursements, maternity leave, and more.\n\n"
            "Every answer is backed by official policy documents with source citations."
        ),
    ).send()


@cl.on_message
async def handle_message(message: cl.Message):
    """Called each time the user sends a message."""
    thread_id = cl.user_session.get("thread_id")

    msg = cl.Message(content="")
    await msg.send()

    async with cl.Step(name="Searching Policies & Re-ranking", type="tool") as step:
        step.input = message.content
        t0 = time.time()
        answer = await cl.make_async(ask)(agent, message.content, thread_id=thread_id)
        dt = time.time() - t0
        step.output = f"Retrieved relevant policy chunks and generated grounded response in {dt:.1f}s."

    msg.content = answer
    await msg.update()
