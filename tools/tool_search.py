"""Tool: lookup_loan_status — RAG-backed FAQ and status query."""
from langchain.tools import tool


@tool
def lookup_loan_status(query: str) -> str:
    """
    Look up general loan FAQ or application-status information using the RAG retriever.

    Use this tool when the customer asks general questions about the loan process,
    interest rate bands, processing fees, turnaround times, or product comparisons
    that are not covered by the eligibility or EMI tools.

    Args:
        query: The customer's question in natural language.

    Returns:
        A policy-grounded answer from the knowledge base.
    """
    # TODO (Phase 4): wire to retrieval.retriever.retrieve()
    from retrieval.retriever import retrieve
    docs = retrieve(query)
    if not docs:
        return (
            "I couldn't find specific information on that. "
            "Please contact your nearest branch or call our helpline."
        )
    return "\n\n".join(d.page_content for d in docs[:3])
