"""Unit tests for tools/tool_search.py (query_loan_policy).

The retriever is mocked so tests run without requiring ChromaDB to be built.
Integration-level retrieval accuracy is covered by the evaluation suite
(scripts/run_evaluation.py --suite rag).
"""
from __future__ import annotations
import sys
import pytest
from unittest.mock import patch, MagicMock
from langchain_core.documents import Document


# ── Helpers ────────────────────────────────────────────────────────────────────

def _doc(text: str, source: str = "home_loan_policy") -> Document:
    d = Document(page_content=text)
    d.metadata = {"source": source}
    return d


def _call(query: str, docs: list[Document]) -> str:
    """Call query_loan_policy with a mocked retriever.

    Injects a fake retrieval.retriever module into sys.modules so that the
    local `from retrieval.retriever import retrieve` inside query_loan_policy
    picks up our stub without needing ChromaDB installed.
    """
    from tools.tool_search import query_loan_policy
    mock_mod = MagicMock()
    mock_mod.retrieve.return_value = docs
    with patch.dict(sys.modules, {"retrieval.retriever": mock_mod}):
        return query_loan_policy.invoke({"query": query})


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestQueryLoanPolicyRetrieval:
    def test_returns_string(self):
        docs = [_doc("Home loan rate: 8.50% to 9.50% p.a.")]
        result = _call("what is the home loan interest rate?", docs)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_returns_document_content(self):
        docs = [_doc("Processing fee is 0.5% of loan amount.")]
        result = _call("processing fee?", docs)
        assert "0.5%" in result

    def test_returns_up_to_three_docs(self):
        docs = [_doc(f"chunk {i}") for i in range(5)]
        result = _call("any policy question", docs)
        # Only the first 3 chunks should appear (tool returns docs[:3])
        assert "chunk 0" in result
        assert "chunk 1" in result
        assert "chunk 2" in result
        assert "chunk 3" not in result
        assert "chunk 4" not in result

    def test_multiple_chunks_joined_with_newlines(self):
        docs = [_doc("Rate is 9%."), _doc("Fee is 1%.")]
        result = _call("rate and fee?", docs)
        assert "Rate is 9%." in result
        assert "Fee is 1%." in result

    def test_fallback_when_no_docs_returned(self):
        """Empty retriever result → fallback message, not a crash."""
        result = _call("obscure question with no matching policy", [])
        assert isinstance(result, str)
        assert len(result) > 0
        # Must advise customer to contact branch
        assert "branch" in result.lower() or "contact" in result.lower()

    def test_query_is_passed_to_retriever(self):
        """The exact query string must be forwarded to retrieve()."""
        from tools.tool_search import query_loan_policy
        captured = {}
        def fake_retrieve(q, **kwargs):
            captured["q"] = q
            return [_doc("some policy text")]
        mock_mod = MagicMock()
        mock_mod.retrieve.side_effect = fake_retrieve
        with patch.dict(sys.modules, {"retrieval.retriever": mock_mod}):
            query_loan_policy.invoke({"query": "NRI home loan eligibility"})
        assert captured["q"] == "NRI home loan eligibility"

    def test_single_document_source_preserved(self):
        """Tool should not crash when a single document is returned."""
        docs = [_doc("Minimum CIBIL score is 700 for Home Loan.", source="home_loan_policy")]
        result = _call("minimum cibil score", docs)
        assert "700" in result

    def test_tool_has_description(self):
        from tools.tool_search import query_loan_policy
        assert query_loan_policy.description
        assert len(query_loan_policy.description) > 10

    def test_tool_name(self):
        from tools.tool_search import query_loan_policy
        assert query_loan_policy.name == "query_loan_policy"
