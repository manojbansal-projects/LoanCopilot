# Implementation Plan
**AI-Powered Loan Origination Copilot — 10-Day Build**

Each bucket maps to one capstone phase and one grading rubric dimension.
Tasks are ordered; later tasks in a bucket depend on earlier ones.
"Done when" = the specific, observable signal that the task is complete.

---

## BUCKET 0 — Repository Setup ✅
**Outcome:** Clean, runnable repo skeleton; all engineers can orient instantly.

| # | Task | Done when |
|---|------|-----------|
| 0.1 | Create folder structure per spec | `ls` shows all 15+ module folders |
| 0.2 | Move 5 policy docs to `knowledge/raw/` | `knowledge_base/` folder deleted |
| 0.3 | Move 3 Word docs to `docs/` | Root contains no .docx files |
| 0.4 | Create `requirements.txt` | All 15 packages listed |
| 0.5 | Create `.env.example` | All env vars documented with placeholders |
| 0.6 | Create `.gitignore` | `knowledge/chromadb/`, `logs/*.log`, `.env` all ignored |
| 0.7 | Write Python stubs for all modules | Every `__init__.py` exists; all key files importable |
| 0.8 | Write `data/policy/policy.json` | 4 products × 8+ fields each |
| 0.9 | Write `data/evaluation/test_cases.json` | 5 Q1–Q5 + 5 safety prompts |
| 0.10 | Write `docs/*.md` stubs | 5 markdown docs exist with headings |
| 0.11 | Update `README.md` | Phase map, quick-start, and folder layout are current |
| 0.12 | Write `IMPLEMENTATION_PLAN.md` | This file |

---

## BUCKET 1 — Phase 2: Rules-Based CLI Agent
**Target day:** Day 2
**Outcome:** Working CLI that handles all 5 test-question intents via deterministic logic — no LLM call, no API key needed.

| # | Task | Done when |
|---|------|-----------|
| 1.1 | Implement `agent/core_agent.py::_rules_response` — keyword intent detection | 5 intents recognised: eligibility / EMI / documents / FAQ / escalation |
| 1.2 | Implement `agent/planner.py::next_question` — profile collection sequence | Returns correct next field name for each missing profile field |
| 1.3 | Implement `tools/emi_calculator.py::calculate_emi` — reducing-balance formula | ₹30L × 9% × 240 mo = ₹26,992 ± ₹5 |
| 1.4 | Implement `tools/eligibility_checker.py` — FOIR, age, credit-score, amount rules | All 4 rejection reasons trigger for crafted inputs |
| 1.5 | Run 5-question demo via `python scripts/run_agent.py --phase 2` | All 5 questions return a meaningful response without LLM |
| 1.6 | Document 2 limitations in `notebooks/phase2_exploration.ipynb` | Markdown cell lists: no policy grounding, no context retention |

---

## BUCKET 2 — Phase 3: LLM Integration + Prompt Engineering
**Target day:** Day 3
**Outcome:** Langfuse dashboard live; prompt comparison table showing V3 wins on safety (Q3) and field collection (Q1/Q4).

| # | Task | Done when |
|---|------|-----------|
| 2.1 | Start Langfuse self-hosted via Docker Compose | Dashboard accessible at `http://localhost:3000` |
| 2.2 | Wire `monitoring/langfuse_logger.py::get_langfuse_callback` into agent | First LLM call creates a trace visible in Langfuse |
| 2.3 | Verify 3 prompt variants in `agent/prompts.py` | `PROMPT_VARIANTS` dict has V1, V2, V3 keys with distinct text |
| 2.4 | Create Langfuse dataset `prompt_comparison_5q` with Q1–Q5 | Dataset visible in Langfuse Datasets panel |
| 2.5 | Run each variant against the dataset (15 runs total) | 15 trace entries visible in Langfuse |
| 2.6 | Score each run using Langfuse LLM-as-judge rubric | All 15 runs have a numeric quality score |
| 2.7 | Export results → populate `docs/prompt_comparison_table.md` | All 5 question rows filled; V3 default justified by data |
| 2.8 | Set `SYSTEM_PROMPT = V3_COT_SAFETY` as confirmed default | `agent/prompts.py` line `SYSTEM_PROMPT = V3_COT_SAFETY` |

---

## BUCKET 3 — Phase 4: RAG with ChromaDB
**Target day:** Day 4
**Outcome:** ChromaDB populated; RAG precision ≥ 70% on 20Q Langfuse eval; before/after improvement visible on Q2 and Q5.

