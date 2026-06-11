"""Tool: get_document_checklist — returns required documents per product + employment type."""
from langchain.tools import tool

_COMMON_DOCS = [
    "Aadhaar card (identity + address proof)",
    "PAN card",
    "Last 3 months bank statements",
    "Passport-size photographs (2)",
    "Duly filled application form",
]

_BY_PRODUCT_EMPLOYMENT = {
    ("home_loan", "salaried"): [
        "Last 3 months salary slips",
        "Form 16 / IT returns (2 years)",
        "Property documents / sale agreement",
        "NOC from existing bank (if balance transfer)",
    ],
    ("home_loan", "self_employed"): [
        "IT returns (3 years) with computation",
        "CA-certified P&L and Balance Sheet (2 years)",
        "Property documents / sale agreement",
        "Business proof (GST certificate / trade licence)",
    ],
    ("personal_loan", "salaried"): [
        "Last 3 months salary slips",
        "Form 16 / IT returns (1 year)",
        "Employment confirmation letter",
    ],
    ("personal_loan", "self_employed"): [
        "IT returns (2 years) with computation",
        "CA-certified P&L (1 year)",
        "Business proof",
    ],
    ("msme_loan", "business"): [
        "Business registration certificate",
        "GST registration and returns (12 months)",
        "CA-certified financials (2 years)",
        "IT returns (2 years)",
        "Business bank statements (12 months)",
        "Collateral documents (if secured loan)",
    ],
    ("car_loan", "salaried"): [
        "Last 3 months salary slips",
        "Form 16 (1 year)",
        "Car proforma invoice / dealer quote",
    ],
    ("car_loan", "self_employed"): [
        "IT returns (2 years)",
        "Car proforma invoice / dealer quote",
    ],
}


@tool
def get_document_checklist(loan_product: str, employment_type: str) -> dict:
    """
    Return the document checklist for a given loan product and employment type.

    Args:
        loan_product: home_loan / personal_loan / msme_loan / car_loan.
        employment_type: salaried / self_employed / business.

    Returns:
        dict with common_docs (list) and product_specific_docs (list).
    """
    product = loan_product.lower().replace(" ", "_")
    emp = employment_type.lower().replace("-", "_")
    if emp in ("business_owner", "business owner"):
        emp = "business"

    specific = _BY_PRODUCT_EMPLOYMENT.get((product, emp))
    if specific is None:
        specific = ["Please visit your nearest branch for a personalised document list."]

    return {
        "loan_product": loan_product,
        "employment_type": employment_type,
        "common_docs": _COMMON_DOCS,
        "product_specific_docs": specific,
        "note": "This is an indicative list. Final requirements may vary after credit appraisal.",
    }
