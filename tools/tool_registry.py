"""Central registry — assembles all 5 LangChain tools for the AgentExecutor."""
from tools.emi_calculator import calculate_emi
from tools.eligibility_checker import check_eligibility
from tools.document_checklist import get_document_checklist
from tools.tool_search import query_loan_policy
from tools.tool_escalate import generate_escalation_summary


def get_all_tools() -> list:
    """Return all registered tools in the order the agent should prefer them."""
    return [
        check_eligibility,
        calculate_emi,
        get_document_checklist,
        query_loan_policy,
        generate_escalation_summary,
    ]
