"""
Streamlit web UI — Customer Chat tab + RM Dashboard tab.
Phase 8 target.
"""
import streamlit as st
from agent.core_agent import LoanCopilotAgent
from monitoring.langfuse_logger import flush

st.set_page_config(page_title="Loan Origination Copilot", page_icon="🏦", layout="wide")

# ── Session state ─────────────────────────────────────────────────────────────
if "agent" not in st.session_state:
    st.session_state.agent = LoanCopilotAgent(phase=5)
if "messages" not in st.session_state:
    st.session_state.messages = []

agent: LoanCopilotAgent = st.session_state.agent


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_chat, tab_rm = st.tabs(["💬 Customer Chat", "📊 RM Dashboard"])

# ── Customer Chat ─────────────────────────────────────────────────────────────
with tab_chat:
    st.title("Loan Origination Copilot")
    st.caption("Ask me about Home, Personal, MSME, or Car loans. All assessments are indicative.")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if prompt := st.chat_input("Type your query here…"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                # TODO (Phase 8): wrap with safety gate before calling agent
                response = agent.chat(prompt)
                st.write(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

    col1, col2 = st.columns([8, 1])
    with col2:
        if st.button("Start Over"):
            agent.reset()
            st.session_state.messages = []
            st.rerun()

# ── RM Dashboard ──────────────────────────────────────────────────────────────
with tab_rm:
    st.title("Relationship Manager Dashboard")
    st.info("TODO (Phase 8): Display session summaries, escalation queue, and Langfuse link.")
    # TODO: pull escalation records from logs/interactions.log and display
