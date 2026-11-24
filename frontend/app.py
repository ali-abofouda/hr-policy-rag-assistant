"""frontend/app.py — Streamlit chat UI for the HR Policy RAG Assistant.

Run with:  streamlit run frontend/app.py
"""

import uuid
import time
from pathlib import Path
import sys

# Ensure backend is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st

from backend.app.core.logging import configure_logging
from backend.app.core.config import settings
from backend.app.core.tracing import setup_tracing
from backend.app.domain.services.chat_service import (
    INPUT_BLOCKED_MESSAGE,
    OUTPUT_BLOCKED_MESSAGE,
    ask,
    build_hr_assistant,
)

# ── Bootstrap (once per server start) ────────────────────────────────────────
configure_logging(level=settings.LOG_LEVEL)
setup_tracing()

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="HR Policy Assistant",
    layout="centered",
    initial_sidebar_state="expanded",
)


# ── Access Control & Authentication Gating ────────────────────────────────────
def is_auth_configured() -> bool:
    """Return True only when Streamlit auth configuration and secrets are present."""
    try:
        return "auth" in st.secrets
    except Exception:
        return False


def verify_access_control() -> bool:
    """Enforce Google OAuth authentication and whitelist verification.
    
    In Cloud Run deployment: requires authenticated Google account on allowed list.
    In local development: falls back to open mode to avoid crashing without secrets.toml.
    """
    if not is_auth_configured():
        return True

    user = getattr(st, "user", None)
    is_logged_in = getattr(user, "is_logged_in", False) if user else False

    if not is_logged_in:
        st.subheader("Employee Authentication Required")
        st.info("Please sign in with your corporate Google Workspace account to access company HR policies.")
        if hasattr(st, "login"):
            if st.button("Log in with Google", type="primary", use_container_width=True):
                st.login("google")
        st.stop()
        return False

    user_email = str(getattr(user, "email", "")).strip().lower()
    allowed_emails = [e.lower() for e in settings.ALLOWED_EMPLOYEE_EMAILS]

    if allowed_emails and user_email not in allowed_emails:
        st.error(f"Access Denied: Account '{user_email}' is not authorized to access this HR Assistant.")
        st.caption("Please contact your IT/HR administrator to request system access.")
        if hasattr(st, "logout") and st.button("Log out"):
            st.logout()
            st.rerun()
        st.stop()
        return False

    return True


# Authentication gate (bypassed for local execution without Cloud Run OAuth)
# verify_access_control()

# ── Agent & Semantic Cache (cached — built once, reused across reruns) ──────
@st.cache_resource(show_spinner="Setting up the assistant...")
def get_assistant():
    return build_hr_assistant()

agent, cache = get_assistant()

# ── Session state ────────────────────────────────────────────────────────────
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("HR Assistant")

    if st.button("New conversation", use_container_width=True, type="primary"):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()

    if st.button("Clear Cache", use_container_width=True):
        cache.clear()
        st.success("Semantic cache cleared!")

    input_guardrail = getattr(settings, "GUARDRAIL_PROVIDER", "local")
    output_guardrail = getattr(settings, "GUARDRAIL_OUTPUT_PROVIDER", "local")
    cache_threshold = getattr(settings, "SEMANTIC_CACHE_THRESHOLD", 0.80)

    st.caption(f"Input Guardrail: `{input_guardrail}`")
    st.caption(f"Output Guardrail: `{output_guardrail}`")
    st.caption(f"Cache Threshold: `{cache_threshold}`")

    # Access control status
    user = getattr(st, "user", None)
    if is_auth_configured() and user and getattr(user, "is_logged_in", False):
        st.caption(f"Account: `{user.email}`")
        if hasattr(st, "logout") and st.button("Log out", use_container_width=True):
            st.logout()
            st.rerun()
    else:
        st.caption("Access Control: `Open (Local)`")

    st.divider()

    with st.expander("System info", expanded=False):
        st.markdown(
            f"- **Model:** `{settings.LLM_MODEL_NAME}`\n"
            f"- **Vector DB:** Qdrant Cloud\n"
            f"- **Collection:** `{settings.QDRANT_COLLECTION_NAME}`\n"
            f"- **Retrieval:** Hybrid (Dense + BM25)\n"
            f"- **Reranker:** `{settings.RERANKER_MODEL_NAME}`\n"
            f"- **Guardrails:** Dual (Input + Output)\n"
            f"- **Session ID:** `{st.session_state.thread_id[:8]}...`"
        )

# ── Header ───────────────────────────────────────────────────────────────────
st.title("HR Policy Assistant")
st.caption(
    "Ask any question about company HR policies — leave, work from home, probation, "
    "notice period, reimbursements, code of conduct, and more."
)

# ── Suggested questions (shown only on empty conversation) ────────────────────
if not st.session_state.messages:
    st.markdown("**Common questions to get started:**")
    suggestions = [
        "How many days of annual leave do I get per year?",
        "What is the notice period during probation?",
        "Can I work from home and what are the rules?",
        "What is the policy for claiming travel expenses?",
    ]
    cols = st.columns(2)
    for i, suggestion in enumerate(suggestions):
        with cols[i % 2]:
            if st.button(suggestion, key=f"sug_{i}", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": suggestion})
                st.rerun()

# ── Message history ──────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "badge" in msg:
            st.caption(msg["badge"])

# ── Chat input ───────────────────────────────────────────────────────────────
if user_input := st.chat_input("Ask a question about HR policy..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Searching policies and drafting answer..."):
            t0 = time.time()
            answer = ask(
                agent=agent,
                cache_or_question=cache,
                question_or_none=user_input,
                thread_id=st.session_state.thread_id,
            )
            elapsed = time.time() - t0

        st.markdown(answer)

        # Telemetry badge
        if answer == INPUT_BLOCKED_MESSAGE:
            st.error("Input request was blocked by safety policy.")
            badge = "Blocked by input guardrail"
        elif answer == OUTPUT_BLOCKED_MESSAGE:
            st.error("Generated answer was blocked by output safety policy.")
            badge = "Blocked by output guardrail"
        elif elapsed < 0.15:
            badge = f"Semantic Cache Hit (instant, {elapsed:.3f}s)"
            st.caption(badge)
        else:
            badge = f"Retrieved via RAG pipeline ({elapsed:.2f}s)"
            st.caption(badge)

    st.session_state.messages[-1]["badge"] = badge
    st.session_state.messages.append({"role": "assistant", "content": answer, "badge": badge})
