"""Tool: generate_escalation_summary — structured RM handoff packet."""
from __future__ import annotations
import json
import re
import uuid
from datetime import datetime
from pathlib import Path

from langchain.tools import tool
from safety.pii_filter import mask


# ── Contact detail validators ─────────────────────────────────────────────────

def _validate_mobile(number: str) -> tuple[bool, str]:
    """
    Validate and normalise an Indian mobile number.
    Accepts: 10-digit numbers starting with 6-9, optionally prefixed with
    +91, 91 (12-digit), or 0 (11-digit).
    Returns (is_valid, normalised_10_digit_string).
    """
    digits = re.sub(r"[\s\-\(\)\+]", "", number)
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    elif digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]
    if re.fullmatch(r"[6-9]\d{9}", digits):
        return True, digits
    return False, digits


def _validate_email(email: str) -> bool:
    """Basic RFC-5321 surface check: local@domain.tld, TLD ≥ 2 chars."""
    return bool(re.fullmatch(
        r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
        email.strip(),
    ))

# ── Product display names ─────────────────────────────────────────────────────
_PRODUCT_DISPLAY = {
    "home_loan": "Home Loan",
    "personal_loan": "Personal Loan",
    "msme_loan": "MSME Loan",
    "car_loan": "New Car Loan",
}

# ── Product-specific RM talking points ───────────────────────────────────────
_RM_TALKING_POINTS = {
    "home_loan": [
        "Verify property value and LTV ratio (max 90% for properties ≤₹30L)",
        "Confirm title clearance and legal opinion on property documents",
        "Review applicant's existing home loan obligations if any",
        "Discuss fixed vs floating rate preference given current EBLR",
        "Check eligibility for PMAY subsidy if first-time buyer",
    ],
    "personal_loan": [
        "Confirm employer stability (salary slip vs bank credit pattern)",
        "Discuss purpose of loan — higher-risk end-use may affect rate",
        "Review existing EMI obligations for accurate FOIR",
        "Explore secured personal loan option to bring rate down",
        "Confirm no foreclosure or write-off in credit history",
    ],
    "msme_loan": [
        "Confirm Udyam/MSME registration certificate and business vintage",
        "Review last 2 years CA-certified financials and DSCR",
        "Discuss collateral options (property, plant & machinery)",
        "Explore CGTMSE guarantee scheme eligibility for unsecured portion",
        "Confirm GST compliance and 12-month GST returns",
        "Discuss phased disbursement if full amount needs committee approval",
    ],
    "car_loan": [
        "Confirm proforma invoice from dealer and on-road price",
        "Verify income stability for EMI serviceability",
        "Review applicant's existing vehicle loans if any",
        "Confirm insurance arrangement (bank requires comprehensive cover)",
        "Discuss hypothecation process and RC endorsement timeline",
    ],
}


def _format_timestamp_human(timestamp: str) -> str:
    """Convert '2026-06-11 18:50:48' to 'Thursday, 11 Jun 2026 at 6:50 PM'."""
    try:
        dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
        day = dt.strftime("%A")          # e.g. Thursday
        date = dt.strftime("%-d %b %Y") # e.g. 11 Jun 2026
        time = dt.strftime("%-I:%M %p") # e.g. 6:50 PM
        return f"{day}, {date} at {time}"
    except Exception:
        return timestamp


