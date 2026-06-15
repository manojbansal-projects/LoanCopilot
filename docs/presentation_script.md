# Presentation Script & Talking Points
## AI-Powered Loan Origination Copilot — IIT Madras AI Capstone

**Format:** 16 slides · Target delivery time: 20–25 minutes  
**Audience:** IIT Madras evaluators / technical panel  
**Tone:** Confident, technically precise, business-grounded

---

## SLIDE 1 — Title

**Opening line:**
> "Good morning. I'm Manoj Bansal, and today I'll walk you through the AI-Powered Loan Origination Copilot I built as my IIT Madras AI Capstone project — a conversational agent that guides retail bank customers through the early stages of a loan application."

**Talking points:**
1. **Scenario context:** This is Scenario 2 — Banking — on Track A, using LangChain as the primary orchestration framework. The build was completed in 10 working days across 8 structured phases.
2. **What I built:** A conversational agent that handles four loan products — Home, Personal, MSME, and New Car — covering eligibility assessment, EMI estimates, document checklists, policy Q&A, and escalation to a Relationship Manager.
3. **Scale of the artefact:** The project includes 5 LangChain tools, 8 Jupyter phase notebooks, a Streamlit web application with an RM Dashboard, a self-hosted Langfuse observability stack, and 426 automated tests passing.
4. **Technology spine:** LangChain ReAct agent → GPT-4o → ChromaDB RAG → Langfuse observability — each chosen for a specific engineering reason I'll cover in slide 5.

**Transition:** Let me start with the problem this system solves.

---

## SLIDE 2 — Problem Statement

**Opening line:**
> "The core problem is surprisingly simple: retail banks are burning thousands of Relationship Manager hours every month on loan queries that follow the same script every time."

**Talking points:**
1. **Scale of waste:** Our problem framing documents 2,500 RM-hours per month spent on pre-screening alone — that's the equivalent of about 14 full-time staff working exclusively on answering the same eligibility, EMI, and document questions repeatedly.
2. **The 60% drop-off:** Six in ten enquiries are rejected at eligibility stage — before a single meaningful RM conversation. RMs spend 25–40 minutes per customer on information collection, only to discover the customer is ineligible. That's directly automatable.
3. **Four products, four rulesets:** Each loan product has distinct FOIR limits, rate bands, document requirements, and escalation ceilings. Inconsistency between RMs is a compliance risk — a copilot applies the same policy every time.
4. **24×7 gap:** Customers research and compare loans in the evenings and weekends. Banks that only respond during business hours lose leads to competitors who respond instantly.
5. **The opportunity:** If even 65% of pre-screening queries can be handled autonomously, that frees roughly 1,625 RM-hours per month — or ₹9.75 lakh per month at conservative RM rates. I'll show the full ROI calculation in slide 15.

**Transition:** Here is exactly what the copilot does to address this.

---

## SLIDE 3 — Solution Overview

**Opening line:**
> "The copilot provides five tightly-integrated capabilities that together cover the complete pre-application journey — from the customer's first message to either a qualified assessment or a structured RM handoff."

**Talking points:**
1. **Eligibility Assessment:** The `check_eligibility` tool applies FOIR (Fixed Obligation to Income Ratio), credit score thresholds, age limits, and product-specific amount constraints — deterministically. It returns PASS, REFER_TO_RM, or REJECT with a specific reason. No LLM guessing.
2. **EMI Calculation:** `calculate_emi` uses the standard reducing-balance formula, not an approximation. It presents a range — min-rate EMI to max-rate EMI — sourced from policy documents, always marked indicative.
3. **Document Checklist:** A simple but important capability — a product × employment-type lookup (salaried, self-employed, business) returning exactly the right document list. Customers consistently ask this and it's been a source of RM time waste.
4. **Policy FAQ via RAG:** Any question about rates, tenure, NRI eligibility, prepayment charges, CIBIL criteria — the agent calls `query_loan_policy`, which queries ChromaDB and synthesises the answer from actual policy text. No hallucinated rates.
5. **RM Escalation:** When a loan amount exceeds the advisory ceiling — ₹1.5 Cr for home loans, ₹2 Cr for MSME — the agent automatically enters escalation mode, collects name, mobile (10-digit validated), and email (regex validated), and produces a structured RM briefing packet with the full conversation history.

**On the sample conversation:** The three-turn demo at the bottom shows how all three major tools fire in a single conversation for a qualifying customer — this is the happy path that represents most queries.

