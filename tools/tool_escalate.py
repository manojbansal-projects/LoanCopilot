"""Tool: generate_escalation_summary — structured RM handoff packet."""
from langchain.tools import tool
from safety.pii_filter import mask


@tool
def generate_escalation_summary(
    customer_intent: str,
    loan_product: str,
    loan_amount: float,
    monthly_income: float,
    escalation_reason: str,
) -> dict:
    """
    Generate a structured escalation packet for the Relationship Manager.

    Call this when: (a) loan amount exceeds advisory ceiling, or (b) eligibility
    is borderline / complex and requires human judgement.

    Args:
        customer_intent: One-sentence summary of what the customer wants.
        loan_product: Product name (home_loan / personal_loan / msme_loan / car_loan).
        loan_amount: Requested loan amount in INR.
        monthly_income: Customer's monthly income in INR.
        escalation_reason: Why this case needs RM intervention.

    Returns:
        dict with escalation packet fields (PII-masked for logging).
    """
    summary = {
        "escalation_required": True,
        "product": loan_product,
        "requested_amount_inr": loan_amount,
        "monthly_income_inr": monthly_income,
        "customer_intent": mask(customer_intent),
        "reason": escalation_reason,
        "recommended_action": (
            "Please have an RM contact the customer within 1 business day to "
            "discuss a bespoke loan structure or credit appraisal."
        ),
        "customer_message": (
            "Your query requires a detailed review by our specialist. "
            "A Relationship Manager will reach out to you within 1 business day. "
            "Thank you for your patience."
        ),
    }
    return summary
