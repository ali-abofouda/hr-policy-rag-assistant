"""app_chat.py — Enterprise Chainlit chat interface for the HR Policy RAG Assistant.

Features:
- Nested step visualizer (cl.Step) for Guardrail Screening, Scoped Retrieval & Reranking.
- Interactive Source Inspector (cl.Text display='side') displaying official policy text on click.
- User feedback collector (@cl.on_feedback) logging human ratings to results/user_feedback.json.
- Session persistence via thread_id and rate-limit compliant agent orchestration.

Run with:
    chainlit run app_chat.py
"""

import json
import logging
import os
import re
import time
import uuid
from typing import List, Optional

import chainlit as cl

from hr_assistant import config
from hr_assistant.guardrails import check_input, check_output
from hr_assistant.logging_config import configure_logging
from hr_assistant.pipeline import (
    INPUT_BLOCKED_MESSAGE,
    OUTPUT_BLOCKED_MESSAGE,
    ask_plain,
    build_hr_assistant,
)
from hr_assistant.tracing import check_langsmith_tracing

# ── Bootstrap ────────────────────────────────────────────────────────────────
configure_logging()
check_langsmith_tracing()
logger = logging.getLogger(__name__)

# Build the compiled agent once at startup
agent = build_hr_assistant()

# Path for raw policies to display in the side drawer
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POLICIES_DIR = os.path.join(BASE_DIR, "data", "policies")
FEEDBACK_FILE = os.path.join(BASE_DIR, "results", "user_feedback.json")


def _find_source_documents(answer: str) -> List[cl.Text]:
    """Extract source document names from response and attach them as side drawer elements."""
    elements = []
    # Match patterns like [Source: leave_policy.txt] or [Source: leave_policy.md]
    matches = set(re.findall(r"\[Source:\s*([^\]]+)\]", answer))

    for source_name in matches:
        source_name = source_name.strip()
        # Clean up any extra tags or scores
        clean_name = source_name.split()[0]
        # Check if the document exists in data/policies
        candidates = [
            clean_name,
            clean_name.replace(".md", ".txt"),
            clean_name.replace(".json", ".txt"),
            f"{clean_name}.txt",
        ]

        found_path = None
        for cand in candidates:
            cand_path = os.path.join(POLICIES_DIR, cand)
            if os.path.isfile(cand_path):
                found_path = cand_path
                clean_name = cand
                break

        if found_path:
            try:
                with open(found_path, "r", encoding="utf-8") as f:
                    content = f.read()
                elements.append(
                    cl.Text(
                        name=f"Document: {clean_name}",
                        content=content,
                        display="side",
                    )
                )
            except Exception as exc:
                logger.debug("Could not read policy document %s: %s", found_path, exc)

    return elements


@cl.set_starters
async def set_starters():
    """Starter question cards displayed in the empty chat canvas."""
    return [
        cl.Starter(
            label="Annual Leave Entitlement",
            message="How many paid annual leave days do I get, and how does carry-forward work?",
            description="Leave quotas, sick days, and carry-forward limits.",
        ),
        cl.Starter(
            label="Probation & Notice Period",
            message="What is the standard notice period during my probation period?",
            description="Probation duration and resignation notice requirements.",
        ),
        cl.Starter(
            label="Work From Home Eligibility",
            message="Can I work from home permanently or are there weekly limits?",
            description="Remote work policy and equipment allowances.",
        ),
        cl.Starter(
            label="Internet & Travel Claims",
            message="What are the maximum reimbursement limits for internet bills and business travel?",
            description="Eligible expense claims and receipt deadlines.",
        ),
    ]


