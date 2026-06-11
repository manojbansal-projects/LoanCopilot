# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**AI-Powered Loan Origination Copilot** — An IIT Madras Capstone project (Scenario 2: Banking, Track A: LangChain).

A conversational AI agent that guides retail customers through early-stage loan origination. It provides:
- Indicative eligibility assessments
- EMI estimates  
- Document requirement checklists
- Policy-grounded answers for 4 loan products (Home, Personal, MSME, New Car)

**Status:** Currently in development phases (Phases 2–4 using Jupyter notebooks; production code deployable in Phases 5+).

---

## Tech Stack

- **LLM / Agent:** LangChain AgentExecutor (ReAct), OpenAI GPT-4o (agent) + GPT-4o-mini (safety)
- **Vector DB:** ChromaDB persistent (`knowledge/chromadb/`)
- **Embeddings:** OpenAI text-embedding-3-small
- **Observability:** Langfuse self-hosted — **the only observability tool** (LangSmith and Arize Phoenix excluded; see `docs/engineering_justification.md`)
- **Web UI:** Streamlit (`deployment/app.py`)
- **CLI:** `python scripts/run_agent.py`

---

## Commands

```bash
# One-time setup
pip install -r requirements.txt && cp .env.example .env

# Build ChromaDB index (run after any policy doc change)
python scripts/ingest_documents.py

# Run CLI agent
python scripts/run_agent.py [--phase 2|3|4|5]

# Run Streamlit UI (Phase 8+)
streamlit run deployment/app.py

# Run evaluations
python scripts/run_evaluation.py --suite all   # or: rag | tools | safety

# RLHF analysis
python scripts/run_rlhf_pipeline.py
```

---

## Module Map

| Module | Purpose |
|--------|---------|
| `agent/core_agent.py` | `LoanCopilotAgent` — instantiate with `phase=N` to select tier |
| `agent/prompts.py` | 3 prompt variants (V1/V2/V3); V3 is default (`SYSTEM_PROMPT`) |
| `agent/memory.py` | `SessionState` dataclass + `ConversationBufferWindowMemory(k=10)` |
| `agent/planner.py` | `next_question()` — drives profile collection sequence |
| `retrieval/` | `document_loader → chunker → embedder → chroma_store → retriever` pipeline |
| `tools/tool_registry.py` | `get_all_tools()` — registers all 5 `@tool` functions |
| `tools/eligibility_checker.py` | FOIR + credit score + amount/tenure limits |
| `tools/emi_calculator.py` | Reducing-balance EMI formula |
| `tools/document_checklist.py` | Product × employment-type lookup table |
| `tools/tool_search.py` | RAG-backed FAQ (`lookup_loan_status`) |
| `tools/tool_escalate.py` | RM handoff packet (`generate_escalation_summary`) |
| `safety/guardrails.py` | Stage A: keyword filter; Stage B: GPT-4o-mini intent classifier |
| `safety/pii_filter.py` | Regex masker — Aadhaar, PAN, mobile, email, account numbers |
| `monitoring/langfuse_logger.py` | `get_langfuse_callback()` + `score_session()` |
| `policy_rlhf/` | `feedback_collector`, `policy_checker`, `policy_updater` |
| `deployment/config.py` | Single source of truth for all env vars and constants |

---

## Key Constraints

- `OPENAI_API_KEY` required for Phase 3+
- Policy docs in `knowledge/raw/` are synthetic — not official bank policy
- All log writes must go through `safety/pii_filter.mask()` first
- Always give an INDICATIVE RATE RANGE (e.g. "8.50%–9.25% p.a.") from policy documents, never a single promised rate. Always add a disclaimer that the actual rate is confirmed at sanction. Do not give a flat "contact branch" non-answer when a range is available.
- Escalation ceiling breach → always invoke `generate_escalation_summary` tool

## Escalation Ceilings (defined in `deployment/config.py`)

| Product | Ceiling |
|---------|---------|
| Home Loan | ₹1.5 Cr |
| Personal Loan | ₹40 L (product max) |
| MSME Loan | ₹2 Cr |
| New Car Loan | ₹20 L (product max) |

## Adding a Loan Product

1. Add `knowledge/raw/{product}_policy.txt`
2. Update `PRODUCT_MAP` in `retrieval/document_loader.py`
3. Add product entry to `tools/eligibility_checker.py::PRODUCT_LIMITS` + `RATE_BANDS`
4. Add product to `tools/document_checklist.py::_BY_PRODUCT_EMPLOYMENT`
5. Add product to `deployment/config.py::ESCALATION_CEILINGS`
6. Re-run `python scripts/ingest_documents.py`

## Resources

- Implementation plan with task buckets and done criteria: `IMPLEMENTATION_PLAN.md`
- Design docs: `docs/specification_v2.docx`, `docs/concept_document.docx`
- Architecture diagram: `docs/architecture_diagram.docx`
- Engineering decisions: `docs/engineering_justification.md`
