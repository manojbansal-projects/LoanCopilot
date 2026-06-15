"""
Tests for the Loan Copilot MCP server (loan_mcp/server.py).

Uses the in-process FastMCP `mcp.call_tool()` and `mcp._tool_manager.list_tools()`
APIs to exercise the full MCP schema-validation and serialisation path without
spawning a subprocess or dealing with cross-task cancel-scope issues.

Test coverage:
  - Server registers exactly 5 tools with the correct names
  - Required vs optional parameter counts match tool signatures
  - calculate_emi produces a result within ₹5 of the expected ₹26,992
  - check_eligibility returns eligible=True for a clear-pass profile
  - check_eligibility detects low CIBIL (ineligible) and ceiling breach (escalate)
  - get_document_checklist returns non-empty doc lists
  - generate_escalation_summary rejects a bad mobile number (validation path)
  - get_mcp_tools() builds 5 valid LangChain StructuredTools
  - LangChain StructuredTool (MCP path) calls produce correct results
"""
from __future__ import annotations

import asyncio
import json
import sys
import pytest
from unittest.mock import patch, MagicMock


# ── Helper: run async against the in-process FastMCP server ──────────────────

def _call(tool_name: str, arguments: dict) -> dict | str:
    """Call a tool via in-process FastMCP and return the parsed result."""
    from loan_mcp.server import mcp

    async def _inner():
        contents = await mcp.call_tool(tool_name, arguments)
        # FastMCP returns (unstructured_list, structured_dict) for str-annotated tools;
        # plain list[TextContent] for dict-returning tools.
        if isinstance(contents, tuple):
            content_list, _ = contents
        else:
            content_list = contents
        text = content_list[0].text
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return text

    return asyncio.run(_inner())


# ── 1. Tool registration ──────────────────────────────────────────────────────

def test_server_lists_exactly_five_tools():
    from loan_mcp.server import mcp

    tools = mcp._tool_manager.list_tools()
    names = {t.name for t in tools}
    assert names == {
        "check_eligibility",
        "calculate_emi",
        "get_document_checklist",
        "query_loan_policy",
        "generate_escalation_summary",
    }, f"Unexpected tool set: {names}"


def test_tool_schemas_have_correct_required_params():
    from loan_mcp.server import mcp

    schema_map = {t.name: t.parameters for t in mcp._tool_manager.list_tools()}

    assert set(schema_map["calculate_emi"]["required"]) == {
        "principal", "annual_rate_percent", "tenure_months"
    }
    assert set(schema_map["get_document_checklist"]["required"]) == {
        "loan_product", "employment_type"
    }
    assert "query" in schema_map["query_loan_policy"]["required"]

    elig_required = set(schema_map["check_eligibility"]["required"])
    assert elig_required == {
        "loan_product", "monthly_income", "loan_amount",
        "tenure_months", "age", "employment_type",
    }
    # optional params exist but are not required
    elig_props = set(schema_map["check_eligibility"]["properties"].keys())
    assert "credit_score" in elig_props - elig_required
    assert "existing_emi_obligations" in elig_props - elig_required

    esc_required = set(schema_map["generate_escalation_summary"]["required"])
    assert esc_required == {
        "customer_intent", "loan_product", "loan_amount",
        "monthly_income", "escalation_reason",
    }
    # 12 optional contact / context params
    esc_optional = (
        set(schema_map["generate_escalation_summary"]["properties"].keys())
        - esc_required
    )
    assert len(esc_optional) == 12


# ── 2. calculate_emi — reducing-balance correctness ──────────────────────────

def test_calculate_emi_30L_9pct_240mo():
    """₹30L × 9% × 240 months = ₹26,992 (± ₹5)."""
    data = _call("calculate_emi", {
        "principal": 3_000_000.0,
        "annual_rate_percent": 9.0,
        "tenure_months": 240,
    })
    assert isinstance(data, dict)
    assert abs(data["emi"] - 26_992) < 5, f"EMI {data['emi']} too far from 26,992"
    assert data["total_interest"] > 0
    assert data["total_payable"] > data["principal"]


# ── 3. check_eligibility ─────────────────────────────────────────────────────

