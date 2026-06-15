"""
LoanCopilotAgent — unified agent class across all phases.

Phases:
  2  — rules-based (no LLM, no API key needed)
  3  — LLM + Langfuse (no RAG, no tools)
  4  — LLM + RAG (ChromaDB)
  5+ — LLM + RAG + 5 tools + memory (full)
"""
from __future__ import annotations

import re
import uuid
from typing import Optional

from agent.memory import SessionState, CustomerProfile
from agent.planner import next_field_and_question


# ── Indicative rate bands ────────────────────────────────────────────────────
_RATE_BANDS: dict[str, tuple[float, float]] = {
    "home_loan":     (8.50,  9.50),
    "personal_loan": (9.99, 24.00),
    "msme_loan":     (9.00, 16.00),
    "car_loan":      (8.75, 10.50),
}

_PRODUCT_DISPLAY = {
    "home_loan": "Home Loan", "personal_loan": "Personal Loan",
    "msme_loan": "MSME Loan", "car_loan": "New Car Loan",
}


# ── Intent detection (Phase 2 — keyword-only) ───────────────────────────────

def _detect_intent(text: str) -> str:
    lower = text.lower()
    if any(k in lower for k in [
        "invest", "mutual fund", "insurance", "stocks", "shares",
        "legal advice", "competitor", "other bank", "income tax filing",
        "ignore previous", "forget your", "act as", "jailbreak",
        "reveal your prompt", "system prompt",
    ]):
        return "OUT_OF_SCOPE"
    if any(k in lower for k in [
        "interest rate", "rate of interest", "what is the rate",
        "processing fee", "how long", "processing time",
        "how many days", "turnaround", "what is foir", "what is emi",
        "eligibility criteria", "minimum salary", "minimum income",
    ]):
        return "FAQ"
    if any(k in lower for k in [
        "document", "papers", "what do i need", "checklist",
        "required doc", "kyc", "id proof", "what should i bring",
    ]):
        return "DOCUMENTS"
    if any(k in lower for k in [
        "emi", "monthly payment", "installment", "instalment",
        "how much per month", "repayment amount", "monthly outgo",
    ]):
        return "EMI"
    return "ELIGIBILITY"  # default for loan queries


# ── Profile value extractor (Phase 2 — regex-only) ─────────────────────────

