"""Validate agent responses against hard policy rules."""
from __future__ import annotations


HARD_RULES = [
    {
        "id": "no_rate_promise",
        "description": "Agent must not quote a specific interest rate",
        "check": lambda resp: "%" not in resp or "indicative" in resp.lower() or "current rate" in resp.lower(),
    },
    {
        "id": "no_approval_guarantee",
        "description": "Agent must not guarantee loan approval",
        "check": lambda resp: "guaranteed" not in resp.lower() and "will be approved" not in resp.lower(),
    },
    {
        "id": "no_pii_in_response",
        "description": "Agent must not echo back PII",
        "check": lambda resp: not any(term in resp for term in ["aadhaar", "pan card number", "account number"]),
    },
]


def check_response(response: str) -> list[dict]:
    """Return list of rule violations (empty list = all pass)."""
    violations = []
    for rule in HARD_RULES:
        if not rule["check"](response):
            violations.append({"rule_id": rule["id"], "description": rule["description"]})
    return violations