def test_check_eligibility_eligible_profile():
    """Salaried, ₹1.2L/mo, ₹50L home loan, 240 mo, CIBIL 750 → eligible."""
    data = _call("check_eligibility", {
        "loan_product": "home_loan",
        "monthly_income": 120_000.0,
        "loan_amount": 5_000_000.0,
        "tenure_months": 240,
        "age": 35,
        "employment_type": "salaried",
        "credit_score": 750,
    })
    assert data["eligible"] is True
    assert "foir" in data
    assert data["foir"] < 0.56


def test_check_eligibility_ineligible_low_cibil():
    """CIBIL 580 → not eligible for personal loan."""
    data = _call("check_eligibility", {
        "loan_product": "personal_loan",
        "monthly_income": 80_000.0,
        "loan_amount": 1_000_000.0,
        "tenure_months": 60,
        "age": 30,
        "employment_type": "salaried",
        "credit_score": 580,
    })
    assert data["eligible"] is False
    assert "credit" in data["reason"].lower() or "cibil" in data["reason"].lower()


def test_check_eligibility_escalation_ceiling():
    """Car loan ₹28L > ₹20L ceiling → escalate_to_rm=True."""
    data = _call("check_eligibility", {
        "loan_product": "car_loan",
        "monthly_income": 95_000.0,
        "loan_amount": 2_800_000.0,
        "tenure_months": 84,
        "age": 32,
        "employment_type": "salaried",
        "credit_score": 740,
    })
    assert data.get("escalate_to_rm") is True


# ── 4. get_document_checklist ────────────────────────────────────────────────

def test_get_document_checklist_returns_docs():
    data = _call("get_document_checklist", {
        "loan_product": "home_loan",
        "employment_type": "salaried",
    })
    assert isinstance(data.get("common_docs"), list)
    assert len(data["common_docs"]) > 0
    assert isinstance(data.get("product_specific_docs"), list)
    assert len(data["product_specific_docs"]) > 0


# ── 5. generate_escalation_summary — validation rejection path ───────────────

def test_generate_escalation_summary_bad_mobile_rejected():
    """An invalid mobile (starts with 1) → escalation_saved=False + validation_errors."""
    data = _call("generate_escalation_summary", {
        "customer_intent": "Home loan of 2.5 crore",
        "loan_product": "home_loan",
        "loan_amount": 25_000_000.0,
        "monthly_income": 180_000.0,
        "escalation_reason": "Amount exceeds advisory ceiling",
        "customer_name": "Test User",
        "callback_number": "1234567890",   # invalid — must start with 6–9
        "customer_email": "test@example.com",
    })
    assert data.get("escalation_saved") is False
    assert "validation_errors" in data


# ── 6. LangChain MCP tool path ────────────────────────────────────────────────

def test_get_mcp_tools_returns_five_langchain_tools():
    """get_mcp_tools() builds 5 valid LangChain StructuredTools with correct names."""
    from tools.tool_registry import get_mcp_tools
    tools = get_mcp_tools()
    assert len(tools) == 5
    names = {t.name for t in tools}
    assert names == {
        "check_eligibility", "calculate_emi",
        "get_document_checklist", "query_loan_policy",
        "generate_escalation_summary",
    }


def test_mcp_tool_emi_via_langchain():
    """calculate_emi (MCP path) called via LangChain .invoke() returns correct EMI."""
    from tools.tool_registry import get_mcp_tools
    tools = {t.name: t for t in get_mcp_tools()}
    result = tools["calculate_emi"].invoke({
        "principal": 3_000_000.0,
        "annual_rate_percent": 9.0,
        "tenure_months": 240,
    })
    data = json.loads(result)
    assert abs(data["emi"] - 26_992) < 5


def test_mcp_tool_eligibility_via_langchain():
    """check_eligibility (MCP path) returns eligible=True for a clear-pass profile."""
    from tools.tool_registry import get_mcp_tools
    tools = {t.name: t for t in get_mcp_tools()}
    result = tools["check_eligibility"].invoke({
        "loan_product": "home_loan",
        "monthly_income": 150_000.0,
        "loan_amount": 5_000_000.0,
        "tenure_months": 240,
        "age": 38,
        "employment_type": "salaried",
        "credit_score": 780,
    })
    data = json.loads(result)
    assert data["eligible"] is True


# ── 7. query_loan_policy via MCP with mocked retriever ───────────────────────

