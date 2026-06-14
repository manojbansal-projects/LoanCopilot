# Agent Skills (Tools)

Five LangChain tools registered in `tools/tool_registry.py`.

| # | Tool name | File | Phase | Description |
|---|-----------|------|-------|-------------|
| 1 | `check_eligibility` | `tools/eligibility_checker.py` | Phase 5 | Rules-based FOIR + credit score + amount-limit check |
| 2 | `calculate_emi` | `tools/emi_calculator.py` | Phase 5 | Reducing-balance EMI formula |
| 3 | `get_document_checklist` | `tools/document_checklist.py` | Phase 5 | Product × employment-type lookup table |
| 4 | `query_loan_policy` | `tools/tool_search.py` | Phase 5 | RAG-backed policy FAQ over knowledge/raw/ |
| 5 | `generate_escalation_summary` | `tools/tool_escalate.py` | Phase 5 | Structured RM handoff packet |

## Tool invocation order (ReAct agent preferred sequence)

1. `check_eligibility` — always run first after profile is complete
2. `calculate_emi` — only if eligibility passes
3. `get_document_checklist` — after eligibility confirmed
4. `generate_escalation_summary` — when amount > advisory ceiling or eligibility is borderline
5. `query_loan_policy` — for FAQ / policy questions not covered by the above tools

## Adding a new tool

1. Create `tools/{tool_name}.py` with a `@tool` decorated function
2. Add the import to `tools/tool_registry.py::get_all_tools()`
3. Add a test case to `data/evaluation/test_cases.json`
4. Document the tool in this file
