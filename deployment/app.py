"""
Streamlit web UI — Customer Chat + RM Dashboard.
Phase 8: safety gate · PII-masked interaction logging · latency tracking.
"""
import sys, os, html as _html
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import time
from collections import Counter
from datetime import datetime
import streamlit as st
from agent.core_agent import LoanCopilotAgent
from monitoring.langfuse_logger import flush, score_session
from monitoring.interaction_logger import log_interaction, read_recent
from policy_rlhf.feedback_collector import record_feedback
from deployment.config import DATA_DIR, LANGFUSE_HOST, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY

st.set_page_config(
    page_title="Loan Origination Copilot",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ── Langfuse live conversation fetch ─────────────────────────────────────────

def _extract_trace_text(value) -> str:
    """Pull the CURRENT turn's text out of a Langfuse trace input/output field."""
    if not value:
        return ""
    if isinstance(value, str):
        return value[:800]
    if isinstance(value, dict):
        for key in ("input", "output", "text", "content"):
            v = value.get(key)
            if isinstance(v, str) and v:
                return v[:800]
        # LangGraph stores messages as a list under "messages" — take the last one
        msgs = value.get("messages")
        if isinstance(msgs, list) and msgs:
            last = msgs[-1]
            if isinstance(last, dict):
                return str(last.get("content", ""))[:800]
    return str(value)[:800]


def _extract_full_messages(value) -> list[dict]:
    """Extract the complete turn-by-turn conversation from a LangChain/LangGraph
    trace input (which carries the full sliding-window message history).

    Skips the system prompt message.  Returns a list of
    {"role": "user"|"assistant", "content": str} dicts.
    """
    if not isinstance(value, dict):
        return []
    msgs = value.get("messages", [])
    if not isinstance(msgs, list):
        return []
    turns = []
    for msg in msgs:
        if not isinstance(msg, dict):
            continue
        msg_type = (msg.get("type") or msg.get("role") or "").lower()
        content = msg.get("content", "")
        if not msg_type or not content:
            continue
        if "system" in msg_type:
            continue
        if "human" in msg_type or "user" in msg_type:
            turns.append({"role": "user", "content": str(content)[:1200]})
        elif "ai" in msg_type or "assistant" in msg_type:
            text = str(content).strip()
            if text:
                turns.append({"role": "assistant", "content": text[:1200]})
    return turns


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_langfuse_conversation(hex_id: str) -> list[dict]:
    """Fetch conversation turns from Langfuse for a session (cached 5 min).

    Uses the Langfuse REST API (v4 compatible) — client.fetch_traces() was
    removed in Langfuse v4.  Tries two strategies:
      1. Query all traces tagged with sessionId=hex_id (new sessions after
         the session_id fix in langfuse_logger.py).
      2. Fall back to the single trace whose id=hex_id (legacy records where
         session_id was the same as the trace_id).
    Returns [] when Langfuse is not configured or no traces are found.
    """
    try:
        import base64, urllib.request as _urlreq, json as _json
        from deployment.config import (
            LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST,
        )
        if not LANGFUSE_PUBLIC_KEY:
            return []

        creds = base64.b64encode(
            f"{LANGFUSE_PUBLIC_KEY}:{LANGFUSE_SECRET_KEY}".encode()
        ).decode()
        base = (LANGFUSE_HOST or "https://cloud.langfuse.com").rstrip("/")
        headers = {"Authorization": f"Basic {creds}"}

        def _get(path: str) -> dict:
            req = _urlreq.Request(f"{base}{path}", headers=headers)
            with _urlreq.urlopen(req, timeout=10) as r:
                return _json.loads(r.read())

        # Strategy 1 — session-tagged traces (future sessions)
        data = _get(f"/api/public/traces?sessionId={hex_id}&limit=100")
        raw_traces = data.get("data", [])

        # Strategy 2 — single trace by ID (legacy RM dashboard records)
        if not raw_traces:
            try:
                single = _get(f"/api/public/traces/{hex_id}")
                if single.get("id"):
                    raw_traces = [single]
            except Exception:
                pass

        if not raw_traces:
            return []

        sorted_traces = sorted(raw_traces, key=lambda t: t.get("timestamp", ""))

        # When the sessionId query returns multiple traces (one per agent turn),
        # extract the current user message + agent output from each trace in order.
        if len(sorted_traces) > 1:
            turns = []
            for trace in sorted_traces:
                user_text  = _extract_trace_text(trace.get("input"))
                agent_text = _extract_trace_text(trace.get("output"))
                if user_text:
                    turns.append({"role": "user",      "content": user_text})
                if agent_text:
                    turns.append({"role": "assistant", "content": agent_text})
            return turns

        # Only 1 trace returned (session_id mismatch for older records — legacy fallback).
        # The trace input carries the full LangChain memory window as a messages array.
        # Reconstruct the whole conversation from that array, then append the output.
        latest = sorted_traces[0]
        turns = _extract_full_messages(latest.get("input"))
        agent_text = _extract_trace_text(latest.get("output"))
        # Append final agent response only if it's not already the last item
        if agent_text and (not turns or turns[-1].get("content") != agent_text):
            turns.append({"role": "assistant", "content": agent_text})
        return turns
    except Exception:
        return []

@st.cache_data(ttl=3600)
def _get_langfuse_project_id() -> str:
    """Return the Langfuse project ID by inspecting any trace's htmlPath (cached 1 hr).

    Langfuse v4 uses /project/{project_id}/traces/{id} — the old /traces/{id}
    URL returns 404.  The htmlPath field on every trace object contains the
    correct path, so we read one trace and extract the project ID segment.
    """
    if not LANGFUSE_PUBLIC_KEY:
        return ""
    try:
        import base64, urllib.request as _urlreq, json as _json
        creds = base64.b64encode(
            f"{LANGFUSE_PUBLIC_KEY}:{LANGFUSE_SECRET_KEY}".encode()
        ).decode()
        base = (LANGFUSE_HOST or "https://cloud.langfuse.com").rstrip("/")
        req = _urlreq.Request(
            f"{base}/api/public/traces?limit=1",
            headers={"Authorization": f"Basic {creds}"},
        )
        with _urlreq.urlopen(req, timeout=10) as r:
            data = _json.loads(r.read())
        for t in data.get("data", []):
            hp = t.get("htmlPath", "")
            # htmlPath = /project/{project_id}/traces/{trace_id}
            parts = hp.split("/")
            if len(parts) > 2 and parts[1] == "project":
                return parts[2]
    except Exception:
        pass
    return ""


# ── Escalation history injection ──────────────────────────────────────────────

def _read_escalation_count() -> int:
    """Return the current number of persisted escalation records."""
    esc_path = DATA_DIR / "rlhf" / "escalations.json"
    try:
        if esc_path.exists():
            return len(json.loads(esc_path.read_text()))
    except Exception:
        pass
    return 0


def _inject_history_if_new(count_before: int, session_id: str) -> None:
    """If a new escalation was saved this turn, patch it with the full conversation
    history from session state and the correct session_id for Langfuse linking.

    This runs *after* the assistant response is appended to st.session_state.messages
    so the stored history includes every turn including the escalation message itself.
    """
    esc_path = DATA_DIR / "rlhf" / "escalations.json"
    try:
        if not esc_path.exists():
            return
        records = json.loads(esc_path.read_text())
        if len(records) <= count_before:
            return  # no new escalation this turn
        last = records[-1]
        if last.get("conversation_history"):
            return  # already populated (guard against double-write)
        history = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.get("messages", [])
            if m.get("content") and m.get("role") in ("user", "assistant")
        ]
        if history:
            records[-1]["conversation_history"] = history
        # LLM cannot access agent.session_id at runtime — fix it here
        if not records[-1].get("session_id"):
            records[-1]["session_id"] = session_id
        # Ensure every new record has a status field (default: pending)
        if not records[-1].get("status"):
            records[-1]["status"] = "pending"
        esc_path.write_text(json.dumps(records, indent=2, ensure_ascii=False))
    except Exception:
        pass