| # | Task | Done when |
|---|------|-----------|
| 3.1 | Implement `retrieval/document_loader.py` | `load_documents()` returns 5 `Document` objects |
| 3.2 | Implement `retrieval/chunker.py` (500 chars, 100 overlap, product-label prefix) | 5 docs produce ~160 chunks; each chunk prefixed with product label for retrieval accuracy |
| 3.3 | Implement `retrieval/embedder.py` — `text-embedding-3-small` | `get_embeddings()` returns valid `OpenAIEmbeddings` |
| 3.4 | Implement `retrieval/chroma_store.py` — `build_store` + `load_store` | `knowledge/chromadb/` directory populated after `python scripts/ingest_documents.py` |
| 3.5 | Implement `retrieval/retriever.py::retrieve` | `retrieve("home loan FOIR")` returns 5 relevant chunks (RAG_TOP_K=5) |
| 3.6 | Wire retriever to `tools/tool_search.py` | `query_loan_policy("car loan rate")` returns non-empty string from policy docs |
| 3.7 | Create Langfuse dataset `rag_eval_20q` (extend test_cases.json to 20 Qs) | 20 Q/A pairs uploaded to Langfuse |
| 3.8 | Run Langfuse LLM-as-judge on all 20 Qs | Pass rate ≥ 70%; results in Langfuse dashboard |
| 3.9 | Before/after notebook cell on Q2 (doc list) and Q5 (rate) | Notebook shows no-RAG vs RAG response side by side |

---

## BUCKET 4 — Phase 5: Tool Integration (ReAct AgentExecutor) ✅
**Target day:** Days 5–6
**Outcome:** All 5 tools appear in Langfuse traces; EMI range on Q1; escalation triggered on MSME ₹5Cr.

### Sub-bucket 4A — Core Tools (Day 5)

| # | Task | Done when |
|---|------|-----------|
| 4A.1 | Verify `tools/emi_calculator.py` as `@tool` with correct schema | ✅ `calculate_emi.name == "calculate_emi"` passes; schema has 3 required args |
| 4A.2 | Verify `tools/eligibility_checker.py` as `@tool` | ✅ FOIR rejection fires for income=80K, loan=50L → FOIR 56% → rejected |
| 4A.3 | Implement `tools/tool_registry.py::get_all_tools` | ✅ Returns list of 5 tools |
| 4A.4 | Wire tools into `agent/core_agent.py::_build_executor` | ✅ Uses `create_agent` (LangGraph tool-calling); `_executor_response` passes chat_history and updates memory |
| 4A.5 | Test Q1 end-to-end | ✅ Eligible: eligibility → EMI (₹26,992 exact) → document checklist |

### Sub-bucket 4B — Remaining Tools + Escalation (Day 6)

| # | Task | Done when |
|---|------|-----------|
| 4B.1 | Verify `tools/document_checklist.py` | ✅ Returns 5 common + 4 product-specific docs for home_loan/salaried |
| 4B.2 | Verify `tools/tool_search.py` | ✅ RAG-backed; returns policy chunks from ChromaDB |
| 4B.3 | Verify `tools/tool_escalate.py` | ✅ Returns dict with `escalation_saved=True`, `rm_briefing`, and `customer_message`; validates mobile + email; persists record to `data/rlhf/escalations.json` |
| 4B.4 | Test Q4 escalation ceiling | ✅ MSME ₹5 Cr → `generate_escalation_summary` auto-invoked; RM message returned |
| 4B.5 | Verify all 5 tools appear across test traces | ✅ All 5 tools exercised across Demos 1–4 in phase5_tools.ipynb |

### Sub-bucket 4C — MCP Exposure Layer ✅
**Outcome:** All 5 tools discoverable and callable via Model Context Protocol; LangChain agent can use either direct or MCP path; 11 MCP-specific tests pass.

| # | Task | Done when |
|---|------|-----------|
| 4C.1 | Install `mcp>=1.0.0` SDK (FastMCP) | ✅ `from mcp.server.fastmcp import FastMCP` succeeds; v1.27.2 installed |
| 4C.2 | Implement `loan_mcp/server.py` | ✅ FastMCP server registers all 5 tools; `mcp._tool_manager._tools` has 5 entries |
| 4C.3 | Implement `loan_mcp/client.py` | ✅ `LoanMCPClient` async context manager (stdio subprocess) + `call_tool_sync` in-process helper |
| 4C.4 | Wire `USE_MCP` into `tools/tool_registry.py` and `agent/core_agent.py` | ✅ `get_mcp_tools()` builds 5 `StructuredTool` objects with correct Pydantic schemas; `_build_executor` checks `USE_MCP` env var |
| 4C.5 | Write `tests/test_mcp_server.py` (11 tests) | ✅ All 11 pass; full suite 244 tests green; 0 regressions |
| 4C.6 | Add MCP engineering justification (`docs/engineering_justification.md` §6) | ✅ Trade-off against low-level SDK + serialisation overhead documented |
| 4C.7 | Update `IMPLEMENTATION_PLAN.md`, `CLAUDE.md`, `README.md` | ✅ Module map, commands, and phase map reflect MCP layer |
| 4C.8 | Update `docs/specification_v2.docx` and `docs/concept_document.docx` | Architecture sections updated; old tool name `lookup_loan_status` → `query_loan_policy` fixed |
| 4C.9 | Rebuild `docs/capstone_presentation.pptx` | S4 Architecture, S5 Tech Stack, S7 Tools updated; MCP shown in architecture diagram |

