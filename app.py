"""app.py — Interactive Web UI for the HR Policy RAG Assistant.

Run with:
    streamlit run app.py
"""

import uuid
import streamlit as st

from hr_assistant.logging_config import configure_logging
from hr_assistant.pipeline import ask, build_hr_assistant
from hr_assistant.tracing import check_langsmith_tracing
from hr_assistant import config

# 1. إعداد الـ Logging والـ Tracing مرة واحدة عند إقلاع السيرفر
configure_logging()
check_langsmith_tracing()

# 2. إعدادات الصفحة وهوية الموقع
st.set_page_config(
    page_title="HR Policy Assistant",
    page_icon="💼",
    layout="centered",
    initial_sidebar_state="expanded",
)

# 3. بناء وتهيئة الـ Agent مرة واحدة في الرام (Caching)
@st.cache_resource(show_spinner="Connecting to HR Knowledge Base & Vector Store...")
def get_agent():
    return build_hr_assistant()

agent = get_agent()

# 4. إدارة حالة الجلسة والذاكرة (Session State)
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

# 5. بناء الشريط الجانبي (Sidebar)
with st.sidebar:
    st.title("💼 HR Assistant")
    st.caption("AI-powered HR Policy Companion")
    st.markdown("---")

    # زر بدء محادثة جديدة
    if st.button("🔄 New Conversation", use_container_width=True, type="primary"):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()

    st.markdown("### ⚙️ System Status")
    st.markdown(
        f"""
        - **LLM**: `{config.LLM_MODEL_NAME}`
        - **Vector DB**: `Qdrant Cloud`
        - **Embeddings**: `FastEmbed (Local ONNX)`
        - **Observability**: `LangSmith Active`
        """
    )
    
    st.markdown("---")
    st.markdown("### 💡 Quick Questions")
    quick_questions = [
        "How many paid annual leave days do I get?",
        "What is the notice period during probation?",
        "Can I work from home every day?",
        "How many weeks of maternity leave do I have?",
    ]
    
    selected_quick = None
    for q in quick_questions:
        if st.button(q, key=f"quick_{q}", use_container_width=True):
            selected_quick = q

# 6. الهيدر الترحيبي للشاشة الرئيسية
st.title("🏢 Enterprise HR Policy Assistant")
st.write(
    "Welcome! I am your AI assistant trained on official company HR policies. "
    "Ask me about annual leaves, remote work rules, probation, reimbursements, or notice periods."
)

# عرض شاشة ترحيبية إرشادية إذا كانت المحادثة خالية
if not st.session_state.messages:
    with st.container():
        st.info(
            "👋 **Tip:** You can ask questions in plain English, or click on any of the **Quick Questions** in the sidebar to test me instantly."
        )

# 7. عرض رسائل المحادثة السابقة
for message in st.session_state.messages:
    avatar = "🧑‍💻" if message["role"] == "user" else "🤖"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

# 8. استلام السؤال (سواء من الـ Input Box أو من الـ Quick Questions)
user_prompt = st.chat_input("Type your HR policy question here...")

if selected_quick:
    user_prompt = selected_quick

if user_prompt:
    # عرض سؤال المستخدم وحفظه
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(user_prompt)
    st.session_state.messages.append({"role": "user", "content": user_prompt})

    # استدعاء الـ Agent وتوليد الإجابة مع سبينر تحميل جذاب
    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Searching HR policies & evaluating guidelines..."):
            answer = ask(agent, user_prompt, thread_id=st.session_state.thread_id)
        st.markdown(answer)

    # حفظ إجابة المساعد في سياق الجلسة
    st.session_state.messages.append({"role": "assistant", "content": answer})