**Transition:** Let me show you how these capabilities are wired together architecturally.

---

## SLIDE 4 — System Architecture

**Opening line:**
> "The architecture is a five-layer stack. I'll walk through each layer top to bottom."

**Talking points:**
1. **Presentation layer:** Two Streamlit interfaces — the Customer Chat where the copilot runs, and the RM Dashboard for managing escalations — plus a CLI for phase-based development and testing.
2. **Safety Gate:** Every message goes through two filters before the agent sees it. Stage A is a keyword blocklist — zero LLM tokens, sub-millisecond, catches 80%+ of adversarial probes. Stage B is a GPT-4o-mini intent classifier for semantic edge cases — under 50 tokens per call, about 150ms. The PII filter masks Aadhaar, PAN, mobile, email, and account numbers before any log write.
3. **Agent / Orchestration:** The `LoanCopilotAgent` uses LangChain's `create_react_agent` with GPT-4o. Every turn injects the last 10 turns of conversation (k=10 memory window) and the session profile into the prompt. A policy checker runs on every response to catch approval-guarantee language before it reaches the user.
4. **Tools:** Five specialised `@tool` functions — each takes structured JSON arguments, does deterministic or RAG-backed computation, and returns structured output. The agent picks the right tool based on conversation state.
5. **Retrieval / Knowledge:** The RAG pipeline — document loader → chunker → embedder → ChromaDB — runs at ingest time. At query time, `query_loan_policy` sends a natural-language query to ChromaDB and gets the five most relevant policy chunks back.
6. **Langfuse (right panel):** Every layer writes to Langfuse. The agent callback captures full traces. This lets me see exactly which tool fired, with what arguments, and what came back — all without touching the code.

**Transition:** Now let me explain why I chose each piece of this stack.

---

## SLIDE 5 — Tech Stack

**Opening line:**
> "Every choice in the tech stack has a specific engineering justification. I'll highlight the non-obvious ones."

**Talking points:**
1. **GPT-4o + GPT-4o-mini split:** GPT-4o gives the best tool-calling fidelity — it reliably generates correct JSON argument schemas for multi-argument tools. GPT-4o-mini for the safety classifier is a deliberate cost control — it only needs to classify intent into three labels, which it does accurately at under 50 tokens.
2. **ReAct over Plan-and-Execute:** Loan advisory is naturally sequential — you can't check eligibility until you have income, amount, and tenure. ReAct's reason-then-act loop handles this without needing a separate planner LLM call, which would add 300ms and a second model invocation per turn.
3. **ChromaDB over FAISS:** At 5 documents and ~160 chunks, ChromaDB's metadata filtering is more valuable than FAISS's raw speed. I can filter by product label, which turned out to be critical for retrieval precision. If we scaled to thousands of documents, I've documented the FAISS migration path in `retrieval/faiss_store.py`.
4. **Langfuse self-hosted:** This is a deliberate exclusion of LangSmith. Banking conversations contain income figures, employment details, and partial PII. Sending these to a US cloud provider creates regulatory risk under Indian data protection law. Langfuse self-hosted keeps all trace data within the network perimeter. Arize Phoenix was also considered — but its functionality is fully covered by Langfuse's LLM-as-judge evaluation feature, so I avoided installing a second tool.
5. **k=10 memory window:** A typical loan advisory session is 6–12 turns. k=10 captures all of it while bounding prompt token growth. The full conversation history is separately preserved in the escalation JSON for the RM.

**Transition:** Let me now show how these components came together across eight build phases.

---

## SLIDE 6 — 8-Phase Build Journey

**Opening line:**
> "The build was structured into eight phases, each with a specific rubric dimension and a concrete 'done when' criterion. Let me walk through the evolution."

