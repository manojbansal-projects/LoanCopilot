"""PII masking applied to all text before log writes."""
import re

# ── Regex patterns ────────────────────────────────────────────────────────────
_AADHAAR = re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b")
_PAN     = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
_MOBILE  = re.compile(r"\b(?:\+91[\s-]?)?[6-9]\d{9}\b")
_EMAIL   = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
_ACCOUNT = re.compile(r"\b\d{9,18}\b")  # bank account / IFSC-adjacent numbers

PATTERNS = [
    (_AADHAAR, "[AADHAAR REDACTED]"),
    (_PAN,     "[PAN REDACTED]"),
    (_MOBILE,  "[MOBILE REDACTED]"),
    (_EMAIL,   "[EMAIL REDACTED]"),
    (_ACCOUNT, "[ACCOUNT REDACTED]"),
]


def mask(text: str) -> str:
    """Return text with all PII replaced by placeholder tokens."""
    for pattern, replacement in PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def contains_pii(text: str) -> bool:
    """Return True if any PII pattern matches (used in safety gate pre-check)."""
    return any(p.search(text) for p, _ in PATTERNS)
