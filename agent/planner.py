"""
Advisory planner — determines the next collection step based on SessionState.
Used to guide the agent toward progressively completing the customer profile
before running eligibility / EMI tools.
"""
from __future__ import annotations
from agent.memory import CustomerProfile


COLLECTION_SEQUENCE = [
    ("loan_product",    "Which loan are you interested in? (Home / Personal / MSME / Car)"),
    ("customer_name",   "May I know your name?"),
    ("loan_amount",     "How much would you like to borrow?"),
    ("tenure_months",   "Over how many months/years would you like to repay?"),
    ("monthly_income",  "What is your approximate monthly take-home income?"),
    ("age",             "May I know your age?"),
    ("employment_type", "Are you salaried, self-employed, or a business owner?"),
    ("credit_score",    "Do you know your approximate credit score? (optional — say 'skip' if unsure)"),
]


def next_question(profile: CustomerProfile) -> str | None:
    """Return the next question to ask, or None if all fields are collected."""
    for field, question in COLLECTION_SEQUENCE:
        if getattr(profile, field) is None:
            return question
    return None


def next_field_and_question(profile: CustomerProfile) -> tuple[str, str] | None:
    """Return (field_name, question) for the next missing field, or None if complete."""
    for field, question in COLLECTION_SEQUENCE:
        if getattr(profile, field) is None:
            return (field, question)
    return None


def is_ready_for_eligibility(profile: CustomerProfile) -> bool:
    """Return True when the minimum fields are present to run eligibility check."""
    return not profile.missing_required_fields()