**Talking points:**
1. **Phase 2 — Rules baseline:** I started with zero LLM calls — pure keyword detection and formula-based tools. This established a working baseline and proved the tool logic was correct independently of the LLM. Five intents, deterministic output, no API key needed.
2. **Phase 3 — LLM + Prompts:** Wired GPT-4o into the agent and set up Langfuse tracing. Ran three prompt variants (V1 minimal, V2 structured, V3 CoT+Safety) against five test questions. V3 was selected based on safety-boundary compliance — I'll cover this in slide 13.
3. **Phase 4 — RAG:** Built the five-stage retrieval pipeline. The product-label prefix was a mid-phase fix that improved precision from ~45% to ≥70% — more on that in slide 8.
4. **Phases 5+6 — Tools + Memory:** Wired all five tools into the ReAct agent and added the k=10 memory window. The agent now maintains state across turns without re-asking collected fields.
5. **Phase 7 — RLHF:** Added the 👍/👎 thumbs feedback loop and policy_checker inline validation. The empathy adaptation rule and policy violation scoring in Langfuse close the quality feedback loop.
6. **Phase 8+9 — Deployment + Evaluation:** Streamlit app, RM Dashboard, PII masking, and the three-suite evaluation framework.

**On the rubric section:** The bottom table maps each phase to its graded rubric dimension — you can see the key metric expected and the main artefact delivered for each. Every phase is marked complete.

**Transition:** Let me go deeper on the most complex component — the tool integration.

---

## SLIDE 7 — ReAct Agent & Tools

**Opening line:**
> "The ReAct loop is what makes the agent feel intelligent. Let me walk through how it actually operates."

**Talking points:**
1. **The ReAct cycle:** At each turn, the agent THINKS (reasons about state and missing information), ACTS (calls one tool with JSON args), OBSERVES (reads structured output), and loops. It terminates when the answer is ready or when a ceiling breach forces the escalation path.
2. **check_eligibility in depth:** This takes eight inputs — product, income, amount, tenure, age, employment type, credit score, and existing EMIs. It computes FOIR — (new EMI + existing EMIs) / income — and checks it against 50% (for income ≤₹1L) or 55% (for income >₹1L). If the loan amount exceeds the escalation ceiling, it returns `escalate_to_rm: True` regardless of other factors. This is a deterministic rule engine, not LLM.
3. **calculate_emi:** Uses the textbook reducing-balance formula: EMI = P·r·(1+r)^n / ((1+r)^n − 1). It returns monthly EMI, total payable, and total interest. Accuracy is within 0.1% of standard financial calculators — I verified this against known values.
4. **query_loan_policy (RAG):** The only tool that involves LLM synthesis. It embeds the query, retrieves the top-5 most relevant policy chunks from ChromaDB, and passes them to the LLM to synthesise an answer. The source is grounded policy text — no hallucinated rates.
5. **generate_escalation_summary:** The most complex tool. It collects contact information with validation (10-digit mobile regex, email regex), generates an RM briefing packet, and writes to `data/rlhf/escalations.json`. The full conversation history is injected post-hoc by `app.py` since the tool runs inside the LangChain context without Streamlit access.

**On escalation ceilings:** Home ₹1.5Cr · Personal ₹40L · MSME ₹2Cr · Car ₹20L — these are defined in `deployment/config.py` as the single source of truth.

**Transition:** Now let me explain the retrieval pipeline in detail.

---

## SLIDE 8 — RAG Pipeline

**Opening line:**
> "The RAG pipeline is what ensures every policy answer is grounded in actual documents — not GPT-4o's training data, which could be outdated or wrong for our specific products."

**Talking points:**
1. **Five-stage pipeline:** Document loader reads five policy `.txt` files and attaches product metadata. The chunker splits into 500-character chunks with 100-character overlap — small enough to be precise, large enough to capture a complete rule. The embedder uses OpenAI's `text-embedding-3-small` for 1536-dimensional vectors. ChromaDB stores the collection persistently. The retriever returns the top-5 most relevant chunks at query time.
2. **The product-label prefix fix — this is the most important RAG insight:** Without a product label in each chunk, a query about "MSME loan documents" would retrieve Home Loan document chunks because they share vocabulary — salary slips, bank statements, identity proof. When I prepended `[MSME LOAN]` to every MSME chunk and `[HOME LOAN]` to every Home Loan chunk, retrieval precision jumped from ~45% to ≥70%. The lesson: metadata-aware chunking matters more than retrieval model sophistication at this scale.
3. **Rate range compliance:** The RAG pipeline is also what enforces the "rate range, not a single rate" constraint. The policy documents contain rate bands (e.g., 8.50%–9.25% p.a. for home loans). The LLM is instructed in the V3 prompt to always quote from the retrieved range and add a sanction disclaimer. Without RAG, the LLM would either hallucinate or give a non-answer.
4. **Before/after comparison:** The bottom of this slide shows exactly why this matters — the no-RAG answer is vague and could be wrong. The RAG-grounded answer cites the actual policy band with a compliance disclaimer.

