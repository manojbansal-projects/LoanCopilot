"""
Loan Copilot MCP Server — exposes all 5 loan tools via FastMCP.

Allows Claude Desktop, Claude Code, and any MCP-capable client to discover
and call the loan tools without knowing the underlying implementation.

Transport options:
  stdio (default) — for Claude Desktop / subprocess integration
  http            — for network access (port configurable, default 8080)

Usage:
  python scripts/start_mcp_server.py                     # stdio
  python scripts/start_mcp_server.py --transport http    # HTTP on :8080
  python scripts/start_mcp_server.py --transport http --port 9000
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

# ── Server instance ───────────────────────────────────────────────────────────

mcp = FastMCP(
    name="Loan Copilot",
    instructions=(
        "You have access to 5 tools for an Indian retail bank loan origination copilot. "
        "Preferred invocation sequence:\n"
        "1. check_eligibility — after collecting the customer profile\n"
        "2. calculate_emi     — only when eligibility passes\n"
        "3. get_document_checklist — after confirming eligibility\n"
        "4. query_loan_policy — for any policy/rate/tenure/charge question\n"
        "5. generate_escalation_summary — when loan_amount > advisory ceiling "
        "   (Home ₹1.5Cr · Personal ₹40L · MSME ₹2Cr · Car ₹20L) or case is complex.\n"
        "All rate figures are indicative. Never promise approval."
    ),
)

# ── Tool 1: Eligibility check ─────────────────────────────────────────────────

@mcp.tool()
def check_eligibility(
    loan_product: str,
    monthly_income: float,
    loan_amount: float,
    tenure_months: int,
    age: int,
    employment_type: str,
    credit_score: int = 700,
    existing_emi_obligations: float = 0.0,
) -> dict:
    """
    Perform an indicative eligibility check for a loan application.

    Args:
        loan_product: home_loan | personal_loan | msme_loan | car_loan
        monthly_income: Net monthly take-home income in INR.
        loan_amount: Requested loan amount in INR.
        tenure_months: Requested repayment tenure in months.
        age: Applicant age in years (eligible range 21–65).
        employment_type: salaried | self_employed | business
        credit_score: CIBIL score (default 700 if unknown).
        existing_emi_obligations: Total existing monthly EMI payments in INR.

    Returns:
        dict with eligible (bool), reason, foir, indicative_rate_range,
        escalate_to_rm (bool), and escalation_note if ceiling is breached.
    """
    from tools.eligibility_checker import check_eligibility as _fn
    return _fn.invoke({
        "loan_product": loan_product,
        "monthly_income": monthly_income,
        "loan_amount": loan_amount,
        "tenure_months": tenure_months,
        "age": age,
        "employment_type": employment_type,
        "credit_score": credit_score,
        "existing_emi_obligations": existing_emi_obligations,
    })


# ── Tool 2: EMI calculator ────────────────────────────────────────────────────

@mcp.tool()
def calculate_emi(
    principal: float,
    annual_rate_percent: float,
    tenure_months: int,
) -> dict:
    """
    Calculate the monthly EMI for a loan using the reducing-balance method.

    Args:
        principal: Loan amount in INR.
        annual_rate_percent: Annual interest rate as a number (e.g. 9.5 for 9.5%).
        tenure_months: Loan tenure in months.

    Returns:
        dict with emi, total_payable, total_interest, principal, rate, tenure_months.
        All monetary values in INR, rounded to 2 decimal places.
    """
    from tools.emi_calculator import calculate_emi as _fn
    return _fn.invoke({
        "principal": principal,
        "annual_rate_percent": annual_rate_percent,
        "tenure_months": tenure_months,
    })


# ── Tool 3: Document checklist ────────────────────────────────────────────────

@mcp.tool()
def get_document_checklist(
    loan_product: str,
    employment_type: str,
) -> dict:
    """
    Return the document checklist for a given loan product and employment type.

    Args:
        loan_product: home_loan | personal_loan | msme_loan | car_loan
        employment_type: salaried | self_employed | business

    Returns:
        dict with common_docs (list of str) and product_specific_docs (list of str).
        Includes an indicative note — final list may vary after credit appraisal.
    """
    from tools.document_checklist import get_document_checklist as _fn
    return _fn.invoke({
        "loan_product": loan_product,
        "employment_type": employment_type,
    })


# ── Tool 4: Policy FAQ (RAG) ──────────────────────────────────────────────────

@mcp.tool()
def query_loan_policy(query: str) -> str:
    """
    Answer customer questions about loan policies using RAG over policy documents.

    Use for: interest rate bands, processing fees, tenure options, NRI eligibility,
    prepayment charges, CIBIL criteria, turnaround times, or any policy question
    not covered by the eligibility or EMI tools.

    Do NOT use to check the status of an existing loan application — that
    requires core banking integration (planned future capability).

    Args:
        query: Customer question in natural language.

    Returns:
        Policy-grounded answer synthesised from ChromaDB knowledge base.
    """
    from tools.tool_search import query_loan_policy as _fn
    return _fn.invoke({"query": query})


# ── Tool 5: RM escalation ─────────────────────────────────────────────────────

@mcp.tool()
def generate_escalation_summary(
    customer_intent: str,
    loan_product: str,
    loan_amount: float,
    monthly_income: float,
    escalation_reason: str,
    customer_name: str = "",
    callback_number: str = "",
    customer_email: str = "",
    gender: str = "",
    preferred_contact_time: str = "",
    age: int = 0,
    employment_type: str = "",
    credit_score: int = 0,
    tenure_months: int = 0,
    existing_emi_obligations: float = 0.0,
    conversation_summary: str = "",
    session_id: str = "",
) -> dict:
    """
    Generate a structured escalation packet for the Relationship Manager.

    Trigger when: (a) loan_amount exceeds advisory ceiling, or (b) eligibility
    is complex and requires human judgement.
    Always collect customer_name, callback_number, and customer_email first.
    The tool validates mobile (10-digit Indian) and email — on failure it returns
    validation_errors so the agent can re-ask the customer.

    Advisory ceilings: Home ₹1.5Cr · Personal ₹40L · MSME ₹2Cr · Car ₹20L

    Args:
        customer_intent: One-sentence summary of what the customer wants.
        loan_product: home_loan | personal_loan | msme_loan | car_loan
        loan_amount: Requested loan amount in INR.
        monthly_income: Customer's net monthly income in INR.
        escalation_reason: Why this case needs RM intervention.
        customer_name: Customer's full name for the RM callback.
        callback_number: Indian mobile number (10 digits starting with 6-9;
            +91/91/0 prefix accepted).
        customer_email: Customer's email address for RM follow-up.
        gender: male | female | other (optional).
        preferred_contact_time: When the customer prefers a callback (optional).
        age: Customer age in years.
        employment_type: salaried | self_employed | business
        credit_score: CIBIL score if known.
        tenure_months: Requested loan tenure in months.
        existing_emi_obligations: Total existing monthly EMI in INR.
        conversation_summary: Brief summary of what was already discussed.
        session_id: Current session UUID to link RM Dashboard to Langfuse trace.

    Returns:
        On success: escalation_saved=True, escalation_id, rm_briefing, customer_message.
        On failure: escalation_saved=False, validation_errors list.
    """
    from tools.tool_escalate import generate_escalation_summary as _fn
    return _fn.invoke({
        "customer_intent": customer_intent,
        "loan_product": loan_product,
        "loan_amount": loan_amount,
        "monthly_income": monthly_income,
        "escalation_reason": escalation_reason,
        "customer_name": customer_name,
        "callback_number": callback_number,
        "customer_email": customer_email,
        "gender": gender,
        "preferred_contact_time": preferred_contact_time,
        "age": age,
        "employment_type": employment_type,
        "credit_score": credit_score,
        "tenure_months": tenure_months,
        "existing_emi_obligations": existing_emi_obligations,
        "conversation_summary": conversation_summary,
        "session_id": session_id,
    })


# ── Entry point ───────────────────────────────────────────────────────────────

def start_server(transport: str = "stdio", port: int = 8080) -> None:
    """
    Start the MCP server and block until interrupted.

    Args:
        transport: 'stdio' for Claude Desktop / subprocess (default),
                   'http' for network access via streamable-HTTP.
        port: Port number for HTTP transport (ignored for stdio).
    """
    if transport == "http":
        mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
    else:
        mcp.run(transport="stdio")