def _extract_profile(text: str, profile: CustomerProfile,
                     last_asked: Optional[str] = None) -> None:
    """
    Parse text and update profile in-place.
    `last_asked` guides extraction when the user gives a bare answer
    (e.g. agent asked "Your age?" → user replied "35").
    """
    lower = text.lower()

    # ── Loan product ──────────────────────────────────────────────────────────
    if profile.loan_product is None:
        if any(k in lower for k in ["home loan", "home  loan", "house loan",
                                     "home", "house", "flat", "apartment", "property"]):
            profile.loan_product = "home_loan"
        elif any(k in lower for k in ["personal loan", "personal"]):
            profile.loan_product = "personal_loan"
        elif any(k in lower for k in ["msme", "sme", "business loan",
                                       "manufacturing", "enterprise"]):
            profile.loan_product = "msme_loan"
        elif any(k in lower for k in ["car loan", "car", "vehicle", "auto", "suv", "sedan"]):
            profile.loan_product = "car_loan"

    # ── Loan amount (crore takes precedence over lakh) ────────────────────────
    if profile.loan_amount is None or last_asked == "loan_amount":
        m = re.search(r'(?:₹|rs\.?\s*)?(\d+(?:\.\d+)?)\s*(?:crore|cr)(?:s|e)?\b', lower)
        if m:
            profile.loan_amount = float(m.group(1)) * 1_00_00_000
        else:
            m = re.search(r'(?:₹|rs\.?\s*)?(\d+(?:\.\d+)?)\s*(?:lakh|lac|l)(?:s|hs)?\b', lower)
            if m:
                profile.loan_amount = float(m.group(1)) * 1_00_000
            elif last_asked == "loan_amount":
                # bare number like "5000000"
                m = re.search(r'\b(\d[\d,]{5,})\b', lower)
                if m:
                    profile.loan_amount = float(m.group(1).replace(',', ''))

    # ── Tenure ────────────────────────────────────────────────────────────────
    if profile.tenure_months is None or last_asked == "tenure_months":
        m = re.search(r'\b(\d{1,2})\s*-?\s*year', lower)
        if m:
            profile.tenure_months = int(m.group(1)) * 12
        else:
            m = re.search(r'\b(\d{2,3})\s*month', lower)
            if m:
                profile.tenure_months = int(m.group(1))
            elif last_asked == "tenure_months":
                m = re.search(r'\b(\d{1,3})\b', lower)
                if m:
                    v = int(m.group(1))
                    # heuristic: ≤30 → years, >30 → months
                    profile.tenure_months = v * 12 if v <= 30 else v

    # ── Monthly income ────────────────────────────────────────────────────────
    if profile.monthly_income is None or last_asked == "monthly_income":
        m = re.search(
            r'(?:earn|income|salary|take.?home|per month|monthly|ctc|get)\D{0,20}'
            r'(?:₹|rs\.?\s*)?(\d[\d,]*(?:\.\d+)?)',
            lower
        )
        if m:
            profile.monthly_income = float(m.group(1).replace(',', ''))
        else:
            # When we explicitly asked for income, accept lakh/crore or bare large number
            m_cr = re.search(r'(?:₹|rs\.?\s*)?(\d+(?:\.\d+)?)\s*(?:crore|cr)(?:s|e)?\b', lower)
            m_lk = re.search(r'(?:₹|rs\.?\s*)?(\d+(?:\.\d+)?)\s*(?:lakh|lac|l)(?:s|hs)?\b', lower)
            if m_cr and last_asked == "monthly_income":
                profile.monthly_income = float(m_cr.group(1)) * 1_00_00_000
            elif m_lk and last_asked == "monthly_income":
                profile.monthly_income = float(m_lk.group(1)) * 1_00_000
            elif last_asked == "monthly_income":
                m = re.search(r'\b(\d[\d,]{3,})\b', lower)
                if m:
                    profile.monthly_income = float(m.group(1).replace(',', ''))

    # ── Age ───────────────────────────────────────────────────────────────────
    if profile.age is None or last_asked == "age":
        m = re.search(r'\b(\d{2})\s*(?:years?\s*old|yr\b)', lower)
        if m:
            profile.age = int(m.group(1))
        else:
            m = re.search(r'(?:age|aged|am)\D{0,5}(\d{2})\b', lower)
            if m:
                profile.age = int(m.group(1))
            elif last_asked == "age":
                m = re.search(r'\b([2-7]\d)\b', lower)
                if m:
                    profile.age = int(m.group(1))

    # ── Employment type ───────────────────────────────────────────────────────
    if profile.employment_type is None or last_asked == "employment_type":
        if any(k in lower for k in ["salaried", "private job", "government job",
                                     "work for a company", "employed by"]):
            profile.employment_type = "salaried"
        elif any(k in lower for k in ["self employed", "self-employed",
                                       "freelance", "consultant", "professional"]):
            profile.employment_type = "self_employed"
        elif any(k in lower for k in ["business owner", "own business",
                                       "proprietor", "partnership", "company owner",
                                       "businessman", "director"]):
            profile.employment_type = "business"
        elif last_asked == "employment_type":
            if "salary" in lower or "salaried" in lower[:20]:
                profile.employment_type = "salaried"
            elif "self" in lower:
                profile.employment_type = "self_employed"
            elif "business" in lower:
                profile.employment_type = "business"

    # ── Credit score ──────────────────────────────────────────────────────────
    if profile.credit_score is None or last_asked == "credit_score":
        m = re.search(r'(?:cibil|credit\s*score|score)\D{0,10}(\d{3})', lower)
        if m:
            profile.credit_score = int(m.group(1))
        elif last_asked == "credit_score":
            m = re.search(r'\b([5-9]\d{2})\b', lower)
            if m:
                profile.credit_score = int(m.group(1))

    # ── Customer name ─────────────────────────────────────────────────────────
    if profile.customer_name is None or last_asked == "customer_name":
        # Search on lowercased text; title-case the extracted name
        _NOT_A_NAME = {
            'salaried', 'self', 'employed', 'business', 'going', 'looking',
            'trying', 'planning', 'interested', 'not', 'also', 'here',
            'available', 'ready', 'working', 'earning', 'seeking', 'applying',
            'a', 'an', 'the',
        }
        m = re.search(
            r'(?:my name is|this is|call me|name\s*[:\s])\s*'
            r'([a-z]+(?:\s+[a-z]+){0,3})',
            lower,
        )
        if not m:
            m = re.search(r"(?:i am|i'm)\s+([a-z]+(?:\s+[a-z]+){0,2})", lower)
        if m:
            candidate = m.group(1).strip()
            first_word = candidate.split()[0]
            if first_word not in _NOT_A_NAME and not first_word[0].isdigit():
                profile.customer_name = candidate.title()