def _build_rm_briefing(
    customer_name: str,
    callback_number: str,
    customer_email: str,
    gender: str,
    preferred_contact_time: str,
    loan_product: str,
    loan_amount: float,
    tenure_months: int,
    monthly_income: float,
    existing_emi_obligations: float,
    age: int,
    employment_type: str,
    credit_score: int,
    customer_intent: str,
    escalation_reason: str,
    conversation_summary: str,
    escalation_id: str,
    timestamp: str,
) -> str:
    """Format the complete pre-call briefing document for the RM."""
    prod = loan_product.lower().replace(" ", "_")
    prod_display = _PRODUCT_DISPLAY.get(prod, loan_product)
    talking_points = _RM_TALKING_POINTS.get(prod, [])
    human_ts = _format_timestamp_human(timestamp)

    # Gender-aware salutation
    salutation = ""
    if gender:
        g = gender.strip().lower()
        if g in ("male", "m"):
            salutation = "Mr."
        elif g in ("female", "f"):
            salutation = "Ms."

    def rupees(amount: float) -> str:
        if amount >= 1_00_00_000:
            return f"₹{amount/1_00_00_000:.2f} Cr"
        if amount >= 1_00_000:
            return f"₹{amount/1_00_000:.1f} L"
        return f"₹{amount:,.0f}"

    display_name = f"{salutation} {customer_name}".strip() if salutation else (customer_name or "Not collected")

    lines = [
        "=" * 56,
        "  RM PRE-CALL BRIEFING",
        f"  Escalation ID : {escalation_id}",
        "=" * 56,
        "",
        "INTERACTION DETAILS",
        f"  Date & Time    : {human_ts}",
        f"  Channel        : AI Loan Copilot (web chat)",
        f"  Best Time      : {preferred_contact_time or 'Not specified'}",
        "",
        "CONTACT",
        f"  Name            : {display_name}",
        f"  Gender          : {gender.title() if gender else 'Not collected'}",
        f"  Callback Number : {callback_number or 'Not collected'}",
        f"  Email           : {customer_email or 'Not collected'}",
        "",
        "LOAN REQUEST",
        f"  Product  : {prod_display}",
        f"  Amount   : {rupees(loan_amount)}",
    ]
    if tenure_months:
        yrs, mo = divmod(tenure_months, 12)
        tenure_str = f"{yrs} yr" + (f" {mo} mo" if mo else "")
        lines.append(f"  Tenure   : {tenure_str} ({tenure_months} months)")
    lines.append(f"  Intent   : {customer_intent}")
    lines += [
        "",
        "CUSTOMER PROFILE",
        f"  Monthly Income       : {rupees(monthly_income)}/month",
    ]
    if existing_emi_obligations:
        lines.append(f"  Existing EMI         : {rupees(existing_emi_obligations)}/month")
    if age:
        lines.append(f"  Age                  : {age} years")
    if employment_type:
        lines.append(f"  Employment           : {employment_type.replace('_', ' ').title()}")
    if credit_score:
        lines.append(f"  CIBIL Score          : {credit_score}")
    lines += [
        "",
        "ESCALATION REASON",
        f"  {escalation_reason}",
        "",
        "SUGGESTED TALKING POINTS FOR RM",
    ]
    for pt in talking_points:
        lines.append(f"  • {pt}")
    if conversation_summary:
        lines += [
            "",
            "CONVERSATION SUMMARY",
            f"  {conversation_summary}",
        ]
    lines += [
        "",
        "─" * 56,
        "NOTE: All figures shared with customer are indicative.",
        "Full credit appraisal required before formal commitment.",
        "=" * 56,
    ]
    return "\n".join(lines)