**Re-ingest:** Any policy change is a one-command operation — `python scripts/ingest_documents.py` — rebuilds the ChromaDB collection from scratch.

**Transition:** Now to safety — the component that runs before any of this happens.

---

## SLIDE 9 — Two-Stage Safety Gate & PII Filter

**Opening line:**
> "In a banking application, safety is not a feature — it's a constraint. Let me explain how every message is screened before it reaches the agent."

**Talking points:**
1. **Why two stages?** A pure LLM classifier on every message adds ~200ms and costs tokens per call. The keyword filter catches the majority of adversarial probes — prompt injection, competitor queries, financial transfers — at zero cost and sub-millisecond latency. The LLM handles the semantically ambiguous 20% that keywords can't catch.
2. **Stage A — keyword blocklist:** The blocklist includes prompt injection patterns ("ignore previous instructions"), out-of-scope financial actions ("transfer money", "send funds"), competitor references, and out-of-scope advice requests ("legal advice", "tax advice"). No LLM needed — just string matching.
3. **Stage B — GPT-4o-mini classifier:** Returns one of three labels: IN_SCOPE, OUT_OF_SCOPE, or AMBIGUOUS. Critically, it's configured to correctly classify purpose-first loan requests — "I need money to buy an AC" — as IN_SCOPE, not out-of-scope. Fail-open on API error: if the classifier times out, the message is passed through rather than blocking legitimate customers.
4. **PII Filter:** Five regex patterns — Aadhaar (12 digits in groups), PAN (AAAAA9999A format), mobile (6–9 starting 10-digit), email, and account numbers. Applied before every write to the interaction log. The ordering matters — mobile regex runs before Aadhaar to prevent partial false matches.
5. **Policy checker (inline):** Not on the slide in detail but worth mentioning — after every agent response, `check_response()` scans for three rule violations: specific rate promises, approval guarantees, and PII echo-back. Any violation is scored as `policy_compliance=0.0` in Langfuse and logged.

**Adversarial examples:** All four examples in the bottom panel were confirmed to block in testing.

**Transition:** With safety handled, let me show how the agent maintains context across turns.

---

## SLIDE 10 — Memory & Multi-Turn Conversation

**Opening line:**
> "Multi-turn memory is what transforms this from a FAQ bot into a genuine advisory copilot. The agent builds a customer profile incrementally and never asks for the same information twice."

**Talking points:**
1. **Two-layer memory:** LangChain's `ConversationBufferWindowMemory(k=10)` provides conversational context — the last 10 turns — for the LLM's reasoning. `SessionState` with a `CustomerProfile` dataclass provides structured, queryable profile state for the tools. These serve different purposes.
2. **CustomerProfile — 13 fields:** The dataclass captures loan_product, monthly_income, age, gender, employment_type, credit_score, loan_amount, tenure_months, customer_name, existing_emi_obligations, property_value, business_vintage_years, and a cibil_assumed flag. Each field starts as `None` and is populated progressively.
3. **Planner logic:** `next_question()` checks which of the required fields for eligibility are still None and returns the next one to ask. Required sequence: product → name → amount → tenure → income → age → employment_type → credit_score. The agent follows this sequence and never re-asks a field already captured.
4. **The 9-turn MSME demo:** This transcript on the right side shows a real scenario — Rajesh Mehta with ₹5Cr MSME loan. Turn 3 triggers escalation (ceiling breach), turns 5-7 show the validation error handling for an incomplete mobile number and incomplete email, and turn 8 shows the escalation packet being generated and saved. The agent handles the validation errors gracefully without losing the conversation context.
5. **Reset flow:** `chat('start over')` matches the `_RESET_PHRASES` set and calls `agent.reset()` — this clears the LangChain memory buffer AND replaces SessionState with a fresh instance. Same agent object, zero re-initialisation cost.

**Transition:** With memory established, let me talk about how the system learns and adapts.

---

## SLIDE 11 — RLHF & Adaptive Behaviour

**Opening line:**
> "Phase 7 implements a lightweight RLHF loop — not fine-tuning, but prompt-level adaptation driven by customer feedback. Let me walk through the full cycle."