---

## BUCKET 5 — Phase 6: Memory + Multi-Turn ✅
**Target day:** Day 7
**Outcome:** 5-turn session in Langfuse; agent never re-asks a collected field; `start over` resets cleanly.

| # | Task | Done when |
|---|------|-----------|
| 5.1 | Verify `agent/memory.py::ConversationBufferWindowMemory(k=10)` wired | ✅ `agent.memory.chat_memory.messages` grows with each turn |
| 5.2 | Verify `SessionState.profile` accumulates across turns | ✅ `_extract_profile` called in `_executor_response` after each turn |
| 5.3 | Test no-duplicate-question flow (Demo 4 from demo_script.md) | ✅ `notebooks/phase6_memory.ipynb` Demo 3 — income asked once |
| 5.4 | Test `reset` clears both LangChain memory and `SessionState` | ✅ `chat("start over")` calls `reset()` → messages=[] and profile=None |
| 5.5 | Post 5-turn session to Langfuse; verify session view | ✅ Demo 5 — session_id forwarded as trace_id; flush() called |

**Key changes:**
- `agent/core_agent.py` — `_RESET_PHRASES` set + start-over detection in `chat()`; `_extract_profile` called after every `_executor_response` turn
- `notebooks/phase6_memory.ipynb` — 6 demo cells covering all 5 done criteria + sliding-window cap demo

---

## BUCKET 6 — Phase 7: Adaptive Behaviour ✅
**Target day:** Day 8
**Outcome:** Feedback collected, PII-masked, and stored; before/after demo on empathy adaptation; Langfuse annotation ≥ 4/5 on 3 escalation summaries.

| # | Task | Done when |
|---|------|-----------|
| 6.1 | Implement `policy_rlhf/feedback_collector.py::record_feedback` | ✅ `data/rlhf/feedback_store.json` grows by 1 entry per call; PII masked via `safety/pii_filter` |
| 6.2 | Wire feedback in `deployment/app.py` (1–5 star rating + optional comment) | ✅ `st.feedback("stars")` renders star selector; comment text area appears on selection; Submit posts normalized score `(rating−1)/4` to store + Langfuse |
| 6.3 | Implement Rule 1 in `policy_rlhf/policy_updater.py` — low-rating empathy injection | ✅ `analyse_feedback()` returns `adapt="increase_empathy"` when avg < 0.6 |
| 6.4 | Implement Rule 2 — high-rating positive reinforcement | ✅ Returns `adapt="maintain"` when avg ≥ 0.85 |
| 6.5 | Verify `policy_rlhf/policy_checker.py` blocks approval-language | ✅ `check_response("Your loan is guaranteed!")` returns 1 violation; wired into `_executor_response` |
| 6.6 | Annotate 3 escalation summaries in Langfuse (target ≥ 4/5) | ✅ LLM-as-judge in `notebooks/phase7_rlhf.ipynb` Demo 6; average written to `docs/evaluation_report.md` |

**Key changes:**
- `policy_rlhf/policy_updater.py` — `EMPATHY_PREFIX` constant + `get_adapted_prompt(base_prompt)` returns empathy-enriched prompt when avg_rating < 0.6
- `policy_rlhf/policy_checker.py` — wired into `agent/core_agent.py::_executor_response`; violations scored as `policy_compliance=0.0` in Langfuse
- `deployment/app.py` — 👍/👎 feedback buttons with per-message state; RM Dashboard tab shows real escalation records + live feedback analytics
- `notebooks/phase7_rlhf.ipynb` — 6 demo cells covering all 6 done criteria

---

## BUCKET 7 — Phase 8: Deployment + Safety Gate ✅
**Target day:** Day 9
**Outcome:** Streamlit app running on localhost; PII masking demo; P95 < 5s over 10 turns.