@tool
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
    Generate a structured escalation packet for the Relationship Manager and
    persist it to escalations.json for the RM Dashboard.

    Call this when: (a) loan amount exceeds advisory ceiling, or (b) eligibility
    is borderline / complex and requires human judgement.
    Always collect customer_name, callback_number, and customer_email first.
    The tool validates mobile and email format — if either is invalid it returns
    validation_errors and does NOT save the record; ask the customer to correct
    the flagged field(s) and call this tool again.

    Args:
        customer_intent: One-sentence summary of what the customer wants.
        loan_product: home_loan / personal_loan / msme_loan / car_loan.
        loan_amount: Requested loan amount in INR.
        monthly_income: Customer's net monthly income in INR.
        escalation_reason: Why this case needs RM intervention.
        customer_name: Customer's full name for the RM callback.
        callback_number: Indian mobile number (10 digits, starts with 6-9;
            +91/91/0 prefix accepted). Full number stored for RM.
        customer_email: Customer's email address for RM follow-up.
        gender: Customer gender — male / female / other (optional).
        preferred_contact_time: When the customer prefers to be called back
            (e.g. "mornings", "after 6 PM", "weekdays only"). Optional.
        age: Customer age in years.
        employment_type: salaried / self_employed / business.
        credit_score: CIBIL score if known.
        tenure_months: Requested loan tenure in months.
        existing_emi_obligations: Total existing monthly EMI in INR.
        conversation_summary: Brief summary of what was already discussed.
        session_id: Current session UUID — used to link the RM Dashboard record
            to the Langfuse trace. Pass agent.session_id when calling.

    Returns:
        On success: dict with escalation_saved=True, rm_briefing, customer_message.
        On validation failure: dict with escalation_saved=False, validation_errors
        listing which fields are invalid so the agent can re-ask the customer.
    """
    from deployment.config import DATA_DIR

    # ── Validate contact details ──────────────────────────────────────────────
    validation_errors = []

    mobile_valid, mobile_clean = _validate_mobile(callback_number) if callback_number else (False, "")
    if not callback_number:
        validation_errors.append("callback_number: not provided — please ask the customer for their mobile number")
    elif not mobile_valid:
        validation_errors.append(
            f"callback_number: '{callback_number}' is not a valid Indian mobile number "
            "(must be 10 digits, starting with 6, 7, 8, or 9)"
        )

    if not customer_email:
        validation_errors.append("customer_email: not provided — please ask the customer for their email address")
    elif not _validate_email(customer_email):
        validation_errors.append(
            f"customer_email: '{customer_email}' does not look like a valid email address "
            "(expected format: name@domain.com)"
        )

    if validation_errors:
        return {
            "escalation_saved": False,
            "validation_errors": validation_errors,
            "retry_instruction": (
                "Please inform the customer that one or more contact details need "
                "correction, ask them to provide the correct value(s), and call "
                "generate_escalation_summary again with the corrected fields."
            ),
        }

    # ── Build packet ──────────────────────────────────────────────────────────
    escalation_id = uuid.uuid4().hex[:8].upper()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    last_four = mobile_clean[-4:]

    rm_briefing = _build_rm_briefing(
        customer_name=customer_name,
        callback_number=mobile_clean,       # normalised 10-digit, full for RM
        customer_email=customer_email.strip(),
        gender=gender,
        preferred_contact_time=preferred_contact_time,
        loan_product=loan_product,
        loan_amount=loan_amount,
        tenure_months=tenure_months,
        monthly_income=monthly_income,
        existing_emi_obligations=existing_emi_obligations,
        age=age,
        employment_type=employment_type,
        credit_score=credit_score,
        customer_intent=customer_intent,
        escalation_reason=escalation_reason,
        conversation_summary=conversation_summary,
        escalation_id=escalation_id,
        timestamp=timestamp,
    )

    packet = {
        "escalation_saved": True,
        "escalation_id": escalation_id,
        "session_id": session_id or "",
        "timestamp": timestamp,
        "loan_product": loan_product,
        "customer_name": customer_name or "Not provided",
        "gender": gender or "Not collected",
        "preferred_contact_time": preferred_contact_time or "Not specified",
        "callback_number": mobile_clean,            # full normalised number for RM
        "customer_email": customer_email.strip(),   # full email for RM
        "age": age or None,
        "employment_type": employment_type or None,
        "credit_score": credit_score or None,
        "tenure_months": tenure_months or None,
        "existing_emi_obligations_inr": existing_emi_obligations or None,
        "loan_amount_inr": loan_amount,
        "monthly_income_inr": monthly_income,
        "customer_intent": customer_intent,
        "escalation_reason": escalation_reason,
        "conversation_summary": conversation_summary or None,
        "rm_briefing": rm_briefing,
        "recommended_action": (
            "Contact the customer within 1 business day to discuss "
            "a bespoke loan structure or credit appraisal."
        ),
        "customer_message": (
            "Your query requires a detailed review by our specialist. "
            f"A Relationship Manager will call you back within 1 business day "
            f"on the number ending in {last_four} and may also reach out to "
            f"{customer_email.strip()}. Thank you for your patience."
        ),
    }

    # Persist to escalations.json for RM Dashboard (Phase 8)
    _persist_escalation(DATA_DIR, packet)

    return packet


def _persist_escalation(data_dir: Path, packet: dict) -> None:
    """Append escalation packet to escalations.json (masked copy for audit log)."""
    escalations_path = data_dir / "rlhf" / "escalations.json"
    try:
        existing = json.loads(escalations_path.read_text()) if escalations_path.exists() else []
        # Store full packet in escalations.json (RM Dashboard reads this)
        existing.append(packet)
        escalations_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False))
    except Exception:
        pass  # Never block the agent turn for a persistence failure