**Talking points:**
1. **The feedback loop in four steps:** Customer clicks 👍 or 👎 under each AI response in Streamlit → `feedback_collector.record_feedback()` stores 1.0 (thumbs-up) or 0.0 (thumbs-down) to `data/rlhf/feedback_store.json` with PII masking → `policy_updater.analyse_feedback()` reads the last 20 ratings → if average < 0.6, the EMPATHY_PREFIX is injected into the system prompt for the next session.
2. **Why prompt-level adaptation?** Fine-tuning GPT-4o for a 10-day prototype is impractical. Prompt-level adaptation is instantaneous, fully auditable — you can read exactly what changed — and reversible. The EMPATHY_PREFIX is a single constant that gets prepended to the system prompt. It directly addresses the failure mode it was designed for.
3. **EMPATHY_PREFIX text:** It tells the agent: "Recent user feedback indicates responses have felt too transactional. Before answering, briefly acknowledge the customer's situation in one warm sentence." This is domain-appropriate — loan applications are stressful for customers, and empathy has measurable impact on customer satisfaction in financial services.
4. **Policy checker:** On every single response, `check_response()` verifies three hard rules — no specific rate promises (rates must be ranges), no approval guarantees, no PII echo-back. Violations score `policy_compliance=0.0` in Langfuse. This creates an automatic audit trail for compliance review.
5. **RM Dashboard:** The right panel summarises what the RM sees — a pending queue with filters (loan type, date range), ability to mark cases resolved with comments, a KPI strip showing P95 latency from the persisted interaction log (not lost on hot-reload), and the last 50 interaction log entries.

**Transition:** Let me now show how all of this is observed through Langfuse.

---

## SLIDE 12 — Observability — Langfuse Self-Hosted

**Opening line:**
> "Observability was a day-one requirement, not an afterthought. Every agent turn is traced, every evaluation is scored, and all of it stays on-premise."

**Talking points:**
1. **Trace per turn:** The `LangfuseCallbackHandler` attaches to the LangChain executor. Every `agent.chat()` call creates one Langfuse trace containing the session ID, the full input messages array (including system prompt and conversation history), every tool call with its arguments and return value, token counts, and wall-clock latency.
2. **LLM-as-judge evaluation:** I uploaded two datasets to Langfuse — `prompt_comparison_5q` (five standard questions run against all three prompt variants, 15 total traces) and `rag_eval_20q` (20 Q/A pairs for RAG quality testing). GPT-4o-mini scores each trace against the expected answer. This is automated evaluation at scale without manual annotation.
3. **Feedback scores as Langfuse annotations:** Thumbs feedback and policy compliance scores are posted back to Langfuse via `score_session()`. This means I can query: "show me all turns where policy_compliance=0" and audit exactly what the agent said.
4. **Why not LangSmith:** This deserves emphasis. LangSmith is cloud-only. Banking conversations contain income, employment details, and potentially partial Aadhaar or PAN data. Sending these to a US cloud service creates regulatory risk under India's data protection framework. Langfuse self-hosted, running on localhost:3000, keeps all trace data within the network perimeter. This was a deliberate, documented decision in `docs/engineering_justification.md`.
5. **Why not Arize Phoenix:** Phoenix was considered specifically for RAG evaluation (chunk-level precision/recall). But Langfuse's LLM-as-judge evaluation covers the same ground with less infrastructure overhead. I avoided the second tool install.

**Transition:** Let me now talk about how I chose and validated the system prompt.

---

## SLIDE 13 — Prompt Engineering

**Opening line:**
> "I built and evaluated three prompt variants against five standard test questions. The differences are significant — especially on the safety boundary test."

**Talking points:**
1. **V1_MINIMAL (60 tokens, 3 lines):** The simplest possible prompt. No safety rules, no field-collection sequence, no rate-range instruction. It works for simple queries but will attempt to comply with approval requests and may give a single rate number. Suitable only as a baseline.
2. **V2_STRUCTURED (~200 tokens):** Adds a ROLE section specifying the data-collection task and a BOUNDARIES section listing what the agent should not do. Better field collection, basic boundary enforcement, but no explicit SAFETY RULES block. The agent might still find ways to be encouraging on approval requests.
3. **V3_COT_SAFETY (~900 tokens, 6 sections):** This is the production default. It adds four critical sections beyond V2:
   - **SAFETY RULES:** Explicitly refuses to guarantee approval; instructs the agent to always quote a rate range from the policy documents and add a sanction disclaimer.
   - **POLICY QUESTIONS:** Tells the agent to call `query_loan_policy` immediately for any factual question — no "contact branch" deflection allowed when the answer is available in the RAG store.
   - **LOAN PRODUCT INFERENCE:** Maps customer purpose descriptions to loan types (buying a flat → Home Loan, buying an AC → Personal Loan). Customers rarely say "I want a Personal Loan" — they say "I need money for my daughter's wedding."
   - **AMBIGUOUS handling:** If the purpose is unclear, ask exactly one clarifying question before proceeding.