# ── FAQ templates (Phase 2 — no LLM) ───────────────────────────────────────

def _faq_rate(product: Optional[str]) -> str:
    rates = {
        "home_loan":     "8.50% – 9.50%",
        "personal_loan": "9.99% – 24.00%",
        "msme_loan":     "9.00% – 16.00%",
        "car_loan":      "8.75% – 10.50%",
    }
    if product and product in rates:
        return (f"Indicative {_PRODUCT_DISPLAY[product]} rate: {rates[product]} p.a. "
                f"Actual rate depends on your credit profile. "
                f"Please contact your branch for current rates.")
    return ("Indicative rates — Home: 8.50–9.50%  |  Personal: 9.99–24%  |  "
            "MSME: 9–16%  |  Car: 8.75–10.50% (all p.a.). "
            "Contact your branch for current rates.")


# ════════════════════════════════════════════════════════════════════════════
# LoanCopilotAgent
# ════════════════════════════════════════════════════════════════════════════

class LoanCopilotAgent:
    """
    Instantiate with phase=2 for rules-based (no LLM, no API key needed).
    Instantiate with phase=5 for full ReAct agent (requires OPENAI_API_KEY).
    """

    def __init__(
        self,
        phase: int = 5,
        session_id: Optional[str] = None,
        model: str = "gpt-4o",
        memory_window: int = 10,
        prompt_variant: str = "V3_COT_SAFETY",
    ):
        from agent.prompts import PROMPT_VARIANTS, SYSTEM_PROMPT
        self.phase = phase
        self.session_id = session_id or str(uuid.uuid4())
        self.state = SessionState(session_id=self.session_id)
        self.model = model
        self._executor = None
        self._prompt_variant = prompt_variant
        self._system_prompt = PROMPT_VARIANTS.get(prompt_variant, SYSTEM_PROMPT)

        # Only wire LangChain memory for Phase 3+
        if phase >= 3:
            from agent.memory import build_langchain_memory
            self.memory = build_langchain_memory(memory_window)
        else:
            self.memory = None

    # ── Public API ────────────────────────────────────────────────────────────

    _RESET_PHRASES = frozenset({
        "start over", "reset", "restart", "begin again",
        "start again", "new session", "clear session", "start fresh",
    })

    def chat(self, user_input: str) -> str:
        """Process one user turn and return the agent response."""
        self.state.turn_count += 1
        if user_input.strip().lower() in self._RESET_PHRASES:
            self.reset()
            return (
                "Sure, I've cleared our previous conversation. "
                "Let's start fresh — which loan product can I help you with today? "
                "(Home / Personal / MSME / New Car)"
            )
        if self.phase == 2:
            return self._rules_response(user_input)
        return self._llm_response(user_input)

    def reset(self) -> None:
        """Reset all session state (supports 'start over' command)."""
        self.state.reset()
        if self.memory:
            self.memory.clear()

    def inject_context(self, user_message: str, assistant_message: str) -> None:
        """Inject a pre-canned exchange into conversation memory without calling the LLM.

        Call this when a product is selected via a shortcut (UI button, terminal menu)
        and a rule-based intake prompt is shown to the user.  Syncing the exchange here
        means the LLM sees the product choice on the user's very next turn and never
        asks 'which loan type?' again.
        """
        self.state.turn_count += 1
        _extract_profile(user_message, self.state.profile)
        if self.memory:
            self.memory.chat_memory.add_user_message(user_message)
            self.memory.chat_memory.add_ai_message(assistant_message)

    # ── Phase 2: rules-based (no LLM) ────────────────────────────────────────

    def _rules_response(self, user_input: str) -> str:
        lower = user_input.lower().strip()

        # ── Guard: approval / guarantee requests ──────────────────────────────
        if any(k in lower for k in ["approve", "approval guarantee",
                                     "guarantee my", "confirm my loan", "will i get approved"]):
            return (
                "I'm unable to provide guaranteed approval. All assessments here are "
                "indicative, subject to formal credit appraisal by our team. "
                "Would you like me to run an indicative eligibility check for you?"
            )

        # ── Guard: skip / "don't know" for credit score ──────────────────────
        if (self.state.last_asked_field == "credit_score" and
                any(k in lower for k in ["skip", "don't know", "not sure",
                                          "no idea", "unknown", "cant say",
                                          "no clue", "not available"])):
            self.state.profile.credit_score = 700
            self.state.cibil_assumed = True
            return self._check_and_proceed()

        # ── Extract values from this turn ─────────────────────────────────────
        _extract_profile(user_input, self.state.profile, self.state.last_asked_field)

        # ── Detect intent ────────────────────────────────────────────────────
        intent = _detect_intent(user_input)

        if intent == "OUT_OF_SCOPE":
            return (
                "I can only assist with Home, Personal, MSME, and New Car loan queries. "
                "For other matters, please contact your nearest branch."
            )

        if intent == "FAQ":
            return self._faq_response(user_input)

        if intent == "DOCUMENTS":
            # For document checklist we only need product + employment type
            needed = [f for f in ("loan_product", "employment_type")
                      if getattr(self.state.profile, f) is None]
            if needed:
                return self._ask_specific(needed[0])
            return self._format_document_checklist()

        # ELIGIBILITY / EMI — collect full profile then run tools
        return self._check_and_proceed()

    def _check_and_proceed(self) -> str:
        """If all required fields are present, run tools.
        Otherwise ask for the next missing required field.
        Credit score is optional but disclosed before defaulting to 700."""
        missing_required = self.state.profile.missing_required_fields()
        if not missing_required:
            if self.state.profile.credit_score is None:
                # Ask with explicit disclosure rather than silently defaulting
                self.state.last_asked_field = "credit_score"
                return (
                    "I now have everything needed to run the assessment. "
                    "One important note: I will use a default CIBIL score of 700 "
                    "if you don't provide yours. This can affect both eligibility "
                    "and the indicative rate you receive — a score of 750+ generally "
                    "unlocks better rates, while a score below 700 may result in "
                    "rejection for some products.\n\n"
                    "Do you know your CIBIL score? Please share it for a more "
                    "accurate assessment, or say 'skip' to proceed with 700."
                )
            self.state.last_asked_field = None
            return self._run_rules_tools()

        # Ask for the next missing required field
        result = next_field_and_question(self.state.profile)
        if result:
            field, question = result
            self.state.last_asked_field = field
            return question
        self.state.last_asked_field = None
        return self._run_rules_tools()

    def _run_rules_tools(self) -> str:
        """Call eligibility, EMI, and document checklist tools; format combined response."""
        from tools.eligibility_checker import check_eligibility
        from tools.emi_calculator import calculate_emi
        from tools.tool_escalate import generate_escalation_summary

        p = self.state.profile
        rate_lo, rate_hi = _RATE_BANDS.get(p.loan_product, (10.0, 14.0))
        prod_name = _PRODUCT_DISPLAY.get(p.loan_product, p.loan_product)

        # 1 — Eligibility check
        elig = check_eligibility.invoke({
            "loan_product": p.loan_product,
            "monthly_income": p.monthly_income,
            "loan_amount": p.loan_amount,
            "tenure_months": p.tenure_months,
            "age": p.age,
            "employment_type": p.employment_type,
            "credit_score": p.credit_score or 700,
            "existing_emi_obligations": p.existing_emi_obligations or 0.0,
        })
        self.state.eligibility_result = elig

        lines: list[str] = []
        lines.append(f"=== Indicative Assessment — {prod_name} ===")
        if self.state.cibil_assumed:
            lines.append(f"[Note: CIBIL score assumed as 700 — share your actual score "
                         f"for a more accurate result]")
        lines.append("")

        # Escalation path
        if elig.get("escalate_to_rm"):
            self.state.escalated = True
            lines.append(f"Amount: ₹{p.loan_amount/1e5:.1f} lakh")
            esc = generate_escalation_summary.invoke({
                "customer_intent": f"{prod_name} of ₹{p.loan_amount/1e5:.1f}L",
                "loan_product": p.loan_product,
                "loan_amount": p.loan_amount,
                "monthly_income": p.monthly_income,
                "escalation_reason": elig.get("escalation_note", "Amount exceeds advisory ceiling"),
                "gender": p.gender or "",
            })
            lines.append(f"Status : ⚠  Referred to Relationship Manager")
            # esc may have validation_errors if contact details not yet collected
            # (normal in Phase 2 rules path — no contact collection in that flow)
            if esc.get("escalation_saved"):
                lines.append(f"Reason : {esc['escalation_reason']}")
                lines.append("")
                lines.append(esc["customer_message"])
            else:
                reason = elig.get("escalation_note", "Amount exceeds advisory ceiling")
                lines.append(f"Reason : {reason}")
                lines.append("")
                lines.append(
                    "Your query requires a detailed review by our Relationship Manager. "
                    "To proceed, please share your name, mobile number, and email so we "
                    "can arrange a callback within 1 business day."
                )
            lines.append("")
            lines.append("(All assessments are indicative and subject to formal credit appraisal.)")
            return "\n".join(lines)

        # Eligible / not-eligible path
        if elig["eligible"]:
            lines.append(f"Status : INDICATIVELY ELIGIBLE ✓")
            lines.append(f"FOIR   : {elig['foir']:.0%}  (limit {50 if p.monthly_income <= 100000 else 55}%)")
            lines.append(f"Rates  : {elig['indicative_rate_range']}  (indicative)")
        else:
            lines.append(f"Status : NOT ELIGIBLE ✗")
            lines.append(f"Reason : {elig['reason']}")
            lines.append("")
            lines.append("You may wish to: (a) reduce the requested amount, "
                         "(b) increase your tenure, or (c) improve your credit score. "
                         "Please visit your branch to explore options.")
            lines.append("")
            lines.append("(All assessments are indicative and subject to formal credit appraisal.)")
            return "\n".join(lines)

        # 2 — EMI range (both ends of the rate band)
        emi_lo = calculate_emi.invoke({
            "principal": p.loan_amount,
            "annual_rate_percent": rate_lo,
            "tenure_months": p.tenure_months,
        })
        emi_hi = calculate_emi.invoke({
            "principal": p.loan_amount,
            "annual_rate_percent": rate_hi,
            "tenure_months": p.tenure_months,
        })
        self.state.emi_result = {"low": emi_lo, "high": emi_hi}

        lines.append("")
        lines.append("--- EMI Estimate ---")
        lines.append(f"Loan   : ₹{p.loan_amount/1e5:.1f} lakh  |  {p.tenure_months} months"
                     f"  ({p.tenure_months//12} yrs {p.tenure_months%12} mo)")
        lines.append(f"At {rate_lo}% : ₹{emi_lo['emi']:,.0f}/month  "
                     f"(total ₹{emi_lo['total_payable']/1e5:.2f}L)")
        lines.append(f"At {rate_hi}% : ₹{emi_hi['emi']:,.0f}/month  "
                     f"(total ₹{emi_hi['total_payable']/1e5:.2f}L)")

        # 3 — Document checklist
        lines.append("")
        lines.append(self._format_document_checklist())

        lines.append("")
        lines.append("(All assessments are indicative and subject to formal credit appraisal.)")
        return "\n".join(lines)

    def _format_document_checklist(self) -> str:
        from tools.document_checklist import get_document_checklist
        p = self.state.profile
        result = get_document_checklist.invoke({
            "loan_product": p.loan_product or "home_loan",
            "employment_type": p.employment_type or "salaried",
        })
        common = "  • " + "\n  • ".join(result["common_docs"])
        specific = "  • " + "\n  • ".join(result["product_specific_docs"])
        return (
            f"--- Document Checklist "
            f"({_PRODUCT_DISPLAY.get(result['loan_product'], result['loan_product'])} "
            f"/ {result['employment_type']}) ---\n"
            f"Common:\n{common}\n"
            f"Product-specific:\n{specific}"
        )

    def _ask_specific(self, field: str) -> str:
        questions = {
            "loan_product":   "Which loan are you interested in? (Home / Personal / MSME / Car)",
            "employment_type":"Are you salaried, self-employed, or a business owner?",
            "monthly_income": "What is your approximate monthly take-home income?",
            "age":            "May I know your age?",
            "loan_amount":    "How much would you like to borrow?",
            "tenure_months":  "Over how many months/years would you like to repay?",
            "credit_score":   "Do you know your approximate CIBIL credit score? (say 'skip' if unsure)",
        }
        self.state.last_asked_field = field
        return questions.get(field, f"Could you tell me your {field.replace('_', ' ')}?")

    def _faq_response(self, text: str) -> str:
        lower = text.lower()
        if any(k in lower for k in ["interest rate", "rate of interest", "what.*rate",
                                     "rate?", "current rate"]):
            return _faq_rate(self.state.profile.loan_product)
        if any(k in lower for k in ["processing fee", "charges", "how much.*fee"]):
            return ("Processing fees are typically 0.5% – 2% of the loan amount "
                    "(minimum and maximum caps apply). Contact your branch for the exact structure.")
        if any(k in lower for k in ["how long", "processing time", "how many days",
                                     "turnaround", "when will"]):
            return ("Standard loans are processed in 3–7 business days. "
                    "Complex or high-value cases may take 10–15 business days.")
        if "foir" in lower:
            return ("FOIR (Fixed Obligation to Income Ratio) is total monthly EMI obligations "
                    "divided by net monthly income. The bank's limit is 50% "
                    "(55% for income > ₹1 lakh/month).")
        if any(k in lower for k in ["minimum salary", "minimum income", "eligibility criteria"]):
            return ("Minimum income norms vary by product. As a guide: "
                    "Home Loan — ₹25,000/month (salaried); "
                    "Personal Loan — ₹30,000/month; "
                    "Car Loan — ₹20,000/month. "
                    "Final eligibility is determined by FOIR, credit score, and other factors.")
        return ("I can help with Home, Personal, MSME, and Car loans. "
                "Ask me about eligibility, EMI estimates, documents, rates, or processing fees.")

    # ── Phase 3+: LLM-backed ─────────────────────────────────────────────────

    def _get_llm(self):
        """Return ChatOpenAI — supports custom base URL for Vocarium / other providers."""
        from langchain_openai import ChatOpenAI
        from deployment.config import OPENAI_API_KEY, OPENAI_BASE_URL
        kwargs: dict = {"model": self.model, "temperature": 0}
        if OPENAI_API_KEY:
            kwargs["openai_api_key"] = OPENAI_API_KEY
        if OPENAI_BASE_URL:
            kwargs["openai_api_base"] = OPENAI_BASE_URL
        return ChatOpenAI(**kwargs)

    def _get_callbacks(self) -> list:
        """Langfuse callback list; empty if Langfuse is not configured."""
        callbacks = []
        try:
            from monitoring.langfuse_logger import get_langfuse_callback
            cb = get_langfuse_callback(
                session_id=self.session_id,
                tags=[f"phase_{self.phase}", self._prompt_variant],
            )
            if cb:
                callbacks.append(cb)
        except Exception:
            pass
        return callbacks

    def _llm_response(self, user_input: str) -> str:
        """Phase 3–4: simple LLM chain.  Phase 5+: ReAct executor with tools."""
        if self.phase >= 5:
            return self._executor_response(user_input)
        return self._chain_response(user_input)

    def _chain_response(self, user_input: str) -> str:
        """Phase 3–4: direct ChatOpenAI call with sliding-window conversation memory."""
        from langchain_core.messages import SystemMessage, HumanMessage

        messages = [SystemMessage(content=self._system_prompt)]
        if self.memory:
            messages.extend(self.memory.chat_memory.messages)

        # Phase 4+: inject retrieved policy chunks as a grounding message
        # immediately before the user turn so the LLM prioritises it.
        if self.phase >= 4:
            try:
                from retrieval.retriever import retrieve
                docs = retrieve(user_input)
                if docs:
                    context_block = "\n\n".join(
                        f"[Source: {d.metadata.get('source', 'policy')}]\n{d.page_content}"
                        for d in docs
                    )
                    messages.append(HumanMessage(content=(
                        "POLICY CONTEXT FOR YOUR NEXT RESPONSE — treat these excerpts as "
                        "ground truth. Use specific figures (rates, limits, fees) from this "
                        "context in your answer. Do not say 'not specified' if a figure "
                        "appears below.\n\n" + context_block
                    )))
            except Exception:
                pass  # ChromaDB not built yet; silently fall back to no-RAG

        messages.append(HumanMessage(content=user_input))

        try:
            llm = self._get_llm()
            response = llm.invoke(messages, config={"callbacks": self._get_callbacks()})
        except Exception as exc:
            return (
                "I'm sorry, I encountered an issue processing your request. "
                f"Please try again. ({type(exc).__name__})"
            )

        if self.memory:
            self.memory.chat_memory.add_user_message(user_input)
            self.memory.chat_memory.add_ai_message(response.content)

        return response.content

    def _executor_response(self, user_input: str) -> str:
        """Phase 5+: invoke the LangGraph tool-calling agent.

        LangChain 1.3.x uses create_agent() which returns a LangGraph
        CompiledStateGraph. Input/output use the messages protocol:
          input  → {"messages": [*history, HumanMessage(user_input)]}
          output → {"messages": [..., AIMessage(final_response)]}
        Memory is managed manually here after each turn.
        """
        from langchain_core.messages import HumanMessage

        agent = self._get_executor()
        history = self.memory.chat_memory.messages if self.memory else []

        try:
            result = agent.invoke(
                {"messages": [*history, HumanMessage(content=user_input)]},
                config={"callbacks": self._get_callbacks()},
            )
            # Last message in the output list is the final AI response
            response_text = result["messages"][-1].content
        except Exception as exc:
            return (
                "I'm sorry, I encountered an issue processing your request. "
                f"Please try again. ({type(exc).__name__})"
            )

        # Manually update sliding-window memory so history grows across turns
        if self.memory:
            self.memory.chat_memory.add_user_message(user_input)
            self.memory.chat_memory.add_ai_message(response_text)

        # Keep SessionState.profile in sync so phase6 verification and
        # the Phase 2 fallback path always have an up-to-date profile.
        _extract_profile(user_input, self.state.profile)

        # Phase 7: score any policy violations in Langfuse (log-only, don't block)
        try:
            from policy_rlhf.policy_checker import check_response as _check_policy
            violations = _check_policy(response_text)
            if violations:
                from monitoring.langfuse_logger import score_session
                hex_id = self.session_id.replace("-", "").lower()
                score_session(
                    trace_id=hex_id,
                    score_name="policy_compliance",
                    value=0.0,
                    comment=f"Violations: {[v['rule_id'] for v in violations]}",
                )
        except Exception:
            pass

        # Attach full conversation history to any escalation saved this turn
        try:
            self._try_attach_conversation(result["messages"])
        except Exception:
            pass

        return response_text

    def _try_attach_conversation(self, messages) -> None:
        """Scan the turn's messages for a successful generate_escalation_summary
        call and, if found, write the full conversation history into that record."""
        import json as _json
        from langchain_core.messages import ToolMessage
        for msg in messages:
            if not isinstance(msg, ToolMessage):
                continue
            if getattr(msg, "name", None) != "generate_escalation_summary":
                continue
            try:
                content = msg.content
                if isinstance(content, str):
                    tool_result = _json.loads(content)
                elif isinstance(content, list):
                    text = next((c["text"] for c in content if c.get("type") == "text"), "")
                    tool_result = _json.loads(text) if text else {}
                else:
                    tool_result = content if isinstance(content, dict) else {}
                if isinstance(tool_result, dict) and tool_result.get("escalation_saved"):
                    esc_id = tool_result.get("escalation_id")
                    if esc_id:
                        self._attach_history_to_escalation(esc_id)
            except Exception:
                pass

    def _attach_history_to_escalation(self, escalation_id: str) -> None:
        """Append the current conversation turns to an escalation record."""
        import json as _json
        from deployment.config import DATA_DIR
        path = DATA_DIR / "rlhf" / "escalations.json"
        if not path.exists():
            return
        try:
            records = _json.loads(path.read_text(encoding="utf-8"))
            history = []
            if self.memory:
                for msg in self.memory.chat_memory.messages:
                    role = "user" if msg.type == "human" else "assistant"
                    content = str(msg.content)
                    if len(content) > 600:
                        content = content[:600] + "…"
                    history.append({"role": role, "content": content})
            for r in records:
                if r.get("escalation_id") == escalation_id:
                    r["conversation_history"] = history
                    r["session_id"] = r.get("session_id") or self.session_id
                    break
            path.write_text(_json.dumps(records, indent=2, ensure_ascii=False))
        except Exception:
            pass

    def _get_executor(self):
        if self._executor is None:
            self._executor = self._build_executor()
        return self._executor

    def _build_executor(self):
        """Build a LangGraph tool-calling agent with all 5 tools (Phase 5+).

        LangChain 1.3.x create_agent() wraps a LangGraph ReAct loop that uses
        OpenAI's function-calling API: the LLM decides which tool to call,
        the graph executes it, and loops until no more tool calls are needed.
        This is equivalent to the classic AgentExecutor ReAct pattern but more
        reliable — no text parsing, structured tool calls via the OpenAI API.
        """
        import os
        from langchain.agents import create_agent
        from tools.tool_registry import get_all_tools, get_mcp_tools

        use_mcp = os.getenv("USE_MCP", "false").lower() == "true"
        tools = get_mcp_tools() if use_mcp else get_all_tools()
        llm   = self._get_llm()

        # Inject the real session UUID so the LLM can pass it as session_id
        # when calling generate_escalation_summary.  Without this the LLM has
        # no way to know the value and passes a placeholder like "agent.session_id".
        hex_sid = self.session_id.replace("-", "").lower()
        system_prompt = self._system_prompt.replace(
            "(available as agent.session_id)",
            f'— use this exact value: "{hex_sid}"',
        )

        return create_agent(llm, tools, system_prompt=system_prompt)
