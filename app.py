"""app.py — Streamlit chat UI for the HR Policy RAG Assistant.

Run with:  streamlit run app.py
"""

import uuid
import time

import streamlit as st

from hr_assistant.logging_config import configure_logging
from hr_assistant.pipeline import ask, build_hr_assistant
from hr_assistant.tracing import check_langsmith_tracing
from hr_assistant import config

# ── Bootstrap (once per server start) ────────────────────────────────────────
configure_logging()
check_langsmith_tracing()

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="HR Policy Assistant",
    page_icon="💼",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ── Agent (cached — built once, reused across reruns) ────────────────────────
@st.cache_resource(show_spinner="Setting up the assistant...")
def get_agent():
    return build_hr_assistant()

agent = get_agent()

# ── Session state ────────────────────────────────────────────────────────────
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("💼 HR Assistant")

    if st.button("New conversation", icon="🔄", use_container_width=True, type="primary"):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()

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
        ("🏖️", "Leave & Time Off", "Annual, sick, casual leave, carry-forward, holidays"),
        ("🏠", "Remote Work", "WFH eligibility, weekly limits, equipment"),
        ("📋", "Probation & Exits", "Notice periods, final settlement, exit process"),
        ("💰", "Reimbursements", "Travel, internet, certifications, eligible claims"),
    ]
    for i, (icon, title, desc) in enumerate(topics):
        with cols[i % 2]:
            st.markdown(f"**{icon} {title}**")
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
    st.session_state.messages.append({"role": "user", "content": user_prompt})

    with st.chat_message("assistant"):
        with st.spinner("Searching policies..."):
            t0 = time.time()
            answer = ask(agent, user_prompt, thread_id=st.session_state.thread_id)
            dt = time.time() - t0
        st.markdown(answer)
        st.caption(f"Answered in {dt:.1f}s")

    st.session_state.messages.append({"role": "assistant", "content": answer})
