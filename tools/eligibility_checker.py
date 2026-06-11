"""Tool: check_eligibility — rules-based assessment per loan product."""
from langchain.tools import tool
from deployment.config import ESCALATION_CEILINGS

# ── Indicative rate bands per product (min%, max%) ────────────────────────────
RATE_BANDS = {
    "home_loan":     (8.50, 9.50),
    "personal_loan": (9.99, 24.00),
    "msme_loan":     (9.00, 16.00),
    "car_loan":      (8.75, 10.50),
}

# ── Hard limits ───────────────────────────────────────────────────────────────
PRODUCT_LIMITS = {
    "home_loan":     {"min": 5_00_000,    "max": 5_00_00_000, "max_tenure": 360},
    "personal_loan": {"min": 50_000,      "max": 40_00_000,   "max_tenure": 60},
    "msme_loan":     {"min": 50_000,      "max": 10_00_00_000,"max_tenure": 180},
    "car_loan":      {"min": 3_00_000,    "max": 20_00_000,   "max_tenure": 84},
}


@tool
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
        loan_product: One of: home_loan, personal_loan, msme_loan, car_loan.
        monthly_income: Net monthly take-home income in INR.
        loan_amount: Requested loan amount in INR.
        tenure_months: Requested repayment tenure in months.
        age: Applicant age in years.
        employment_type: salaried / self_employed / business.
        credit_score: CIBIL score (default 700 if unknown).
        existing_emi_obligations: Total existing monthly EMI payments in INR.

    Returns:
        dict with eligible (bool), reason, foir, indicative_rate_range, escalate_to_rm (bool)
    """
    product = loan_product.lower().replace(" ", "_")
    if product not in PRODUCT_LIMITS:
        return {"eligible": False, "reason": f"Unknown product: {loan_product}"}

    limits = PRODUCT_LIMITS[product]
    reasons = []

    # Age check
    if age < 21 or age > 65:
        reasons.append(f"Age {age} outside eligible range 21–65")

    # Credit score
    min_score = 700 if product in ("home_loan", "msme_loan") else 720
    if credit_score < min_score:
        reasons.append(f"Credit score {credit_score} below minimum {min_score}")

    # Amount limits
    if loan_amount < limits["min"] or loan_amount > limits["max"]:
        reasons.append(f"Amount ₹{loan_amount:,.0f} outside product range")

    # Tenure
    if tenure_months > limits["max_tenure"]:
        reasons.append(f"Tenure {tenure_months}m exceeds max {limits['max_tenure']}m")

    # FOIR (Fixed Obligation to Income Ratio)
    foir_limit = 0.55 if monthly_income > 1_00_000 else 0.50
    from tools.emi_calculator import calculate_emi
    emi_result = calculate_emi.invoke({
        "principal": loan_amount,
        "annual_rate_percent": sum(RATE_BANDS[product]) / 2,
        "tenure_months": tenure_months,
    })
    proposed_emi = emi_result.get("emi", 0)
    total_obligations = existing_emi_obligations + proposed_emi
    foir = total_obligations / monthly_income if monthly_income > 0 else 1.0
    if foir > foir_limit:
        reasons.append(
            f"FOIR {foir:.0%} exceeds limit {foir_limit:.0%} "
            f"(income ₹{monthly_income:,.0f}/mo)"
        )

    eligible = len(reasons) == 0
    rate_band = RATE_BANDS[product]
    ceiling = ESCALATION_CEILINGS[product]
    escalate = loan_amount > ceiling

    return {
        "eligible": eligible,
        "reason": "Indicative eligibility: PASS" if eligible else "; ".join(reasons),
        "foir": round(foir, 4),
        "indicative_rate_range": f"{rate_band[0]}% – {rate_band[1]}%",
        "escalate_to_rm": escalate,
        "escalation_note": (
            f"Amount ₹{loan_amount/1e5:.1f}L exceeds advisory ceiling ₹{ceiling/1e5:.0f}L. "
            "Will refer to RM."
        ) if escalate else None,
    }