def _mock_retriever(docs):
    """Return a sys.modules patch dict that stubs retrieval.retriever.retrieve."""
    mock_mod = MagicMock()
    mock_mod.retrieve.return_value = docs
    return patch.dict(sys.modules, {"retrieval.retriever": mock_mod})


def test_query_loan_policy_via_mcp_mocked_retriever():
    """query_loan_policy MCP tool returns RAG content when retriever has docs."""
    from langchain_core.documents import Document

    fake_docs = [
        Document(page_content="Home loan interest rates range from 8.50% to 9.25% p.a."),
        Document(page_content="Processing fee is 0.5% of loan amount."),
    ]
    with _mock_retriever(fake_docs):
        result = _call("query_loan_policy", {"query": "What is the home loan interest rate?"})

    assert isinstance(result, str)
    assert "8.50%" in result or "9.25%" in result


def test_query_loan_policy_via_mcp_empty_retriever():
    """query_loan_policy returns fallback message when retriever returns no docs."""
    with _mock_retriever([]):
        result = _call("query_loan_policy", {"query": "What is the NRI rule?"})

    assert isinstance(result, str)
    assert "branch" in result.lower() or "helpline" in result.lower() or "couldn" in result.lower()


def test_query_loan_policy_via_langchain_mocked():
    """query_loan_policy (LangChain MCP path) also routes through the RAG function."""
    from langchain_core.documents import Document
    from tools.tool_registry import get_mcp_tools

    fake_docs = [Document(page_content="Prepayment charges: nil after 12 months for floating rate.")]
    tools = {t.name: t for t in get_mcp_tools()}
    with _mock_retriever(fake_docs):
        result = tools["query_loan_policy"].invoke({"query": "prepayment charges"})

    assert "prepayment" in result.lower() or "nil" in result.lower() or "floating" in result.lower()


# ── 8. generate_escalation_summary — valid save path ─────────────────────────

def test_generate_escalation_summary_valid_save(tmp_path):
    """Valid contact details → escalation_saved=True, escalation_id present."""
    import importlib
    from unittest.mock import patch

    # Redirect DATA_DIR to a temp directory so we don't touch real data
    (tmp_path / "rlhf").mkdir()

    with patch("deployment.config.DATA_DIR", tmp_path):
        data = _call("generate_escalation_summary", {
            "customer_intent": "Home loan of ₹80L for property in Bangalore",
            "loan_product": "home_loan",
            "loan_amount": 8_000_000.0,
            "monthly_income": 120_000.0,
            "escalation_reason": "Amount exceeds 80% LTV — needs committee approval",
            "customer_name": "Priya Sharma",
            "callback_number": "9845012345",
            "customer_email": "priya.sharma@gmail.com",
        })

    assert data.get("escalation_saved") is True
    assert "escalation_id" in data
    assert len(data["escalation_id"]) == 8  # uuid4().hex[:8].upper()
    assert "rm_briefing" in data
    assert "customer_message" in data


def test_generate_escalation_summary_missing_contact_both_rejected():
    """Missing both mobile and email → validation_errors lists both fields."""
    data = _call("generate_escalation_summary", {
        "customer_intent": "Personal loan of 5L",
        "loan_product": "personal_loan",
        "loan_amount": 500_000.0,
        "monthly_income": 60_000.0,
        "escalation_reason": "Complex employment situation",
        # No callback_number, no customer_email
    })
    assert data.get("escalation_saved") is False
    assert len(data["validation_errors"]) == 2


# ── 9. get_document_checklist via LangChain MCP path ─────────────────────────

def test_get_document_checklist_self_employed_via_langchain():
    """get_document_checklist (LangChain MCP path) works for self_employed."""
    from tools.tool_registry import get_mcp_tools
    tools = {t.name: t for t in get_mcp_tools()}
    result = tools["get_document_checklist"].invoke({
        "loan_product": "personal_loan",
        "employment_type": "self_employed",
    })
    data = json.loads(result)
    assert isinstance(data.get("common_docs"), list)
    docs = data["product_specific_docs"]
    assert any("it return" in d.lower() for d in docs)


def test_get_document_checklist_business_via_mcp():
    """get_document_checklist for msme_loan + business returns GST-related docs."""
    data = _call("get_document_checklist", {
        "loan_product": "msme_loan",
        "employment_type": "business",
    })
    docs = data.get("product_specific_docs", [])
    assert any("gst" in d.lower() for d in docs)
