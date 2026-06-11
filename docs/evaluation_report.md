# Evaluation Report

**Phase 9 deliverable** — populate after running `python scripts/run_evaluation.py --suite all`

## Test Sets

| Suite | Cases | Pass | Fail | Pass Rate |
|-------|-------|------|------|-----------|
| RAG quality (20Q) | 20 | TBD | TBD | TBD |
| Tool selection (30 scenarios) | 30 | TBD | TBD | TBD |
| Safety gate (5 adversarial) | 5 | TBD | TBD | TBD |
| **Total** | **55** | **TBD** | **TBD** | **TBD** |

## RAG Quality (Langfuse LLM-as-judge)

*Target: ≥ 70% pass rate*

<!-- Add Langfuse export link here after Phase 9 run -->

## Tool Selection Accuracy

| Tool | Correct Invocations | Total Scenarios | Accuracy |
|------|---------------------|-----------------|----------|
| check_eligibility | TBD | TBD | TBD |
| calculate_emi | TBD | TBD | TBD |
| get_document_checklist | TBD | TBD | TBD |
| lookup_loan_status | TBD | TBD | TBD |
| generate_escalation_summary | TBD | TBD | TBD |

## Failing Case Root Cause + Fix

*Pick one failing case, diagnose root cause, implement fix, re-run to confirm improvement.*

**Case ID:** TBD  
**Failure mode:** TBD  
**Root cause:** TBD  
**Fix applied:** TBD  
**Before score:** TBD → **After score:** TBD  

## Latency (P95)

*Target: < 5 seconds end-to-end*

| Turn type | P50 | P95 |
|-----------|-----|-----|
| Safety gate only | TBD ms | TBD ms |
| RAG query | TBD ms | TBD ms |
| Tool call (eligibility + EMI) | TBD ms | TBD ms |
| Full multi-tool | TBD ms | TBD ms |
