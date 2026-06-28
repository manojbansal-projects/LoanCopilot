# AI-Powered Loan Origination Copilot

**IIT Madras AI Capstone · Scenario 2: Banking · Track A: LangChain**

A conversational AI agent that guides retail bank customers through early-stage loan origination for 4 products (Home, Personal, MSME, New Car). Provides indicative eligibility, EMI estimates, document checklists, and policy-grounded answers via RAG — fully observable through Langfuse cloud tracing.

---

## Quick Start — Run the App from Scratch

Follow these steps in order. Estimated time: 10 minutes.

### Step 1 — Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.10+ | Check: `python --version` |
| pip | latest | Check: `pip --version` |
| Git | any | To clone the repo |
| API key | Vocareum or OpenAI — GPT-4o / GPT-4o-mini access | Required for Phase 3+ |
| Langfuse account | cloud.langfuse.com free tier | For observability (optional for basic run) |

> **No API key?** You can still run the rules-based Phase 2 agent (no LLM, no costs). See [Option B — CLI](#option-b--cli) and use `--phase 2`.

---

### Step 2 — Clone the Repository

```bash
git clone https://github.com/manojbansal-projects/IITM-LoanCopilot.git
cd IITM-LoanCopilot
```

---

### Step 3 — Create a Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows PowerShell
```

Verify the environment is active: your shell prompt should show `(.venv)`.

---

### Step 4 — Install Dependencies

```bash
pip install -r requirements.txt
```

This installs ~25 packages including LangChain, ChromaDB, Streamlit, FastMCP, Langfuse, and OpenAI.

---

### Step 5 — Configure Environment Variables

```bash
cp .env.example .env
```

Open `.env` in any text editor and fill in the values:

```ini
# --- Required for LLM agent (Phase 3+) ---
OPENAI_API_KEY=<your-key>      # Vocareum key (does NOT start with sk-)
                               # or standard OpenAI key (starts with sk-)
OPENAI_BASE_URL=https://openai.vocareum.com/v1
                               # Vocareum proxy URL (used in this project)
                               # Leave blank if using standard OpenAI directly

# --- Required for observability (optional for basic run) ---
LANGFUSE_PUBLIC_KEY=pk-lf-...  # From cloud.langfuse.com → Settings → API keys
LANGFUSE_SECRET_KEY=sk-lf-...  # Same location
LANGFUSE_HOST=https://cloud.langfuse.com

# --- Optional overrides (defaults shown) ---
SAFETY_MODEL=gpt-4o-mini       # Model used for safety gate and RLHF policy updates
USE_MCP=true                   # true = FastMCP tool path; false = direct import path
```

> **Langfuse not configured?** The agent runs fine without it — tracing is silently skipped. You will see a warning on first run but the app is fully functional.

---

### Step 6 — Build the ChromaDB Knowledge Index

```bash
python scripts/ingest_documents.py
```

Expected output:
```
✓ 4 products ingested — N chunks stored in knowledge/chromadb/
```

This embeds the 5 synthetic policy documents into a local ChromaDB vector store. Re-run this step only if you edit files in `knowledge/raw/`.

---

### Step 7 — Launch the Application

**Web UI (recommended):**

```bash
streamlit run deployment/app.py
```

Open `http://localhost:8501` in your browser. Two tabs:
- **💬 Customer Chat** — live agent with safety gate, per-turn 1–5 star feedback, and start-over
- **📊 RM Dashboard** — escalation queue, feedback analytics, adaptive policy entries, session latency, interaction log

**CLI (terminal):**

```bash
python scripts/run_agent.py            # Full LLM + tools agent (requires API key)
python scripts/run_agent.py --phase 2  # Rules-based agent — no API key needed
```

Type `start over` at any point to reset the session.

---

### Step 8 — Test with a Sample Conversation

Try this in the chat:

```
You: I want a home loan of 50 lakhs for 20 years.
You: I am 35, salaried, monthly income 1.2 lakhs, CIBIL 750.
You: What documents do I need?
```

The agent should check eligibility, calculate an EMI range, and return a document checklist — all in a single multi-turn conversation.

---

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ModuleNotFoundError` | Re-run `pip install -r requirements.txt` with the virtualenv active |
| `ChromaDB collection not found` | Run Step 6 (ingest) before launching the app |
| `API budget exceeded` message | Top up your OpenAI / Vocareum API credit; the app shows a user-friendly message instead of a raw error |
| `LANGFUSE_*` warnings | Fill in Langfuse keys in `.env`, or ignore — the app runs without them |
| Port 8501 in use | Run `streamlit run deployment/app.py --server.port 8502` |
| `USE_MCP=true` tool errors | Set `USE_MCP=false` in `.env` to use the direct import path |

---

---

## Scenario Walkthroughs

### Scenario 1 — Eligibility + EMI (normal flow)

```
You: I want a home loan of 50 lakhs for 20 years.
You: I am 35 years old, salaried at Infosys. Monthly income 1.2 lakhs, CIBIL 750.
You: What documents will I need?
```

Expected agent behaviour:
1. Calls `check_eligibility` → FOIR check passes → eligible
2. Calls `calculate_emi` → shows monthly EMI at 8.50%–9.50% p.a. range
3. Calls `get_document_checklist` → lists identity, income, and property documents
4. All rates given as indicative ranges; disclaimer added

---

### Scenario 2 — Policy FAQ (RAG-backed)

```
You: Can an NRI apply for a home loan?
You: What is the minimum CIBIL score required for a personal loan?
You: Are there prepayment charges on MSME loans?
```

Expected agent behaviour:
- Calls `query_loan_policy` for each question
- Returns policy-grounded answers from ChromaDB (not generic "contact branch" replies)
- Langfuse trace shows the RAG retrieval observation

---

### Scenario 3 — Low CIBIL / Ineligible

```
You: I need an MSME loan of 30 lakhs. Age 42, income 80,000/month, CIBIL 580, tenure 5 years.
```

Expected agent behaviour:
- `check_eligibility` returns `eligible: false`, reason: CIBIL below minimum
- Agent explains why and suggests how to improve eligibility
- No escalation triggered (ineligible ≠ escalation)

---

### Scenario 4 — Escalation (amount exceeds ceiling)

Car Loan ceiling is ₹20L. Request ₹28L to trigger escalation:

```
You: I want a car loan for a Toyota Fortuner. On-road price is 28 lakhs, need the full amount.
You: I am 32, salaried at Wipro, income 95,000/month, CIBIL 740, tenure 7 years.
You: My name is Arjun Sharma, mobile 9845012345, email arjun@wipro.com. Available weekdays 11 AM–1 PM.
```

Expected agent behaviour:
1. `check_eligibility` returns `escalate_to_rm: true` (₹28L > ₹20L ceiling)
2. Agent collects name, mobile, email, preferred callback time
3. Calls `generate_escalation_summary` — validates mobile/email format
4. Record saved to `data/rlhf/escalations.json` with full RM briefing
5. Customer receives callback confirmation with last-4 digits of mobile
6. RM Dashboard (📊 tab) shows the new lead immediately

Home Loan ceiling is ₹1.5 Cr. Request ₹2.2 Cr to trigger a second escalation:

```
You: I need a home loan of 2.2 crores for a 3BHK in Pune. Tenure 25 years.
     Monthly income 1.8 lakhs, age 38, salaried with HDFC Bank, CIBIL 785.
You: Meera Iyer, 7654321098, meera@hdfcbank.com, prefer Saturday mornings.
```

---

### Scenario 5 — Existing EMI (FOIR edge case)

```
You: Home loan of 1.2 crores, 25 years. Age 40, income 2 lakhs/month, CIBIL 800, salaried at TCS.
     I also have a car loan EMI of 15,000/month.
You: Am I still eligible? What is my FOIR?
```

Expected: FOIR calculated as `(EMI + existing_emi) / income`; agent confirms eligibility with explanation.

---

### Scenario 6 — Start Over / Reset

```
You: start over
```

Clears all conversation history and profile state. The agent confirms reset and prompts for a new loan product.

---

### Scenario 7 — Safety Gate (out-of-scope)

```
You: Should I invest in mutual funds or FDs?
You: What is the best insurance plan?
```

Expected: Out-of-scope reply with branch hours. Trace shows `intent=OUT_OF_SCOPE` and `blocked=True` in the interaction log.

---

## RM Dashboard

Open the **📊 RM Dashboard** tab in the Streamlit app. Sections:

| Section | What it shows |
|---------|---------------|
| 🔔 Escalation Queue | All escalated leads with contact, loan details, RM briefing, and conversation history |
| 👍 Feedback Analytics | Star rating distribution, RLHF adaptation signal (empathy / maintain / neutral), avg score trend |
| 🧠 Adaptive Policy | Active behavioral instructions generated by the RLHF pipeline from low-rated customer comments; each entry shows source (🤖 LLM-generated or ✏️ manual) and trigger count |
| 📋 Interaction Log | Last 20 turns — PII-masked, intent label, latency, blocked flag |
| ⚡ Session Latency | Turn-by-turn latency chart + P95 vs 5 s SLA target |

Click **🔍 Langfuse trace** on any escalation card to open the full trace in cloud.langfuse.com.

---

## Seeding Demo Data

To populate the RM Dashboard and Langfuse with 8 scripted sessions (6 normal + 2 escalations) without typing manually:

```bash
# Requires a live OpenAI key with budget
python scripts/seed_sessions.py
```

This runs all 8 sessions using `gpt-4o-mini`, flushes Langfuse traces, and saves 2 escalation records to `data/rlhf/escalations.json`.

> **Note on API budget**: The script uses approximately $0.05–$0.08 total at `gpt-4o-mini` rates. If you are using a Vocareum proxy with a per-project cap, ensure sufficient budget before running.

---

## Langfuse Metrics Report

Pull a structured model evaluation report from your Langfuse project:

```bash
python scripts/langfuse_metrics.py
```

Output includes: total cost, avg cost/trace, token usage, input:output ratio, P50/P95 latency, model distribution, RLHF scores, session coverage, and top 5 traces by cost.

---

## Evaluation Suite

```bash
python scripts/run_evaluation.py --suite all    # RAG + tools + safety
python scripts/run_evaluation.py --suite rag    # 20-question RAG precision
python scripts/run_evaluation.py --suite tools  # Tool-selection accuracy
python scripts/run_evaluation.py --suite safety # Out-of-scope block rate
```

Target metrics: RAG pass rate ≥ 70%, tool accuracy ≥ 80%, safety block rate = 100%.

---

## RLHF Pipeline

```bash
python scripts/run_rlhf_pipeline.py
```

Analyses feedback from `data/rlhf/feedback_store.json` and runs two adaptation layers:

**Layer 1 — Within-session correction** (`agent/core_agent.py`): When a customer gives a low rating (≤ 2 stars) during a live session, `inject_feedback_signal()` queues a correction as a `SystemMessage` that the agent sees on the very next turn — no session restart required. A 4–5 star rating clears all pending corrections.

**Layer 2 — Cross-session adaptive policy** (`policy_rlhf/policy_updater.py`): `update_adaptive_policy()` calls GPT-4o-mini with the low-rated qualitative comments collected since the last run. The LLM generates novel behavioral instructions (e.g. "do not re-ask for information the customer already provided") and writes them to `data/rlhf/adaptive_policy.json`. On the next agent startup, `get_adapted_prompt()` prepends these instructions to the base system prompt.

**Empathy prefix**: If the average rating of the last 20 feedback entries falls below 0.60, a warmth-and-empathy prefix is automatically prepended to the system prompt for all subsequent sessions.

> **Manual policy entries**: Open `data/rlhf/adaptive_policy.json` and add entries with `"source": "manual"` — these are permanently protected from LLM overwrite and always stay active.

> **API key needed**: The `update_adaptive_policy()` step requires a working OpenAI API key. If the key is unavailable or over budget, the pipeline prints a clear message and skips that step without error.

---

## Rebuild Vector Index

Run this whenever you edit any file in `knowledge/raw/`:

```bash
python scripts/ingest_documents.py
```

---

## Phase Map

| Phase | Description | Key Files | Status |
|-------|-------------|-----------|--------|
| 2 | Rules-based CLI agent (no LLM) | `agent/core_agent.py` | ✅ Complete |
| 3 | LLM integration + prompt A/B | `agent/prompts.py`, `monitoring/langfuse_logger.py` | ✅ Complete |
| 4 | RAG with ChromaDB | `retrieval/`, `scripts/ingest_documents.py` | ✅ Complete |
| 5 | 5-tool LangGraph agent | `tools/`, `tools/tool_registry.py` | ✅ Complete |
| 6 | Multi-turn memory | `agent/memory.py`, `agent/core_agent.py` | ✅ Complete |
| 7 | Adaptive behaviour (RLHF) | `policy_rlhf/` | ✅ Complete |
| 8 | Streamlit deployment + safety gate | `deployment/app.py`, `safety/` | ✅ Complete |
| 9 | Full evaluation + packaging | `evaluation/`, `scripts/run_evaluation.py` | ✅ Complete |

Full task breakdown with done criteria: **[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)**

---

## Repository Layout

```
.
├── agent/              Core agent: prompts, memory, planner, LangGraph executor
├── retrieval/          ChromaDB RAG pipeline: load → chunk → embed → retrieve
├── tools/              5 LangChain tools (eligibility, EMI, docs, search, escalate)
├── safety/             Two-stage safety gate (keyword + LLM classifier) + PII masker
├── monitoring/         Langfuse callbacks, interaction JSONL logger
├── evaluation/         Test harness and metrics
├── policy_rlhf/        Feedback collection, policy checker, adaptation rules
├── loan_mcp/           MCP server/client (FastMCP, exposes 5 loan tools)
├── deployment/         Streamlit app + central config
├── scripts/            CLI entry points (ingest, run, evaluate, RLHF, seed, metrics)
├── knowledge/
│   ├── raw/            5 synthetic policy .txt files
│   ├── processed/      Chunked JSON (generated by ingest)
│   └── chromadb/       Persistent ChromaDB store (generated by ingest)
├── data/
│   ├── policy/         Compiled loan parameters (policy.json)
│   ├── evaluation/     Test cases (test_cases.json)
│   └── rlhf/           Feedback store + escalation records
├── docs/               Design docs + markdown reports
├── logs/               Interaction + error logs (PII-masked)
├── notebooks/          Jupyter exploration (Phases 2–8)
├── requirements.txt
├── .env.example
└── IMPLEMENTATION_PLAN.md
```

---

## Loan Products & Escalation Ceilings

| Product | Amount Range | Max Tenure | RM Escalation Ceiling |
|---------|-------------|------------|----------------------|
| Home Loan | ₹5L – ₹5 Cr | 30 yr | ₹1.5 Cr |
| Personal Loan | ₹50K – ₹40L | 5 yr | ₹40L (product max) |
| MSME Loan | ₹50K – ₹10 Cr | 15 yr | ₹2 Cr |
| New Car Loan | ₹3L – ₹20L | 7 yr | ₹20L (product max) |

---

## Tech Stack

- **LLM:** OpenAI GPT-4o (agent) · GPT-4o-mini (safety classifier)
- **Framework:** LangChain 1.3.x + LangGraph (`create_agent` tool-calling loop)
- **Tool transport:** FastMCP v1.27.2 (`loan_mcp/server.py`) — default path (`USE_MCP=true`); direct import via `USE_MCP=false`
- **Vector store:** ChromaDB persistent (`knowledge/chromadb/`)
- **Embeddings:** `text-embedding-3-small`
- **Observability:** Langfuse v4 cloud (LangSmith excluded — see `docs/engineering_justification.md`)
- **UI:** Streamlit with token-streaming (`st.write_stream`)

---

## Key Constraints

- `OPENAI_API_KEY` is required for Phase 3+ (Phase 2 runs rule-based without any key)
- Policy documents are **synthetic** — educational demo, not official bank policy
- All log writes go through `safety/pii_filter.py` (Aadhaar, PAN, mobile, email, account masked)
- Always returns **indicative rate ranges** — never a single promised rate
- **Never promises loan approval** — all assessments are "subject to credit appraisal"
- Does not ask for full Aadhaar, PAN, or bank account number at any point