def _update_escalation_status(escalation_id: str, status: str, comment: str = "") -> None:
    """Update an escalation record's workflow status and write a resolution comment."""
    esc_path = DATA_DIR / "rlhf" / "escalations.json"
    try:
        if not esc_path.exists():
            return
        records = json.loads(esc_path.read_text())
        for rec in records:
            if rec.get("escalation_id") == escalation_id:
                rec["status"] = status
                rec["resolution_comment"] = comment.strip() or None
                rec["resolved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                break
        esc_path.write_text(json.dumps(records, indent=2, ensure_ascii=False))
    except Exception:
        pass


# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Base typography */
html, body, [class*="css"] {
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
}

/* ── Bank header gradient ── */
.bank-header {
    background: linear-gradient(135deg, #0a2342 0%, #1565c0 100%);
    padding: 1.25rem 1.8rem;
    border-radius: 12px;
    color: white;
    margin-bottom: 1.4rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 4px 20px rgba(21, 101, 192, 0.28);
}
.bank-header h1 {
    color: white; margin: 0;
    font-size: 1.5rem; font-weight: 700; letter-spacing: -0.3px;
}
.bank-header .tagline {
    color: #a8c8f0; margin: 0.25rem 0 0; font-size: 0.82rem;
}
.bank-header .pill {
    background: rgba(255,255,255,0.13);
    border: 1px solid rgba(255,255,255,0.28);
    border-radius: 20px; padding: 0.25rem 0.85rem;
    font-size: 0.74rem; color: #dbeafe; white-space: nowrap;
    flex-shrink: 0;
}

/* ── Welcome hero ── */
.welcome-hero {
    text-align: center; padding: 2.2rem 1rem 1.4rem;
}
.welcome-hero h2 {
    color: #1a2e5a; font-size: 1.45rem;
    font-weight: 700; margin-bottom: 0.35rem;
}
.welcome-hero p { color: #6b7280; font-size: 0.91rem; margin: 0; }

/* ── User chat bubble (right-aligned) ── */
.user-bubble-row {
    display: flex; justify-content: flex-end;
    margin: 0.55rem 0 0.25rem;
}
.user-bubble {
    background: #1565c0; color: white;
    padding: 0.75rem 1.1rem;
    border-radius: 18px 4px 18px 18px;
    max-width: 74%;
    font-size: 0.91rem; line-height: 1.55;
    box-shadow: 0 2px 8px rgba(21, 101, 192, 0.22);
    word-wrap: break-word;
}

/* ── RM Dashboard header ── */
.rm-header {
    background: linear-gradient(135deg, #0a2342 0%, #1565c0 100%);
    padding: 1.1rem 1.6rem;
    border-radius: 10px; color: white; margin-bottom: 1.2rem;
}
.rm-header h2 { color: white; margin: 0; font-size: 1.3rem; font-weight: 700; }
.rm-header p  { color: #a8c8f0; margin: 0.2rem 0 0; font-size: 0.82rem; }

/* ── Section headings ── */
.rm-section {
    font-size: 1.02rem; font-weight: 700; color: #0a2342;
    border-bottom: 2px solid #1565c0;
    padding-bottom: 0.4rem; margin: 1.8rem 0 1rem;
}

/* ── Status badges ── */
.badge {
    display: inline-block; border-radius: 12px;
    padding: 0.15rem 0.65rem; font-size: 0.72rem; font-weight: 600;
}
.badge-new      { background: #fef3c7; color: #92400e; border: 1px solid #fcd34d; }
.badge-pending  { background: #dbeafe; color: #1e40af; border: 1px solid #93c5fd; }
.badge-older    { background: #f3f4f6; color: #374151; border: 1px solid #d1d5db; }
.badge-resolved { background: #d1fae5; color: #065f46; border: 1px solid #6ee7b7; }

/* ── Resolution info block ── */
.resolution-block {
    background: #ecfdf5; border-left: 4px solid #10b981;
    border-radius: 0 8px 8px 0;
    padding: 0.65rem 1rem; margin: 0.6rem 0; font-size: 0.88rem;
    color: #064e3b;
}

/* ── Escalation reason block ── */
.esc-reason {
    background: #fffbeb; border-left: 4px solid #f59e0b;
    border-radius: 0 8px 8px 0;
    padding: 0.65rem 1rem; margin: 0.6rem 0; font-size: 0.9rem;
    color: #451a03;
}

/* ── Conversation turns in RM view ── */
.turn-user {
    background: #eff6ff; border-left: 3px solid #3b82f6;
    border-radius: 0 8px 8px 0;
    padding: 0.55rem 0.9rem; margin: 0.3rem 0; font-size: 0.87rem;
}
.turn-bot {
    background: #f0fdf4; border-left: 3px solid #22c55e;
    border-radius: 0 8px 8px 0;
    padding: 0.55rem 0.9rem; margin: 0.3rem 0; font-size: 0.87rem;
}
.turn-label {
    font-weight: 600; font-size: 0.74rem;
    color: #6b7280; margin-bottom: 0.2rem;
    text-transform: uppercase; letter-spacing: 0.4px;
}

/* ── KPI metric cards ── */
div[data-testid="metric-container"] {
    background: #f8faff;
    border: 1px solid #e2e8f0;
    border-radius: 10px; padding: 0.85rem 1rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
</style>
""", unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────
def _make_agent() -> LoanCopilotAgent:
    from policy_rlhf.policy_updater import get_adapted_prompt
    from agent.prompts import SYSTEM_PROMPT
    adapted = get_adapted_prompt(SYSTEM_PROMPT)
    agent = LoanCopilotAgent(phase=5)
    if adapted != SYSTEM_PROMPT:
        agent._system_prompt = adapted
        agent._executor = None
    return agent


for _k, _v in [
    ("agent", None), ("messages", []), ("latencies", []),
    ("show_end_rating", False), ("_processing", False), ("_pending_input", None),
]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

if st.session_state.agent is None:
    st.session_state.agent = _make_agent()

agent: LoanCopilotAgent = st.session_state.agent


# ── Safety gate ───────────────────────────────────────────────────────────────
_OUT_OF_SCOPE_REPLY = (
    "I can only assist with Home, Personal, MSME, and New Car loan queries. "
    "Our branches are open Monday to Saturday, 9:30 AM – 4:00 PM. "
    "Please ask for a Relationship Manager who can help with other queries."
)


_LOAN_CONVERSATION_SIGNALS = (
    "loan", "emi", "eligible", "cibil", "income", "interest rate",
    "home loan", "car loan", "personal loan", "msme", "tenure",
    "on-road price", "on road price", "loan amount", "how much",
    "credit score", "employment", "salaried", "self-employed",
    "relationship manager", "10-digit", "mobile number",
    "callback number", "specialist", "escalat",
)


def _run_safety_gate(text: str) -> tuple[str, bool]:
    """Return (intent_label, blocked). Fails open — never blocks on gate error."""
    from safety.guardrails import keyword_filter, classify_intent, Intent

    # Stage A: keyword blocklist always runs (catches jailbreaks / injections at any turn)
    if keyword_filter(text) == Intent.OUT_OF_SCOPE:
        return "OUT_OF_SCOPE", True

    # Stage B bypass: once the conversation is clearly about loans, skip the LLM
    # classifier for subsequent user messages.  The classifier has no history and
    # misclassifies data-provision replies ("on road price is 15 lacs") as
    # OUT_OF_SCOPE when it can't see the question that preceded them.
    recent = st.session_state.get("messages", [])[-6:]
    active_loan_convo = any(
        m.get("role") == "assistant" and
        any(kw in m.get("content", "").lower() for kw in _LOAN_CONVERSATION_SIGNALS)
        for m in recent
    )
    if active_loan_convo:
        return "IN_SCOPE", False

    # Stage B: LLM classifier — only for cold-start / first messages where context
    # is absent and we need to detect completely off-topic requests.
    try:
        intent = classify_intent(text)
        if intent == Intent.OUT_OF_SCOPE:
            return "OUT_OF_SCOPE", True
        return intent.value, False
    except Exception:
        return "IN_SCOPE", False


# ── Feedback helpers ──────────────────────────────────────────────────────────
def _post_feedback(msg_idx: int, response_text: str, rating: int,
                   comment: str = "", feedback_type: str = "per_turn") -> None:
    turn = sum(1 for m in st.session_state.messages[:msg_idx] if m["role"] == "assistant")
    record_feedback(
        session_id=agent.session_id, turn=turn,
        agent_response=response_text, rating=rating,
        comment=comment, feedback_type=feedback_type,
    )
    try:
        score_name = "session_rating" if feedback_type == "session" else "user_feedback"
        score_session(
            trace_id=agent.session_id.replace("-", "").lower(),
            score_name=score_name,
            value=(rating - 1) / 4,
            comment=f"{rating}/5 stars" + (f': "{comment}"' if comment else ""),
        )
        flush()
    except Exception:
        pass


def _render_feedback_widget(idx: int, response_text: str) -> None:
    """Per-turn thumbs — quick signal, no comment."""
    fb = st.session_state.messages[idx].get("feedback")
    if fb is not None:
        icon = "👍" if fb["rating"] >= 4 else "👎"
        st.caption(f"{icon}  Feedback recorded")
        return
    thumb_idx = st.feedback("thumbs", key=f"fb_thumb_{idx}")
    if thumb_idx is None:
        return
    rating_val = 4 if thumb_idx == 1 else 2
    st.session_state.messages[idx]["feedback"] = {"rating": rating_val, "comment": ""}
    _post_feedback(idx, response_text, rating_val, feedback_type="per_turn")
    st.session_state.pop(f"fb_thumb_{idx}", None)
    st.rerun()


def _render_session_rating_panel() -> None:
    """Inline end-of-session panel shown when user clicks Start Over."""
    st.markdown("""
    <div style="background:#f0f7ff;border:1px solid #bdd7f5;border-radius:10px;
        padding:1.2rem 1.5rem;margin-bottom:1rem">
      <p style="font-weight:700;color:#1a3560;margin:0 0 0.25rem;font-size:1rem">
        ⭐  Rate this conversation before clearing
      </p>
      <p style="color:#4b6080;font-size:0.87rem;margin:0">
        Your feedback helps improve the experience for future customers.
      </p>
    </div>
    """, unsafe_allow_html=True)

    star_idx = st.feedback("stars", key="end_session_stars")
    rating_val = (star_idx + 1) if star_idx is not None else None
    if rating_val:
        st.caption(f"Selected: {'⭐' * rating_val}")

    comment = st.text_area(
        "Any comments? (optional)",
        placeholder="Overall impression, what worked well, what could improve…",
        key="end_session_comment",
        height=80,
    )
    col_submit, col_skip = st.columns([1, 1])
    with col_submit:
        label = "Submit & Clear" if rating_val else "Clear (no rating)"
        if st.button(label, key="end_submit", type="primary", use_container_width=True):
            if rating_val:
                last_response = next(
                    (m["content"] for m in reversed(st.session_state.messages)
                     if m["role"] == "assistant"), "[session-level rating]"
                )
                _post_feedback(
                    len(st.session_state.messages) - 1,
                    last_response, rating_val, comment or "",
                    feedback_type="session",
                )
            agent.reset()
            st.session_state.messages = []
            st.session_state.latencies = []
            st.session_state.show_end_rating = False
            for k in ["end_session_stars", "end_session_comment"]:
                st.session_state.pop(k, None)
            st.rerun()
    with col_skip:
        if st.button("Skip & Clear", key="end_skip", use_container_width=True):
            agent.reset()
            st.session_state.messages = []
            st.session_state.latencies = []
            st.session_state.show_end_rating = False
            for k in ["end_session_stars", "end_session_comment"]:
                st.session_state.pop(k, None)
            st.rerun()


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_chat, tab_rm = st.tabs(["💬  Customer Chat", "📊  RM Dashboard"])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Customer Chat
# ══════════════════════════════════════════════════════════════════════════════
with tab_chat:
    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="bank-header">
      <div>
        <h1>🏦 Loan Origination Copilot</h1>
        <p class="tagline">
          Home · Personal · MSME · New Car &nbsp;|&nbsp;
          All assessments are indicative — subject to credit appraisal
        </p>
      </div>
      <span class="pill">Powered by AI</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Session-end rating panel ───────────────────────────────────────────────
    if st.session_state.show_end_rating:
        _render_session_rating_panel()
        st.stop()

    # ── Handle product quick-start (rule-based, no LLM) ───────────────────────
    _product_start = st.session_state.pop("_product_start", None)
    if _product_start:
        user_msg, canned_reply = _product_start
        # Sync into agent LangChain memory — LLM sees the product context next turn
        agent.inject_context(user_msg, canned_reply)
        st.session_state.messages.append({"role": "user", "content": user_msg, "feedback": None})
        st.session_state.messages.append({"role": "assistant", "content": canned_reply, "feedback": None})
        st.rerun()

    # ── Welcome screen (shown only when no messages) ──────────────────────────
    if not st.session_state.messages:
        st.markdown("""
        <div class="welcome-hero">
          <h2>How can I help you today?</h2>
          <p>Ask about loan eligibility, EMI estimates, interest rates, or required documents.</p>
        </div>
        """, unsafe_allow_html=True)

        wc1, wc2, wc3, wc4 = st.columns(4)
        _quick_options = [
            ("🏠", "Home Loan",
             "Great choice! I can help you with a **Home Loan** assessment.\n\n"
             "To get started, please share the following:\n"
             "1. ₹ **Monthly income** (net take-home pay)\n"
             "2. 🎂 **Age**\n"
             "3. 🏷️ **Loan amount** you are looking for\n"
             "4. 👔 **Employment type** — Salaried / Self-employed / Business owner\n"
             "5. 📊 **Approximate CIBIL score** (if known)"),
            ("🚗", "Car Loan",
             "Happy to help with a **New Car Loan**!\n\n"
             "To calculate your EMI and check eligibility, please share:\n"
             "1. ₹ **Monthly income** (net take-home pay)\n"
             "2. 🎂 **Age**\n"
             "3. 🚘 **On-road price** of the car you have in mind\n"
             "4. 📅 **Preferred tenure** (3 / 5 / 7 years)\n"
             "5. 📊 **Approximate CIBIL score** (if known)"),
            ("💼", "MSME Loan",
             "I can help you explore an **MSME Loan**!\n\n"
             "To give you the most relevant information, please share:\n"
             "1. 🏭 **Business type** — Sole proprietor / Partnership / Pvt Ltd\n"
             "2. ₹ **Monthly business turnover** (or annual revenue)\n"
             "3. 🏷️ **Loan amount** required\n"
             "4. 🗓️ **Business vintage** (years in operation)\n"
             "5. 📋 **Purpose** — Working capital / Equipment / Expansion"),
            ("💳", "Personal Loan",
             "Sure! Let me help you with a **Personal Loan** assessment.\n\n"
             "Please share the following to get started:\n"
             "1. ₹ **Monthly income** (net take-home pay)\n"
             "2. 🎂 **Age**\n"
             "3. 🏷️ **Loan amount** needed\n"
             "4. 📅 **Preferred tenure** (up to 5 years)\n"
             "5. 📊 **Approximate CIBIL score** (if known)"),
        ]
        for col, (icon, label, greeting) in zip([wc1, wc2, wc3, wc4], _quick_options):
            with col:
                if st.button(f"{icon}  {label}", use_container_width=True,
                             key=f"qs_{label}"):
                    st.session_state["_product_start"] = (
                        f"I'd like to inquire about a {label}",
                        greeting,
                    )
                    st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

    # ── Chat history ──────────────────────────────────────────────────────────
    for idx, msg in enumerate(st.session_state.messages):
        if msg["role"] == "user":
            safe = _html.escape(msg["content"]).replace("\n", "<br>")
            st.markdown(
                f'<div class="user-bubble-row">'
                f'<div class="user-bubble">{safe}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            with st.chat_message("assistant", avatar="🏦"):
                st.write(msg["content"])
                _render_feedback_widget(idx, msg["content"])

    # ── Phase 2: LLM processing — runs AFTER user message is already visible ──
    # The chat history loop above already rendered the pending user bubble;
    # now we call the LLM and append the response, then rerun for a clean render.
    if st.session_state.get("_processing") and st.session_state.get("_pending_input"):
        text = st.session_state["_pending_input"]
        intent_label, blocked = _run_safety_gate(text)
        if blocked:
            response = _OUT_OF_SCOPE_REPLY
            latency_ms = 0
        else:
            with st.spinner("Analysing your query…"):
                t0 = time.time()
                _esc_count_before = _read_escalation_count()
                response = agent.chat(text)
                latency_ms = int((time.time() - t0) * 1000)
            st.session_state.latencies.append(latency_ms)
        log_interaction(
            session_id=agent.session_id,
            turn=agent.state.turn_count,
            user_input=text,
            agent_response=response,
            latency_ms=latency_ms,
            intent=intent_label,
            blocked=blocked,
        )
        st.session_state.messages.append({"role": "assistant", "content": response, "feedback": None})
        if not blocked:
            _inject_history_if_new(_esc_count_before, agent.session_id)
        st.session_state["_processing"] = False
        st.session_state["_pending_input"] = None
        st.rerun()

    # ── Action buttons — hidden while LLM is processing ───────────────────────
    if st.session_state.messages and not st.session_state.get("_processing"):
        _, _ab = st.columns([3, 2])
        with _ab:
            _so_col, _ec_col = st.columns(2)
            with _so_col:
                if st.button("↺  Start Over", key="start_over",
                             use_container_width=True):
                    st.session_state.show_end_rating = True
                    st.rerun()
            with _ec_col:
                if st.button("✕  End Chat", key="end_chat",
                             use_container_width=True):
                    st.session_state.show_end_rating = True
                    st.rerun()

    # ── Phase 1: Chat input — appends user message and queues LLM processing ──
    _submit = st.chat_input("Ask about loan eligibility, EMI, rates, documents…")

    if _submit and _submit.strip():
        text = _submit.strip()

        # Gracefully handle conversation-ending keywords
        if text.lower() in {"quit", "exit", "bye", "goodbye"}:
            st.session_state.messages.append({"role": "user", "content": text, "feedback": None})
            farewell = (
                "Thank you for chatting with the Loan Origination Copilot! 😊\n\n"
                "Should you wish to continue your loan journey, our branches are open "
                "**Monday to Saturday, 9:30 AM – 4:00 PM**. Please ask for a "
                "**Relationship Manager** who will be happy to assist you further.\n\n"
                "Have a wonderful day! 👋"
            )
            st.session_state.messages.append({"role": "assistant", "content": farewell, "feedback": None})
            st.session_state.show_end_rating = True
            st.rerun()

        # Append user message NOW so the next rerun renders it immediately,
        # then queue LLM processing for that same rerun (Phase 2 above).
        st.session_state.messages.append({"role": "user", "content": text, "feedback": None})
        st.session_state["_processing"] = True
        st.session_state["_pending_input"] = text
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — RM Dashboard
# ══════════════════════════════════════════════════════════════════════════════
with tab_rm:
    st.markdown("""
    <div class="rm-header">
      <h2>📊  Relationship Manager Dashboard</h2>
      <p>Escalated leads · Feedback signals · Session analytics</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Load data ──────────────────────────────────────────────────────────────
    esc_records: list[dict] = []
    esc_path = DATA_DIR / "rlhf" / "escalations.json"
    if esc_path.exists():
        try:
            esc_records = json.loads(esc_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    fb_records: list[dict] = []
    fb_path = DATA_DIR / "rlhf" / "feedback_store.json"
    if fb_path.exists():
        try:
            fb_records = json.loads(fb_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    lats = st.session_state.get("latencies", [])
    log_entries = read_recent(20)
    # P95 from persisted log (survives hot-reloads); fall back to session lats only
    _log_lats = [r["latency_ms"] for r in read_recent(500)
                 if r.get("latency_ms", 0) > 0 and not r.get("blocked")]
    _lats_for_p95 = _log_lats or lats

    from policy_rlhf.policy_updater import analyse_feedback
    fb_signal = analyse_feedback() if len(fb_records) >= 5 else {}

    # ── KPI strip ──────────────────────────────────────────────────────────────
    n_pending  = sum(1 for r in esc_records if (r.get("status") or "pending") == "pending")
    n_resolved = sum(1 for r in esc_records if (r.get("status") or "pending") == "resolved")

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Escalations (total)", len(esc_records))
    k2.metric("🔴 Pending",  n_pending)
    k3.metric("✅ Resolved", n_resolved)
    avg_stars = fb_signal.get("avg_stars")
    k4.metric("Avg rating", f"{avg_stars} ★" if avg_stars else "—")
    if _lats_for_p95:
        p95 = sorted(_lats_for_p95)[max(0, int(0.95 * len(_lats_for_p95)) - 1)]
        k5.metric("P95 latency", f"{p95} ms",
                  delta="within SLA" if p95 <= 5000 else "over 5 s SLA",
                  delta_color="normal" if p95 <= 5000 else "inverse")
    else:
        k5.metric("P95 latency", "—")

    st.divider()

    # ══════════════════════════════════════════════════════════════════════════
    # Section 1 — Escalation Queue
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown('<p class="rm-section">🔔 Escalation Queue</p>', unsafe_allow_html=True)

    _PRODUCT_ICON = {
        "home_loan": "🏠", "personal_loan": "💳",
        "msme_loan": "🏭", "car_loan": "🚗",
    }
    _LOAN_LABELS = {
        "home_loan": "Home Loan", "personal_loan": "Personal Loan",
        "msme_loan": "MSME Loan", "car_loan":      "Car Loan",
    }

    def _status_badge(rec: dict) -> str:
        """Return status badge HTML. Resolved records get a green badge."""
        if (rec.get("status") or "pending") == "resolved":
            return '<span class="badge badge-resolved">✅ RESOLVED</span>'
        ts_str = rec.get("timestamp", "")
        try:
            ts = datetime.strptime(ts_str[:19], "%Y-%m-%d %H:%M:%S")
            hours = (datetime.now() - ts).total_seconds() / 3600
            if hours < 24:
                return '<span class="badge badge-new">🟡 NEW</span>'
            if hours < 72:
                return '<span class="badge badge-pending">🔵 PENDING</span>'
        except Exception:
            pass
        return '<span class="badge badge-older">⚪ OLDER</span>'

    def _fmt_amount(amt: float) -> str:
        if not amt:
            return "—"
        if amt >= 1e7:
            return f"₹{amt/1e7:.2f} Cr"
        return f"₹{amt/1e5:.1f} L"

    def _apply_esc_filters(records: list[dict], loan_type: str,
                           date_from, date_to) -> list[dict]:
        out = []
        for r in records:
            prod_key = r.get("loan_product", "")
            if loan_type != "All" and _LOAN_LABELS.get(prod_key, "") != loan_type:
                continue
            ts_str = r.get("timestamp", "")[:10]
            try:
                from datetime import date as _date
                rec_date = datetime.strptime(ts_str, "%Y-%m-%d").date()
                if date_from and rec_date < date_from:
                    continue
                if date_to and rec_date > date_to:
                    continue
            except Exception:
                pass
            out.append(r)
        return out

    def _render_esc_card(rec: dict, card_n: int, allow_resolve: bool,
                         key_suffix: str = "") -> None:
        prod      = rec.get("loan_product", "")
        prod_icon = _PRODUCT_ICON.get(prod, "₹")
        prod_label = _LOAN_LABELS.get(prod, prod.replace("_", " ").title()) if prod else "—"
        amt_str   = _fmt_amount(rec.get("loan_amount_inr", 0))
        date_str  = rec.get("timestamp", "")[:10]
        cust      = rec.get("customer_name", "Unknown")
        esc_id    = rec.get("escalation_id", f"card{card_n}")
        badge_html = _status_badge(rec)

        with st.expander(
            f"#{card_n}  ·  {cust}  ·  {prod_icon} {prod_label}  ·  {amt_str}  ·  {date_str}",
            expanded=(card_n == 1),
        ):
            # Badge + timestamp row
            st.markdown(badge_html + "&nbsp;&nbsp;" +
                        f"<small style='color:#6b7280'>{rec.get('timestamp','')[:16]}</small>",
                        unsafe_allow_html=True)
            st.markdown("")

            # Resolution block (resolved records only)
            if (rec.get("status") or "pending") == "resolved":
                res_comment = rec.get("resolution_comment") or "No comment provided."
                res_at      = rec.get("resolved_at", "")[:16]
                st.markdown(
                    f'<div class="resolution-block">'
                    f'<strong>✅ Resolved</strong>'
                    + (f'  ·  <small>{res_at}</small>' if res_at else '')
                    + f'<br>{_html.escape(res_comment)}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                st.markdown("")

            # Contact | Loan split
            col_c, col_l = st.columns(2)
            with col_c:
                st.markdown("**📋 Contact**")
                st.markdown(f"- **Name:** {cust}")
                mobile = rec.get("callback_number") or "—"
                st.markdown(f"- **Mobile:** `{mobile}`")
                email = rec.get("customer_email") or "—"
                st.markdown(f"- **Email:** {email}")
                gender = (rec.get("gender") or "—")
                if gender not in ("—", "Not collected"):
                    st.markdown(f"- **Gender:** {gender.title()}")
                pct = rec.get("preferred_contact_time") or "Not specified"
                st.markdown(f"- **Best time:** {pct}")

            with col_l:
                st.markdown(f"**{prod_icon} Loan**")
                st.markdown(f"- **Product:** {prod_label}")
                st.markdown(f"- **Amount:** {amt_str}")
                income = rec.get("monthly_income_inr", 0) or 0
                st.markdown(f"- **Monthly income:** ₹{income:,.0f}")
                if rec.get("credit_score"):
                    st.markdown(f"- **CIBIL score:** {rec['credit_score']}")
                if rec.get("age"):
                    st.markdown(f"- **Age:** {rec['age']} yrs")
                if rec.get("employment_type"):
                    emp = rec["employment_type"].replace("_", " ").title()
                    st.markdown(f"- **Employment:** {emp}")
                if rec.get("tenure_months"):
                    yrs, mo = divmod(int(rec["tenure_months"]), 12)
                    tenure_str = f"{yrs} yr" + (f" {mo} mo" if mo else "")
                    st.markdown(f"- **Tenure:** {tenure_str}")

            # Escalation reason
            reason = rec.get("escalation_reason") or "—"
            st.markdown(
                f'<div class="esc-reason">'
                f'<strong>⚠️ Escalation reason:</strong> {_html.escape(reason)}'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Conversation summary
            summary = rec.get("conversation_summary")
            stored_history = rec.get("conversation_history") or []

            if summary:
                st.markdown("**📝 Conversation Summary**")
                st.info(summary)

            # ── Conversation history (Langfuse live fetch → stored → nothing) ──
            sid = rec.get("session_id", "")
            hex_id_for_fetch = sid.replace("-", "").lower() if sid else ""
            valid_sid = len(hex_id_for_fetch) == 32 and all(
                c in "0123456789abcdef" for c in hex_id_for_fetch
            )

            if valid_sid and LANGFUSE_PUBLIC_KEY:
                live_history = _fetch_langfuse_conversation(hex_id_for_fetch)
            else:
                live_history = []

            history = live_history or stored_history
            source_label = (
                "📡 Live from Langfuse" if live_history
                else "💾 Stored history"  if stored_history
                else None
            )

            if history:
                with st.expander(
                    f"💬 Full conversation ({len(history)} turns)"
                    + (f"  ·  {source_label}" if source_label else ""),
                    expanded=False,
                ):
                    for turn in history:
                        role    = turn.get("role", "user")
                        content = turn.get("content", "")
                        if role == "user":
                            with st.chat_message("user", avatar="🧑"):
                                st.write(content)
                        else:
                            with st.chat_message("assistant", avatar="🤖"):
                                st.write(content)
            elif not summary:
                st.caption("💬 Conversation not captured for this record.")

            # ── Mark as Resolved (pending records only) ───────────────────────
            if allow_resolve and (rec.get("status") or "pending") == "pending":
                st.divider()
                with st.expander("✅ Mark as Resolved", expanded=False):
                    comment = st.text_area(
                        "Resolution comment",
                        key=f"resolve_comment_{esc_id}{key_suffix}",
                        placeholder="Describe the action taken — e.g. 'Called customer, referred to branch RM for premium financing.'",
                        height=90,
                    )
                    if st.button("Confirm Resolution", key=f"resolve_btn_{esc_id}{key_suffix}",
                                 type="primary"):
                        _update_escalation_status(esc_id, "resolved", comment)
                        st.rerun()

            # Footer: ref ID + trace link
            st.divider()
            foot_l, foot_r = st.columns([3, 1])
            with foot_l:
                st.caption(f"Ref: `{esc_id}`  ·  {date_str}")
            with foot_r:
                if valid_sid and LANGFUSE_PUBLIC_KEY:
                    host = (LANGFUSE_HOST or "https://cloud.langfuse.com").rstrip("/")
                    project_id = _get_langfuse_project_id()
                    if project_id:
                        trace_url = f"{host}/project/{project_id}/traces/{hex_id_for_fetch}"
                    else:
                        trace_url = f"{host}/traces/{hex_id_for_fetch}"
                    st.markdown(f"[🔍 Langfuse trace]({trace_url})")
                else:
                    st.caption("*(no trace)*")

    # ── Tabs: Pending / Resolved / All ────────────────────────────────────────
    if not esc_records:
        st.info("No escalation records yet. Leads appear here when a loan request exceeds "
                "the advisory ceiling for that product.")
    else:
        tab_pending_esc, tab_resolved_esc, tab_all_esc = st.tabs([
            f"🔴 Pending  ({n_pending})",
            f"✅ Resolved  ({n_resolved})",
            f"📋 All  ({len(esc_records)})",
        ])

        _LOAN_FILTER_CHOICES = ["All", "Home Loan", "Personal Loan", "MSME Loan", "Car Loan"]

        def _filter_bar(suffix: str):
            fc1, fc2, fc3 = st.columns([2, 2, 2])
            with fc1:
                lt = st.selectbox("Loan type", _LOAN_FILTER_CHOICES, key=f"lt_{suffix}")
            with fc2:
                df = st.date_input("From date", value=None, key=f"df_{suffix}")
            with fc3:
                dt = st.date_input("To date",   value=None, key=f"dt_{suffix}")
            return lt, df, dt

        with tab_pending_esc:
            lt, df, dt = _filter_bar("pend")
            pending_recs = _apply_esc_filters(
                [r for r in esc_records if (r.get("status") or "pending") == "pending"],
                lt, df, dt,
            )
            if not pending_recs:
                st.info("No pending records match the selected filters." if n_pending
                        else "No pending escalations. All leads have been resolved.")
            else:
                st.caption(f"{len(pending_recs)} pending lead(s) — most recent first")
                for card_n, rec in enumerate(reversed(pending_recs), 1):
                    _render_esc_card(rec, card_n, allow_resolve=True, key_suffix="_p")

        with tab_resolved_esc:
            lt2, df2, dt2 = _filter_bar("res")
            resolved_recs = _apply_esc_filters(
                [r for r in esc_records if (r.get("status") or "pending") == "resolved"],
                lt2, df2, dt2,
            )
            if not resolved_recs:
                st.info("No resolved records match the selected filters." if n_resolved
                        else "No resolved escalations yet. Use 'Mark as Resolved' on a pending lead.")
            else:
                st.caption(f"{len(resolved_recs)} resolved lead(s) — most recent first")
                for card_n, rec in enumerate(reversed(resolved_recs), 1):
                    _render_esc_card(rec, card_n, allow_resolve=False, key_suffix="_r")

        with tab_all_esc:
            lt3, df3, dt3 = _filter_bar("all")
            all_recs = _apply_esc_filters(esc_records, lt3, df3, dt3)
            if not all_recs:
                st.info("No records match the selected filters.")
            else:
                st.caption(f"{len(all_recs)} of {len(esc_records)} lead(s) — most recent first")
                for card_n, rec in enumerate(reversed(all_recs), 1):
                    _render_esc_card(rec, card_n, allow_resolve=True, key_suffix="_a")

    # ══════════════════════════════════════════════════════════════════════════
    # Section 2 — Feedback Analytics
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown('<p class="rm-section">⭐ Feedback Analytics</p>', unsafe_allow_html=True)

    if not fb_records:
        st.info("No feedback data yet. Ratings submitted in the chat will appear here.")
    else:
        if fb_signal:
            fa1, fa2, fa3 = st.columns(3)
            fa1.metric("Total ratings", len(fb_records))
            fa2.metric("Avg — last 20", f"{fb_signal.get('avg_stars', '—')} / 5")
            fa3.metric("Adaptation signal", fb_signal.get("adapt", "—"))

            adapt = fb_signal.get("adapt")
            if adapt == "increase_empathy":
                st.warning("⚠️  Empathy boost ACTIVE — system prompt enriched for new sessions.")
            elif adapt == "maintain":
                st.success("✅  Feedback strong — no prompt adaptation needed.")
            elif adapt == "neutral":
                st.info(fb_signal.get("action", "Ratings in acceptable range."))
        else:
            st.caption(f"{len(fb_records)} record(s) collected — need 5 for RLHF signal.")

        dist = Counter(r.get("rating", 0) for r in fb_records)
        chart_data = {f"{k}★": dist.get(k, 0) for k in range(1, 6)}
        st.bar_chart(chart_data)

        st.markdown("**Recent ratings (last 10)**")
        recent_rows = [
            {
                "Stars":   "⭐" * r.get("rating", 0),
                "Type":    r.get("feedback_type", "per_turn"),
                "Comment": r.get("comment") or "—",
                "Session": r.get("session_id", "")[:8] + "…",
                "Turn":    r.get("turn", "—"),
                "Time":    r.get("ts", "")[:16].replace("T", " "),
            }
            for r in fb_records[-10:][::-1]
        ]
        st.dataframe(recent_rows, width="stretch", hide_index=True)

    # ══════════════════════════════════════════════════════════════════════════
    # Section 3 — Interaction Log
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown('<p class="rm-section">📋 Interaction Log</p>', unsafe_allow_html=True)

    if log_entries:
        log_rows = [
            {
                "Time (UTC)":        r.get("ts", "")[:16].replace("T", " "),
                "Intent":            r.get("intent", "—"),
                "Blocked":           "🚫" if r.get("blocked") else "✓",
                "Latency ms":        r.get("latency_ms", "—"),
                "User input (masked)": r.get("user_input_masked", "")[:80],
            }
            for r in reversed(log_entries)
        ]
        st.dataframe(log_rows, width="stretch", hide_index=True)
    else:
        st.info("Interaction log entries appear after the first chat turn in this session.")

    # ══════════════════════════════════════════════════════════════════════════
    # Section 4 — Session Latency
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown('<p class="rm-section">⚡ Session Latency</p>', unsafe_allow_html=True)

    if lats:
        sorted_lats = sorted(lats)
        p95_val = sorted_lats[max(0, int(0.95 * len(sorted_lats)) - 1)]
        sl1, sl2, sl3, sl4 = st.columns(4)
        sl1.metric("Turns this session", len(lats))
        sl2.metric("Avg latency", f"{sum(lats) / len(lats):.0f} ms")
        sl3.metric("P95 latency", f"{p95_val} ms")
        sl4.metric("Max latency", f"{max(lats)} ms")
        if p95_val <= 5000:
            st.success(f"✅  P95 {p95_val} ms — within 5 s SLA target")
        else:
            st.error(f"❌  P95 {p95_val} ms — exceeds 5 s SLA target")
        st.line_chart({"Latency (ms)": lats})
    else:
        st.info("Latency data appears here after the first chat turn in this session.")
