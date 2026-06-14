"""Tool: query_loan_policy — RAG-backed policy FAQ lookup."""
from langchain.tools import tool


@tool
def query_loan_policy(query: str) -> str:
    """
    Answer customer questions about loan policies using the RAG retriever.

    Use this tool when the customer asks about interest rate bands, processing fees,
    tenure options, NRI eligibility, prepayment charges, CIBIL criteria, or any
    other policy question not covered by the eligibility or EMI tools.
    Do NOT use this for checking the status of an existing loan application —
    that requires core banking integration (future capability).

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
