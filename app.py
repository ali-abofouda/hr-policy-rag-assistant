"""app.py — Streamlit chat UI for the HR Policy RAG Assistant.

Run with:  streamlit run app.py
"""

import uuid
import time

import streamlit as st

from hr_assistant.logging_config import configure_logging
from hr_assistant.pipeline import (
    INPUT_BLOCKED_MESSAGE,
    OUTPUT_BLOCKED_MESSAGE,
    ask,
    build_hr_assistant,
)
from hr_assistant.tracing import check_langsmith_tracing
from hr_assistant import config

# ── Bootstrap (once per server start) ────────────────────────────────────────
configure_logging()
check_langsmith_tracing()

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
    allowed_emails = [e.lower() for e in config.ALLOWED_EMPLOYEE_EMAILS]

    if allowed_emails and user_email not in allowed_emails:
        st.error(f"Access Denied: Account '{user_email}' is not authorized to access this HR Assistant.")
        st.caption("Please contact your IT/HR administrator to request system access.")
        if hasattr(st, "logout") and st.button("Log out"):
            st.logout()
            st.rerun()
        st.stop()
        return False

    return True


# Enforce authentication gate before rendering application components
verify_access_control()

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

    input_guardrail = getattr(config, "GUARDRAIL_PROVIDER", "local")
    output_guardrail = getattr(config, "GUARDRAIL_OUTPUT_PROVIDER", "local")
    cache_threshold = getattr(config, "SEMANTIC_CACHE_THRESHOLD", 0.80)

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
            f"- **Model:** `{config.LLM_MODEL_NAME}`\n"
            f"- **Vector DB:** Qdrant Cloud\n"
            f"- **Embeddings:** FastEmbed (ONNX)\n"
            f"- **Re-ranker:** Cross-Encoder\n"
            f"- **Tracing:** LangSmith"
        )

    st.divider()
    st.caption("Try one of these:")

    quick_questions = [
        "How many paid annual leave days do I get?",
        "What is the notice period during probation?",
        "Can I work from home every day?",
        "How many weeks of maternity leave am I entitled to?",
        "What expenses can I claim reimbursement for?",
    ]

    selected_quick = None
    for q in quick_questions:
        if st.button(q, key=f"q_{q}", use_container_width=True):
            selected_quick = q

# ── Main area ────────────────────────────────────────────────────────────────
st.title("HR Policy Assistant")
st.caption(
    "Ask anything about company HR policies — leave, remote work, "
    "probation, notice periods, reimbursements, and more. "
    "Every answer cites the official source document."
)

# ── Welcome state (empty chat) ───────────────────────────────────────────────
if not st.session_state.messages:
    st.divider()
    cols = st.columns(2)
    topics = [
        ("Leave & Time Off", "Annual, sick, casual leave, carry-forward, holidays"),
        ("Remote Work", "WFH eligibility, weekly limits, equipment"),
        ("Probation & Exits", "Notice periods, final settlement, exit process"),
        ("Reimbursements", "Travel, internet, certifications, eligible claims"),
    ]
    for i, (title, desc) in enumerate(topics):
        with cols[i % 2]:
            st.markdown(f"**{title}**")
            st.caption(desc)
    st.divider()

# ── Chat history ─────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Input ────────────────────────────────────────────────────────────────────
user_prompt = st.chat_input("Ask a question about HR policy...")

if selected_quick:
    user_prompt = selected_quick

if user_prompt:
    with st.chat_message("user"):
        st.markdown(user_prompt)

    with st.chat_message("assistant"):
        with st.spinner("Searching policies..."):
            t0 = time.time()
            answer = ask(agent, cache, user_prompt, thread_id=st.session_state.thread_id)
            dt = time.time() - t0

        if answer in (INPUT_BLOCKED_MESSAGE, OUTPUT_BLOCKED_MESSAGE):
            st.warning(answer)
        else:
            st.markdown(answer)
        st.caption(f"Answered in {dt:.1f}s")

    # Only append to session transcript if the prompt was not blocked at input
    if answer != INPUT_BLOCKED_MESSAGE:
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        st.session_state.messages.append({"role": "assistant", "content": answer})