@cl.on_chat_start
async def start():
    """Initialize user session with fresh thread_id and welcome greeting."""
    thread_id = str(uuid.uuid4())
    cl.user_session.set("thread_id", thread_id)
    cl.user_session.set("last_query", "")
    cl.user_session.set("last_answer", "")

    provider_name = config.GUARDRAIL_PROVIDER.upper()
    fallback_name = config.FALLBACK_MODEL_NAME

    await cl.Message(
        content=(
            "Welcome to the **HR Policy Assistant**.\n\n"
            "I provide verified, citation-backed answers regarding company policies:\n"
            "- Leave entitlements and carry-forward rules.\n"
            "- Remote work guidelines and equipment reimbursements.\n"
            "- Probation terms, notice periods, and exit processes.\n\n"
            f"*Security Stack: {provider_name} Safety Guardrail | Scoped Qdrant Hybrid Search | Router Fallback: `{fallback_name}`*"
        )
    ).send()


@cl.on_message
async def handle_message(message: cl.Message):
    """Execute secured RAG pipeline with visible steps and citation elements."""
    thread_id = cl.user_session.get("thread_id")
    user_query = message.content

    # ── Step 1: Input Safety Screening ───────────────────────────────────────
    async with cl.Step(name="Input Safety Screening", type="run") as guard_step:
        guard_step.input = user_query
        t0 = time.time()
        input_ok, input_reason = await cl.make_async(check_input)(user_query)
        dt_guard = time.time() - t0

        if not input_ok:
            guard_step.output = f"BLOCKED in {dt_guard:.2f}s: {input_reason}"
            await cl.Message(content=INPUT_BLOCKED_MESSAGE).send()
            return

        guard_step.output = f"PASSED in {dt_guard:.2f}s: {input_reason}"

    # ── Step 2: Agent Execution (Scoped Retrieval + Reranking + LLM) ─────────
    async with cl.Step(name="Policy Retrieval & Grounded Generation", type="tool") as agent_step:
        agent_step.input = user_query
        t0 = time.time()
        answer = await cl.make_async(ask_plain)(agent, user_query, thread_id=thread_id)
        dt_agent = time.time() - t0
        agent_step.output = f"Generated grounded answer with citations in {dt_agent:.2f}s"

    # ── Step 3: Output Safety Screening ──────────────────────────────────────
    async with cl.Step(name="Output Safety Verification", type="run") as out_step:
        out_step.input = answer[:100] + "..."
        t0 = time.time()
        output_ok, output_reason = await cl.make_async(check_output)(answer)
        dt_out = time.time() - t0

        if not output_ok:
            out_step.output = f"BLOCKED in {dt_out:.2f}s: {output_reason}"
            await cl.Message(content=OUTPUT_BLOCKED_MESSAGE).send()
            return

        out_step.output = f"PASSED in {dt_out:.2f}s: {output_reason}"

    # ── Step 4: Parse Citations and Attach Side Drawer Elements ──────────────
    side_elements = _find_source_documents(answer)

    # Store for feedback collection
    cl.user_session.set("last_query", user_query)
    cl.user_session.set("last_answer", answer)

    # ── Send Final Response ──────────────────────────────────────────────────
    response_msg = cl.Message(
        content=answer,
        elements=side_elements if side_elements else None,
    )
    await response_msg.send()


@cl.on_feedback
async def on_feedback(feedback):
    """Collect human feedback ratings to build future evaluation datasets."""
    last_query = cl.user_session.get("last_query")
    last_answer = cl.user_session.get("last_answer")

    record = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "for_id": feedback.for_id,
        "value": feedback.value,  # 1 for positive, 0 for negative
        "comment": feedback.comment,
        "query": last_query,
        "answer": last_answer,
    }

    try:
        os.makedirs(os.path.dirname(FEEDBACK_FILE), exist_ok=True)
        existing = []
        if os.path.exists(FEEDBACK_FILE):
            with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
                try:
                    existing = json.load(f)
                except Exception:
                    existing = []

        existing.append(record)
        with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)

        logger.info("Saved user feedback (rating=%s) for message %s", feedback.value, feedback.for_id)
    except Exception as exc:
        logger.warning("Failed to record user feedback: %s", exc)
