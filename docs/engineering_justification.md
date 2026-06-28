# Engineering Justification

Key architectural decisions and their rationale.

## 1. Langfuse Self-Hosted (not LangSmith or Arize Phoenix)

**Decision:** Use Langfuse self-hosted Docker Compose for all observability.

**Rationale:** LangSmith is cloud-only. Banking conversations contain income data, employment details, and partially-revealed PII (Aadhaar, PAN fragments). Sending these traces to a US cloud provider creates regulatory risk under Indian data protection laws. Langfuse self-hosted keeps all trace data within the bank's network perimeter.

Arize Phoenix was considered for RAG evaluation but its functionality is fully covered by Langfuse's LLM-as-judge evaluation feature, avoiding a second tool install.

## 2. ChromaDB (not FAISS)

**Decision:** Use ChromaDB persistent store for RAG vector search.

**Rationale:** ChromaDB provides persistent collections, metadata filtering, and a Python-native API — sufficient for the 5-document prototype. FAISS is faster at large scale but requires serialization management that adds complexity with no benefit at this scale. Migration path to FAISS (or pgvector) is documented in `retrieval/faiss_store.py`.

## 3. Two-Stage Safety Gate (keyword + LLM classifier)

**Decision:** Stage A = keyword blocklist (0 LLM tokens, <1ms), Stage B = GPT-4o-mini classifier (<50 tokens).

**Rationale:** A pure LLM classifier on every turn adds ~200ms and cost per message. The keyword filter catches 80%+ of adversarial probes (prompt injection, competitor queries) instantly. The LLM classifier handles the semantically ambiguous 20% at minimal cost. Dual-stage is described in `safety/guardrails.py`.

## 4. ReAct AgentExecutor over Plan-and-Execute

**Decision:** LangChain ReAct (reason + act) pattern via `create_react_agent`.

**Rationale:** Loan advisory is inherently sequential: collect profile → check eligibility → calculate EMI → list docs → optionally escalate. ReAct with a 10-iteration budget handles this naturally. Plan-and-Execute adds a separate planner LLM call and increases latency without improving correctness for this deterministic use case.

## 5. ConversationBufferWindowMemory (k=10)

**Decision:** Sliding window of 10 turns, not full history.

**Rationale:** A typical loan advisory session is 6–12 turns. Full history risks context overflow for longer sessions; k=10 retains sufficient context while keeping prompt tokens bounded.

## 6. MCP (Model Context Protocol) as Tool Transport Layer

**Decision:** Expose all 5 loan tools via FastMCP (`loan_mcp/server.py`) in addition to the existing LangChain `@tool` direct-import path. Agent selects the path via `USE_MCP=true`.

**Rationale:** MCP (Anthropic's open standard) separates tool *definition* from tool *consumption*. Without MCP, every client (LangChain agent, Claude Desktop, external bank systems) must import the Python modules directly — creating a tight coupling that breaks the moment the tool implementation moves to a different service or language. With MCP:

1. **External discoverability** — Claude Desktop and any MCP-capable client can call the 5 tools without Python imports. The server advertises tool names, descriptions, and JSON schemas automatically.
2. **Schema enforcement at the protocol layer** — FastMCP validates every incoming call against a Pydantic model derived from the tool's type annotations, before the Python function is even called. This catches bad inputs earlier and produces structured error messages.
3. **Additive, not disruptive** — the MCP layer wraps the existing `@tool` business logic rather than replacing it. The direct-import path (`USE_MCP=false`) remains available, so all 424 tests still pass (215 original + 11 MCP-specific + 182 new coverage tests + 16 RLHF adaptive tests).
4. **Future-proofing** — the bank's integration team can connect a core-banking system or RPA bot to `python scripts/start_mcp_server.py --transport http` without touching the LangChain agent code at all.

**Transport choices:**
- `stdio` (default) — subprocess pipe; ideal for Claude Desktop and local tool inspection.
- `streamable-http` (`--transport http`) — network-accessible; suitable for Docker deployments.

**Why FastMCP over low-level MCP SDK?** FastMCP auto-generates schemas from Python type hints, reducing boilerplate by ~80%. The low-level `mcp.server.lowlevel.Server` would require manual schema registration and request-routing for every tool.

**Trade-off acknowledged:** The MCP path adds one serialisation round-trip (Python dict → JSON text → Python dict) compared to the direct-import path. Measured overhead is under 1 ms in-process (thread-pool asyncio bridging) — negligible relative to LLM latency (~500–2000 ms per turn).

## 7. Two-Layer RLHF Adaptive Policy (not hardcoded rules)

**Decision:** Implement RLHF feedback adaptation in two independent layers — within-session `SystemMessage` injection and a cross-session LLM-generated `adaptive_policy.json` — rather than a fixed set of Python if/else adaptation rules.

**Rationale:** A fixed-rule approach (e.g. "if 5+ MSME sessions have low ratings, add a GST question") can only react to patterns the designer anticipated. Loan advisory failures are diverse: agents re-ask for information already given, give overly generic escalation responses, use jargon the customer does not understand. These patterns cannot all be enumerated at build time.

The two-layer design addresses this:

1. **Within-session correction** (`agent/core_agent.py::inject_feedback_signal`): A ≤2-star rating mid-session queues a correction as a `SystemMessage` injected before the next executor call. The agent sees it on the very next turn — no session restart, no LLM rebuild. A 4–5 star rating clears all pending corrections. This gives immediate, turn-level responsiveness to dissatisfied customers.

2. **Cross-session adaptive policy** (`policy_rlhf/policy_updater.py::update_adaptive_policy`): GPT-4o-mini reads the accumulated low-rated qualitative comments and generates novel behavioral instructions it thinks would address the pattern. These are written to `data/rlhf/adaptive_policy.json` as structured entries with `id`, `instruction`, `trigger_count`, and `source`. On next agent startup, `get_adapted_prompt()` prepends active entries to the base system prompt. The LLM can derive patterns that no static rule would capture.

**Why a separate JSON file instead of updating the system prompt in code?** Separating the *decision layer* (`adaptive_policy.json`) from the *evidence layer* (`feedback_store.json`) means: (a) bank operators can audit and manually add compliance rules (entries with `source: "manual"` are permanently protected from LLM overwrite); (b) the LLM pipeline can be re-run without touching any Python code; (c) rolling back a bad policy entry is a JSON edit, not a code deploy.

**Trade-off:** The `update_adaptive_policy()` call consumes a small number of LLM tokens per pipeline run (approximately 200–400 tokens at gpt-4o-mini rates). If the API is unavailable (budget exhausted), the function returns `{"status": "llm_unavailable"}` and the pipeline prints a clear message — the existing `adaptive_policy.json` is preserved untouched.
