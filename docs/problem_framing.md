# Problem Framing

> Full narrative: `docs/concept_document.docx` Section 2

## Business Problem
Indian retail bank loan enquiries generate 2,500 RM-hours/month of repetitive pre-screening work. 60% of queries are rejected at eligibility stage; RMs spend 25–40 minutes per customer on information collection that could be automated.

## AI Opportunity
A conversational copilot can handle early-stage origination (eligibility estimate, EMI calculation, document checklist, FAQ) at scale — freeing RMs for relationship-intensive cases.

## Scope (Prototype)
- **In:** 4 loan products — Home, Personal, MSME, New Car
- **In:** Single-turn and multi-turn advisory conversations (English)
- **Out:** Actual credit decision, KYC verification, loan disbursement
- **Out:** Localization, regional languages (future phase)

## Success Metrics
| Metric | Target |
|--------|--------|
| Eligibility assessment accuracy | ≥ 85% (vs RM judgement) |
| EMI calculation accuracy | ± 1% vs reducing-balance formula |
| Safety gate block rate on 5 adversarial prompts | 100% |
| RAG answer quality (Langfuse LLM-as-judge) | ≥ 70% pass on 20Q set |
| P95 end-to-end latency | < 5 seconds |

## Grounding
All policy claims are grounded in `knowledge/raw/` documents embedded in ChromaDB. No hallucinated rates or rules.