| # | Task | Done when |
|---|------|-----------|
| 7.1 | Verify `safety/pii_filter.py::mask` — all 5 PII types | ✅ All 5 types (Aadhaar, PAN, mobile, email, account) verified in `notebooks/phase8_deployment.ipynb` Demo 1 |
| 7.2 | Integrate safety gate into chat turn: `classify_intent` before `agent.chat` | ✅ `_run_safety_gate()` in `deployment/app.py` — Stage A keyword + Stage B LLM; fail-open on error |
| 7.3 | PII masker applied before every log write | ✅ `monitoring/interaction_logger.py::log_interaction` masks both input and response; `[AADHAAR REDACTED]` verified in Demo 3 |
| 7.4 | Implement Customer Chat tab in `deployment/app.py` | ✅ Full chat with safety gate + feedback + logging |
| 7.5 | Implement Start Over button | ✅ Resets agent + messages |
| 7.6 | Implement RM Dashboard tab | ✅ Escalation queue + latency metrics + feedback analytics + interaction log |
| 7.7 | Measure P95 latency: 10 consecutive turns | ✅ Demo 4 — P95 measured and written to `docs/evaluation_report.md` |
| 7.8 | Implement error handling for API timeout and tool failure | ✅ `try/except` in `_executor_response` + `_chain_response`; friendly message returned |

**Key changes:**
- `monitoring/interaction_logger.py` — NEW: JSONL logger; both fields PII-masked before write; `read_recent(n)` for dashboard
- `deployment/app.py` — `_run_safety_gate()` wraps classify_intent (fail-open); wall-clock timing per turn; `log_interaction` called after each turn; RM Dashboard shows latency bar chart + interaction log table
- `notebooks/phase8_deployment.ipynb` — 5 demo cells covering all 8 tasks

---

## BUCKET 8 — Phase 9: Evaluation + Submission
**Target day:** Day 10
**Outcome:** All 4 graded metrics met; `docs/evaluation_report.md` complete; submission zip ready.

| # | Task | Done when |
|---|------|-----------|
| 8.1 | Extend `data/evaluation/test_cases.json` to 20 RAG Qs | File has 20 entries under `rag_20q` |
| 8.2 | Upload 20Q set to Langfuse dataset `rag_eval_20q` | Dataset visible in Langfuse |
| 8.3 | Run `python scripts/run_evaluation.py --suite rag` | Pass rate ≥ 70%; printed to stdout + logged to Langfuse |
| 8.4 | Run `python scripts/run_evaluation.py --suite tools` (30 scenarios) | Tool-selection accuracy ≥ 80% across 5 tools |
| 8.5 | Run `python scripts/run_evaluation.py --suite safety` (5 prompts) | Block rate = 100% (5/5) |
| 8.6 | Root-cause 1 failing RAG case; implement fix; re-run | Before/after scores in Langfuse trace pair; after > before |
| 8.7 | Populate `docs/evaluation_report.md` from Langfuse exports | All table cells filled; Langfuse dashboard link included |
| 8.8 | Populate `docs/prompt_comparison_table.md` (all 5 rows) | V3 default justified by numeric scores in all 5 rows |
| 8.9 | Final 5-question demo recording | Video / screenshot set covers all 5 demos from `docs/demo_script.md` |
| 8.10 | Package submission zip | Contains: `/agent`, `/retrieval`, `/tools`, `/safety`, `/monitoring`, `/evaluation`, `/data`, `/docs`, `README.md`, `IMPLEMENTATION_PLAN.md`, `requirements.txt` |

---

## Grading Rubric Alignment

| Rubric Dimension | Covered by |
|-----------------|-----------|
| Tool use (5 tools) | Bucket 4 |
| RAG quality | Bucket 3 + 8.3 |
| Safety gate | Bucket 7 + 8.5 |
| Memory / multi-turn | Bucket 5 |
| Adaptive behaviour | Bucket 6 |
| Observability (Langfuse) | Bucket 2 (setup) + all subsequent buckets |
| Evaluation rigour | Bucket 8 |
| Documentation | Bucket 0 + `docs/*.md` |

---

## Known Deviations from Spec

| Item | Spec says | Implementation |
|------|-----------|---------------|
| Vector store | ChromaDB | ChromaDB ✅ (`retrieval/chroma_store.py`) |
| Folder uses `faiss_store.py` | User structure | File exists as redirect stub; real impl in `chroma_store.py` |
| `monitoring/langsmith_tracer.py` | User structure | File exists; raises `ImportError` — use `langfuse_logger.py` instead |
| `knowledge/faiss_index/` | User structure | Folder replaced by `knowledge/chromadb/` |
| RAG_TOP_K = 3 | Original config | Raised to 5 — rate-range chunks for tabular policy sections rank at positions 4–5; k=3 missed them |
| Plain chunk text | Original chunker | Each chunk prefixed with product label (e.g. `[Home Loan Policy]`) so semantically similar chunks from different products rank correctly |
| Rate answer = "contact branch" | Original V3 prompt | Changed to provide indicative range from policy with sanction disclaimer — "contact branch" alone is not useful for a pre-application copilot |
