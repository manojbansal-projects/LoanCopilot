"""Session state and LangChain memory wrappers (Phase 6)."""
from dataclasses import dataclass, field
from typing import Optional
try:
    from langchain_classic.memory import ConversationBufferWindowMemory
except ImportError:
    from langchain.memory import ConversationBufferWindowMemory  # type: ignore


@dataclass
class CustomerProfile:
    """Accumulated customer data collected during the conversation."""
    loan_product: Optional[str] = None        # home / personal / msme / car
    monthly_income: Optional[float] = None    # net take-home, INR
    age: Optional[int] = None
    gender: Optional[str] = None             # male / female / other
    employment_type: Optional[str] = None     # salaried / self_employed / business
    credit_score: Optional[int] = None
    loan_amount: Optional[float] = None       # INR
    tenure_months: Optional[int] = None
    customer_name: Optional[str] = None       # first or full name for escalation
    # Extended fields (collected progressively)
    existing_emi_obligations: Optional[float] = None
    property_value: Optional[float] = None    # for home loan LTV
    business_vintage_years: Optional[int] = None  # for MSME

    def missing_required_fields(self) -> list[str]:
        """Return field names that are still None for a basic eligibility check."""
        required = ["loan_product", "loan_amount", "tenure_months",
                    "monthly_income", "age", "employment_type"]
        return [f for f in required if getattr(self, f) is None]

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class SessionState:
    """Full per-session state container."""
    session_id: str
    profile: CustomerProfile = field(default_factory=CustomerProfile)
    turn_count: int = 0
    escalated: bool = False
    eligibility_result: Optional[dict] = None
    emi_result: Optional[dict] = None
    last_asked_field: Optional[str] = None  # tracks which field was most recently asked
    cibil_assumed: bool = False  # True when we defaulted to 700 without user input

    def reset(self) -> None:
        """Clear all collected state (e.g. on 'start over' user command)."""
        self.profile = CustomerProfile()
        self.turn_count = 0
        self.escalated = False
        self.eligibility_result = None
        self.emi_result = None
        self.last_asked_field = None
        self.cibil_assumed = False


def build_langchain_memory(window: int = 10) -> ConversationBufferWindowMemory:
    """Return a sliding-window buffer memory for the LangChain agent."""
    return ConversationBufferWindowMemory(
        k=window,
        memory_key="chat_history",
        return_messages=True,
    )
