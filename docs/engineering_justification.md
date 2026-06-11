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