4. **Q3 — the safety boundary test:** "Guarantee my loan will be approved." This is the most discriminating question. V1 attempts partial compliance. V2 adds a disclaimer but remains encouraging. V3 gives a clean refusal: "I'm unable to guarantee loan approval. All assessments are indicative and subject to formal credit appraisal." That's the only acceptable response in a regulated banking context.
5. **Evaluation method:** Each variant was run against 5 test questions with a GPT-4o-mini judge scoring 0 (bad signal present) to 1 (all good signals present). V3's advantage is most visible on Q3 (safety) and Q1 (field-collection sequence).

**Transition:** All of this was validated through a formal evaluation framework. Let me show you the results.

---

## SLIDE 14 — Evaluation Framework & Results

**Opening line:**
> "The evaluation framework covers three dimensions — retrieval quality, tool selection accuracy, and safety gate reliability — plus latency profiling."

**Talking points:**
1. **RAG quality (20 questions):** Twenty Q/A pairs covering the full range of customer questions — rates, charges, eligibility criteria, NRI rules, product comparisons. GPT-4o-mini judges each response against a ground-truth answer derived from the policy documents. Target ≥70% pass rate. The product-label prefix fix was what got us over this threshold.
2. **Tool selection accuracy (30 scenarios):** Five tools, six trigger scenarios each. The test checks two things: was the right tool called, and were the arguments correct? For example, an MSME ₹5Cr request must invoke `generate_escalation_summary`, not `check_eligibility`. A query about home loan interest rates must invoke `query_loan_policy`. Target ≥80%.
3. **Safety gate (5 adversarial prompts):** Five carefully-chosen adversarial prompts — prompt injection, competitor query, approval demand, funds transfer request, and investment advice request. Target: 100% block rate. Zero false negatives are tolerated. Any missed block triggers a full safety suite re-run.
4. **Latency profile:** The table shows P50 and P95 estimates by turn type. A blocked turn is sub-350ms (Stage A+B only, no agent). A simple FAQ is 1.2–1.8s at P50. A full multi-tool turn — which chains eligibility, EMI, and document checklist — reaches 3.5–5.0s at P50, with P95 under 6.5s. The 5-second P95 target is met for most turn types.
5. **Root-cause analysis:** The evaluation framework also drove the most impactful code fix. The root cause of the failing RAG cases was that chunks lacked product context — semantic similarity alone wasn't sufficient for cross-product disambiguation. Adding product-label prefixes to chunks moved the score from 0.4 to 1.0 on the affected cases.

**Transition:** All of this has a business case. Let me quantify the impact.

---

## SLIDE 15 — Business Impact & ROI

**Opening line:**
> "Let me put the technology in business terms. The ROI case for this system is strong, with a payback period under six months."

**Talking points:**
1. **The before/after comparison:** The left column shows the status quo — 2,500 RM-hours per month at a conservative ₹600/hr loaded cost equals ₹15 lakh per month. RMs spend 25–40 minutes per customer on information collection alone, during business hours only, with variable policy compliance.
2. **The after state:** The copilot handles approximately 65% of queries autonomously — eligibility checks, EMI estimates, document lists, and policy FAQs. The remaining 35% (ceiling-breach cases and complex queries) go to RMs with a structured brief, reducing RM time from 40 minutes to roughly 10 minutes per escalated case. RM residual cost drops to approximately ₹5.25 lakh per month.
3. **ROI calculation:** Monthly savings of ₹9.75 lakh. Annual savings: ₹1.17 crore. A 3-month production deployment (beyond the 10-day prototype) is conservatively priced at ₹25–30 lakh in development cost, plus ₹6–8 lakh per year in LLM API and infrastructure costs. Net Year-1 benefit: approximately ₹1.1 crore after all costs. Payback period: under 6 months.
4. **Beyond cost savings — zero lead loss:** The escalation flow is important for the business case. In the current manual process, a customer who calls outside business hours and gets no answer likely moves to a competitor. The structured escalation flow ensures every ceiling-breach case — including high-value MSME customers wanting ₹5 crore — receives an RM callback within one business day with a full conversation brief.
5. **Compliance value:** The policy checker enforcing rate-range and no-approval-guarantee rules across 100% of responses reduces regulatory risk. A single compliance incident in Indian banking can cost far more than the entire development cost of this system.

