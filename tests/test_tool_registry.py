"""Unit tests for tools/tool_registry.py.

Verifies that both the direct tool path (get_all_tools) and MCP path
(get_mcp_tools) return the correct set of LangChain tool objects.
"""
from __future__ import annotations

import pytest

EXPECTED_TOOL_NAMES = {
    "check_eligibility",
    "calculate_emi",
    "get_document_checklist",
    "query_loan_policy",
    "generate_escalation_summary",
}


# ═══════════════════════════════════════════════════════════════════
# 1. Direct tool path — get_all_tools()
# ═══════════════════════════════════════════════════════════════════

class TestGetAllTools:
    def _tools(self):
        from tools.tool_registry import get_all_tools
        return get_all_tools()

    def test_returns_exactly_five_tools(self):
        assert len(self._tools()) == 5

    def test_all_expected_names_present(self):
        names = {t.name for t in self._tools()}
        assert names == EXPECTED_TOOL_NAMES

    def test_all_tools_have_description(self):
        for tool in self._tools():
            assert isinstance(tool.description, str)
            assert len(tool.description) > 10, f"{tool.name} has too-short description"

    def test_each_tool_is_invocable(self):
        """Each tool must have an .invoke() method."""
        for tool in self._tools():
            assert callable(getattr(tool, "invoke", None)), \
                f"{tool.name} missing .invoke()"

    def test_calculate_emi_in_list(self):
        names = {t.name for t in self._tools()}
        assert "calculate_emi" in names

    def test_check_eligibility_in_list(self):
        names = {t.name for t in self._tools()}
        assert "check_eligibility" in names

    def test_query_loan_policy_in_list(self):
        names = {t.name for t in self._tools()}
        assert "query_loan_policy" in names

    def test_generate_escalation_summary_in_list(self):
        names = {t.name for t in self._tools()}
        assert "generate_escalation_summary" in names

    def test_tools_are_unique(self):
        """No duplicate names."""
        names = [t.name for t in self._tools()]
        assert len(names) == len(set(names))


# ═══════════════════════════════════════════════════════════════════
# 2. MCP tool path — get_mcp_tools()
# ═══════════════════════════════════════════════════════════════════

class TestGetMCPTools:
    def _tools(self):
        from tools.tool_registry import get_mcp_tools
        return get_mcp_tools()

    def test_returns_exactly_five_tools(self):
        assert len(self._tools()) == 5

    def test_all_expected_names_present(self):
        names = {t.name for t in self._tools()}
        assert names == EXPECTED_TOOL_NAMES

    def test_all_tools_have_description(self):
        for tool in self._tools():
            assert isinstance(tool.description, str)
            assert len(tool.description) > 10

    def test_all_tools_have_args_schema(self):
        """MCP path builds Pydantic args_schema — must be present."""
        for tool in self._tools():
            assert tool.args_schema is not None, \
                f"{tool.name} missing args_schema in MCP path"

    def test_mcp_tools_are_invocable(self):
        for tool in self._tools():
            assert callable(getattr(tool, "invoke", None))

    def test_calculate_emi_args_schema_has_required_fields(self):
        tools = {t.name: t for t in self._tools()}
        emi_tool = tools["calculate_emi"]
        schema_fields = set(emi_tool.args_schema.model_fields.keys())
        assert {"principal", "annual_rate_percent", "tenure_months"}.issubset(schema_fields)

    def test_check_eligibility_args_schema_has_required_fields(self):
        tools = {t.name: t for t in self._tools()}
        elig_tool = tools["check_eligibility"]
        schema_fields = set(elig_tool.args_schema.model_fields.keys())
        assert {"loan_product", "monthly_income", "loan_amount",
                "tenure_months", "age", "employment_type"}.issubset(schema_fields)


# ═══════════════════════════════════════════════════════════════════
# 3. Consistency between direct and MCP paths
# ═══════════════════════════════════════════════════════════════════

class TestDirectVsMCPConsistency:
    def test_same_tool_names(self):
        from tools.tool_registry import get_all_tools, get_mcp_tools
        direct_names = {t.name for t in get_all_tools()}
        mcp_names    = {t.name for t in get_mcp_tools()}
        assert direct_names == mcp_names, \
            f"Direct path tools {direct_names} != MCP path tools {mcp_names}"

    def test_same_tool_count(self):
        from tools.tool_registry import get_all_tools, get_mcp_tools
        assert len(get_all_tools()) == len(get_mcp_tools())
