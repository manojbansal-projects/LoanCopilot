"""
Central registry — assembles LangChain tools for the AgentExecutor.

Two paths:
  get_all_tools()  — direct imports (default; USE_MCP not set or false)
  get_mcp_tools()  — tools backed by the in-process FastMCP server (USE_MCP=true)

Both return a list of LangChain tool objects the agent can bind to its LLM.
The MCP path validates inputs/outputs through the MCP protocol layer, making it
straightforward to swap the underlying implementation for a remote MCP service.
"""
from tools.emi_calculator import calculate_emi
from tools.eligibility_checker import check_eligibility
from tools.document_checklist import get_document_checklist
from tools.tool_search import query_loan_policy
from tools.tool_escalate import generate_escalation_summary


def get_all_tools() -> list:
    """Return all 5 LangChain @tool objects (direct import path)."""
    return [
        check_eligibility,
        calculate_emi,
        get_document_checklist,
        query_loan_policy,
        generate_escalation_summary,
    ]


# JSON Schema type → Python type
_JSON_TYPE_MAP: dict = {
    "string":  str,
    "number":  float,
    "integer": int,
    "boolean": bool,
}


def get_mcp_tools() -> list:
    """
    Return LangChain StructuredTool objects backed by the in-process MCP server.

    Each tool is discovered from FastMCP's registered tool list, then wrapped in
    a StructuredTool whose args_schema is built dynamically from the MCP tool's
    JSON Schema parameters.  Calls route through ``loan_mcp.client.call_tool_sync``
    which exercises FastMCP's full schema-validation and serialisation path.

    Activated when USE_MCP=true in the environment.
    Falls back to get_all_tools() if the mcp package is not installed.
    """
    import json as _json
    from typing import Optional
    from langchain_core.tools import StructuredTool
    from pydantic import create_model, Field
    try:
        from loan_mcp.client import call_tool_sync, list_tools_sync
        mcp_tools = list_tools_sync()
    except ImportError:
        import logging
        logging.getLogger(__name__).warning(
            "USE_MCP=true but 'mcp' package not found — "
            "falling back to direct tool imports. "
            "Activate your venv or run: pip install mcp>=1.0.0"
        )
        return get_all_tools()
    lc_tools = []

    for t in mcp_tools:
        tool_name = t["name"]
        tool_desc = t["description"]
        params    = t["parameters"]
        required  = params.get("required", [])
        props     = params.get("properties", {})

        # Build a Pydantic model so LangChain can parse the arg dict correctly
        pydantic_fields: dict = {}
        for field_name, field_def in props.items():
            py_type = _JSON_TYPE_MAP.get(field_def.get("type", "string"), str)
            field_desc = field_def.get("description", "")
            if field_name in required:
                pydantic_fields[field_name] = (
                    py_type,
                    Field(description=field_desc),
                )
            else:
                default_val = field_def.get("default", 0 if py_type in (int, float) else "")
                pydantic_fields[field_name] = (
                    Optional[py_type],
                    Field(default=default_val, description=field_desc),
                )

        args_schema = create_model(f"{tool_name}_schema", **pydantic_fields)

        def _make_func(name: str):
            def _func(**kwargs) -> str:
                result = call_tool_sync(name, kwargs)
                if isinstance(result, (dict, list)):
                    return _json.dumps(result, ensure_ascii=False, indent=2)
                return str(result)
            _func.__name__ = name
            return _func

        lc_tools.append(
            StructuredTool.from_function(
                func=_make_func(tool_name),
                name=tool_name,
                description=tool_desc,
                args_schema=args_schema,
            )
        )

    return lc_tools
