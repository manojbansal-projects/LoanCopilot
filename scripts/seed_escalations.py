"""
Seed two real escalation sessions for the RM Dashboard demo.

Scenario A — Car Loan ₹28L  (ceiling ₹20L) — Arjun Sharma
Scenario B — Home Loan ₹2.2 Cr (ceiling ₹1.5 Cr) — Meera Iyer

Each session drives the Phase-5 LLM agent turn-by-turn so that:
  1. A real OpenAI / Langfuse trace is created per session.
  2. generate_escalation_summary is called with the correct session_id.
  3. The escalation record is appended to data/rlhf/escalations.json.

Run from the project root:
    python scripts/seed_escalations.py
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.core_agent import LoanCopilotAgent
from monitoring.langfuse_logger import flush
from deployment.config import DATA_DIR

BOLD  = "\033[1m"
CYAN  = "\033[96m"
GREEN = "\033[92m"
RED   = "\033[91m"
RESET = "\033[0m"


def _clean_stale(name: str) -> None:
    """Remove any previously seeded record for this customer name."""
    path = DATA_DIR / "rlhf" / "escalations.json"
    if not path.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    before = len(data)
    data = [r for r in data if r.get("customer_name") != name]
    if len(data) < before:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        print(f"  (removed {before - len(data)} stale record(s) for '{name}')")


def run_session(label: str, turns: list[str]) -> str:
    """Drive one scripted conversation; return session_id."""
    print(f"\n{'─'*60}")
    print(f"{BOLD}{label}{RESET}")
    print(f"{'─'*60}")

    agent = LoanCopilotAgent(phase=5)
    print(f"  session_id : {agent.session_id}")
    print(f"  hex_id     : {agent.session_id.replace('-','').lower()}")

    for i, user_msg in enumerate(turns, 1):
        print(f"\n{CYAN}Turn {i} →{RESET} {user_msg[:100]}{'…' if len(user_msg)>100 else ''}")
        try:
            response = agent.chat(user_msg)
            print(f"{GREEN}Copilot:{RESET} {response[:350]}{'…' if len(response)>350 else ''}")
        except Exception as exc:
            print(f"{RED}ERROR on turn {i}: {exc}{RESET}")
            break

    return agent.session_id


# ── Remove stale records from previous runs ───────────────────────────────────
_clean_stale("Arjun Sharma")
_clean_stale("Meera Iyer")

# ── Scenario A: Car Loan ₹28L — exceeds ₹20L ceiling ────────────────────────
session_a = run_session(
    "Scenario A — Car Loan ₹28 Lakhs (ceiling ₹20L) — Arjun Sharma",
    [
        "Hi, I want a new car loan for a Toyota Fortuner. "
        "The on-road price is ₹28 lakhs and I need the full amount.",
        "I am 32 years old, salaried at Wipro, monthly income ₹95,000, "
        "CIBIL score 740. Tenure 7 years.",
        # Agent should detect escalation (₹28L > ₹20L) and ask for contact
        "My name is Arjun Sharma, mobile 9845012345, "
        "email arjun.sharma@wipro.com, male, "
        "available weekdays between 11 AM and 1 PM.",
    ],
)

# ── Scenario B: Home Loan ₹2.2 Cr — exceeds ₹1.5 Cr ceiling ─────────────────
session_b = run_session(
    "Scenario B — Home Loan ₹2.2 Crores (ceiling ₹1.5 Cr) — Meera Iyer",
    [
        "I need a home loan of ₹2.2 crores to buy a 3BHK in Pune. "
        "Tenure 25 years. My monthly income is ₹1.8 lakhs, age 38, "
        "salaried with HDFC Bank, CIBIL 785.",
        # Agent should detect escalation (₹2.2 Cr > ₹1.5 Cr) and ask for contact
        "Meera Iyer, phone 7654321098, email meera.iyer@hdfcbank.com, "
        "female, prefer callbacks on Saturday mornings.",
    ],
)

# ── Flush Langfuse and report ─────────────────────────────────────────────────
print(f"\n{'─'*60}")
print("Flushing Langfuse traces…")
flush()
print(f"{GREEN}✓ Done.{RESET}")

# Show what was saved
path = DATA_DIR / "rlhf" / "escalations.json"
data = json.loads(path.read_text(encoding="utf-8"))
print(f"\nEscalation records in escalations.json: {len(data)}")
for r in data:
    sid = r.get("session_id", "")
    status = "✓ real sid" if (sid and sid != "current_session_id" and len(sid.replace("-","")) == 32) else "✗ missing/fake sid"
    print(f"  {r['escalation_id']} | {r.get('customer_name','?'):20s} | {status}")