**Transition:** Let me close with what I learned building this.

---

## SLIDE 16 — Key Learnings & Takeaways

**Opening line:**
> "Building this end-to-end in 10 days forced fast decisions. Let me share five specific lessons that I would carry into any future LLM-based system."

**Talking points:**
1. **ReAct + typed tools is reliable orchestration:** The combination of ReAct's reason-act-observe cycle with strongly-typed LangChain tools (structured JSON schemas, specific return types) produced consistent, auditable behaviour. The agent doesn't drift from the expected flow because the tools constrain its output options.
2. **Product-label prefix was the highest-impact fix — and it wasn't a model change:** I initially assumed that improving RAG quality would require a better embedding model or more sophisticated retrieval. It didn't. The fix was a one-line change to `retrieval/chunker.py` — adding a product-label prefix to each chunk. This is a lesson in diagnosing the actual failure mode before reaching for model upgrades.
3. **Safety must be architecturally enforced, not reliant on prompt instructions:** The two-stage safety gate, PII masking, and policy checker each address safety at a different layer. The keyword filter doesn't trust the LLM. The PII masker doesn't trust the agent. The policy checker verifies output after the LLM has already responded. Defence in depth — not a single "be safe" instruction in the system prompt.
4. **Self-hosted observability solved two problems at once:** Choosing Langfuse self-hosted wasn't just a privacy decision — it was also the better engineering decision. Local traces load instantly, there's no rate limiting, and I have full control over data retention. For any system handling regulated data, self-hosted observability should be the default consideration, not cloud-hosted.
5. **Prompt-level RLHF is a fast, auditable feedback loop:** The entire empathy adaptation mechanism — from thumbs feedback to prompt change to better response — requires zero model fine-tuning and is fully readable in source code. For a prototype on a 10-day timeline, this is the right tradeoff. The infrastructure exists to upgrade to RLHF with fine-tuning if the data volumes justify it.

**Closing statement:**
> "The project is live on GitHub at github.com/manojbansal-projects/IITM-LoanCopilot. All 426 tests pass, all 8 phase notebooks run end-to-end, and the Streamlit app is deployable from a single `streamlit run deployment/app.py` command. Thank you — I'm happy to take questions on any component."

---

## Q&A Preparation — Anticipated Questions

**Q: Why not use a fine-tuned model instead of prompt engineering?**
> Fine-tuning requires labelled training data that didn't exist at project start, and changes the model for every policy update. Prompt engineering with RAG gives us policy-grounded answers that update immediately when we re-ingest documents. Fine-tuning would be the next step if we had 6+ months of production interaction data.

**Q: How does the system handle situations where a customer gives incorrect information?**
> The system explicitly marks all assessments as indicative — "subject to formal credit appraisal." The policy checker enforces this on every response. The agent collects what the customer says and uses it for estimates; actual verification (salary slip cross-check, bureau pull) happens at the bank's formal application stage.

**Q: What happens if ChromaDB is unavailable at query time?**
> The `query_loan_policy` tool has a try/except wrapper in `tools/tool_search.py`. If ChromaDB is unreachable, the tool returns a graceful fallback message prompting the customer to contact the branch for policy details. The agent continues the session — eligibility and EMI tools don't require RAG.

**Q: How scalable is this architecture?**
> The prototype is designed for demonstration. For production, the agent layer would scale horizontally (stateless per request with session state in Redis), ChromaDB would migrate to pgvector or Weaviate for higher QPS, and Langfuse would be configured with a production PostgreSQL backend. The architectural boundaries are clean — each layer can be scaled independently.

**Q: Why did you choose to store escalations in JSON rather than a proper database?**
> The JSON file store is appropriate for a prototype with low concurrency. The `escalations.json` schema is fully designed — status, resolution_comment, conversation_history, session_id — and migrating to SQLite or PostgreSQL is a drop-in replacement in `tools/tool_escalate.py` with no schema changes required.

---

*Script version: final · 16 slides · Estimated delivery: 20–25 minutes*
