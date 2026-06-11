"""Tool: calculate_emi — reducing-balance EMI formula."""
from langchain.tools import tool


@tool
def calculate_emi(
    principal: float,
    annual_rate_percent: float,
    tenure_months: int,
) -> dict:
    """
    Calculate the monthly EMI for a loan using the reducing-balance method.

    Args:
        principal: Loan amount in INR.
        annual_rate_percent: Annual interest rate (e.g. 9.5 for 9.5%).
        tenure_months: Loan tenure in months.

    Returns:
        dict with keys: emi, total_payable, total_interest, principal, rate, tenure_months
    """
    if tenure_months <= 0 or principal <= 0:
        return {"error": "Principal and tenure must be positive"}

    r = annual_rate_percent / 12 / 100
    if r == 0:
        emi = principal / tenure_months
    else:
        emi = principal * r * (1 + r) ** tenure_months / ((1 + r) ** tenure_months - 1)

    total_payable = emi * tenure_months
    total_interest = total_payable - principal

    return {
        "emi": round(emi, 2),
        "total_payable": round(total_payable, 2),
        "total_interest": round(total_interest, 2),
        "principal": principal,
        "annual_rate_percent": annual_rate_percent,
        "tenure_months": tenure_months,
    }
