"""
Run 8 scripted agent sessions to populate Langfuse traces and the RM Dashboard.

Sessions 1-6: Normal conversations (eligibility, EMI, rates, documents).
Sessions 7-8: Escalation scenarios (amount exceeds product ceiling).

Run from project root:
    python scripts/seed_sessions.py
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Use gpt-4o-mini to stay within the per-request cost cap ($0.25).
# The full V3 system prompt + 5 tool definitions push gpt-4o calls slightly over
# the limit. gpt-4o-mini is ~15x cheaper per token and handles structured
# tool-calling (including generate_escalation_summary) reliably.
os.environ["AGENT_MODEL"] = "gpt-4o-mini"

from agent.core_agent import LoanCopilotAgent
from monitoring.langfuse_logger import flush
from deployment.config import DATA_DIR

BOLD  = "\033[1m"
CYAN  = "\033[96m"
GREEN = "\033[92m"
YELLOW= "\033[93m"
RED   = "\033[91m"
RESET = "\033[0m"

TURN_DELAY = 1.5   # seconds between turns within a session
SESSION_DELAY = 3  # seconds between sessions


# ── Helpers ───────────────────────────────────────────────────────────────────

def run_session(label: str, turns: list[str], is_escalation: bool = False) -> dict:
    """Drive one scripted conversation. Returns session info dict."""
    print(f"\n{'─'*64}")
    tag = f"  {YELLOW}[ESCALATION]{RESET}" if is_escalation else ""
    print(f"{BOLD}{label}{RESET}{tag}")
    print(f"{'─'*64}")

    agent = LoanCopilotAgent(phase=5, model="gpt-4o-mini")
    hex_id = agent.session_id.replace("-", "").lower()
    print(f"  session_id : {agent.session_id}")
    print(f"  hex_id     : {hex_id}")

    success_turns = 0
    for i, user_msg in enumerate(turns, 1):
        print(f"\n{CYAN}Turn {i} →{RESET} {user_msg[:110]}{'…' if len(user_msg)>110 else ''}")
        try:
            response = agent.chat(user_msg)
            print(f"{GREEN}Copilot:{RESET} {response[:400]}{'…' if len(response)>400 else ''}")
            success_turns += 1
        except Exception as exc:
            print(f"{RED}ERROR on turn {i}: {exc}{RESET}")
            break
        if i < len(turns):
            time.sleep(TURN_DELAY)

    status = GREEN + "✓" + RESET if success_turns == len(turns) else RED + "✗ (partial)" + RESET
    print(f"\n  Status: {status}  ({success_turns}/{len(turns)} turns)")
    return {
        "label": label,
        "session_id": agent.session_id,
        "hex_id": hex_id,
        "turns_ok": success_turns,
        "turns_total": len(turns),
        "is_escalation": is_escalation,
    }


# ── Clean slate: wipe existing records ───────────────────────────────────────

esc_path = DATA_DIR / "rlhf" / "escalations.json"
if esc_path.exists():
    existing = json.loads(esc_path.read_text(encoding="utf-8"))
    print(f"Clearing {len(existing)} existing escalation record(s) for a clean demo run.")
esc_path.write_text("[]", encoding="utf-8")
print("escalations.json reset to [].\n")


# ── Session definitions ───────────────────────────────────────────────────────

sessions = []

# ── 1. Home Loan — Eligible, moderate ask ────────────────────────────────────
sessions.append(run_session(
    "Session 1 — Rohan Mehta | Home Loan ₹50L | Eligible",
    [
        "Hi, I am looking for a home loan of 50 lakhs to buy a 2BHK flat in Hyderabad.",
        "I am Rohan Mehta, 35 years old, salaried at Infosys. "
        "My monthly take-home is 1.2 lakhs and CIBIL score is 750. "
        "I need the loan for 20 years.",
        "What documents will I need to submit for this home loan?",
    ],
))
time.sleep(SESSION_DELAY)

# ── 2. Personal Loan — EMI + rate inquiry ────────────────────────────────────
sessions.append(run_session(
    "Session 2 — Deepika Nair | Personal Loan ₹5L | EMI Query",
    [
        "I need a personal loan of 5 lakhs for home renovation. "
        "What is the interest rate range for personal loans?",
        "I am Deepika Nair, 28 years old, salaried. "
        "My monthly income is 60,000 and CIBIL is 720. "
        "I would prefer a 3-year tenure. What would my EMI be?",
        "Are there any processing fees I should know about for personal loans?",
    ],
))
time.sleep(SESSION_DELAY)

# ── 3. MSME Loan — Low CIBIL, ineligible ─────────────────────────────────────
sessions.append(run_session(
    "Session 3 — Sanjay Gupta | MSME Loan ₹30L | Low CIBIL",
    [
        "I own a grocery shop and want an MSME loan of 30 lakhs "
        "to expand my business. I have been running the shop for 5 years.",
        "I am Sanjay Gupta, 42 years old. My monthly income is 80,000. "
        "My CIBIL score is around 580. Tenure 5 years.",
        "My CIBIL is low because of a missed payment 2 years ago. "
        "How can I improve it to qualify for this loan in the future?",
    ],
))
time.sleep(SESSION_DELAY)

# ── 4. Car Loan — Eligible, EMI calculation ──────────────────────────────────
sessions.append(run_session(
    "Session 4 — Kavitha Krishnan | Car Loan ₹8L | EMI Calc",
    [
        "Hi, I want a car loan to buy a Maruti Suzuki Baleno. "
        "The on-road price is about 10 lakhs and I want to take a loan of 8 lakhs.",
        "I am Kavitha Krishnan, 30 years old, salaried at a private firm. "
        "Monthly income 85,000, CIBIL score 770. "
        "I prefer a 5-year tenure. Can you calculate my EMI?",
        "What is the indicative interest rate range for car loans? "
        "Does the rate change based on my CIBIL score?",
    ],
))
time.sleep(SESSION_DELAY)

# ── 5. Home Loan — Full eligibility with existing EMI ────────────────────────
sessions.append(run_session(
    "Session 5 — Amit Shah | Home Loan ₹1.2 Cr | Existing EMI",
    [
        "I want to apply for a home loan of 1.2 crores for a property in Mumbai.",
        "I am Amit Shah, 40 years old, salaried at TCS. "
        "Monthly take-home is 2 lakhs, CIBIL score 800. "
        "I also have an existing car loan EMI of 15,000 per month. "
        "Tenure 25 years.",
        "Given my existing EMI, am I still eligible? What would my FOIR be?",
        "What indicative rate range can I expect and what EMI should I plan for?",
    ],
))
time.sleep(SESSION_DELAY)

# ── 6. Personal Loan — Eligible, document checklist ─────────────────────────
sessions.append(run_session(
    "Session 6 — Neha Joshi | Personal Loan ₹10L | Document Checklist",
    [
        "I need a personal loan of 10 lakhs. I am a salaried employee, "
        "32 years old, monthly income 1 lakh, CIBIL 740. Tenure 4 years.",
        "Am I eligible for this loan? What would be my approximate EMI?",
        "Can you give me the complete document checklist for a salaried "
        "personal loan applicant?",
    ],
))
time.sleep(SESSION_DELAY)

# ── 7. ESCALATION — Car Loan ₹28L > ₹20L ceiling ────────────────────────────
sessions.append(run_session(
    "Session 7 — Arjun Sharma | Car Loan ₹28L | ESCALATION",
    [
        "Hi, I want a new car loan for a Toyota Fortuner. "
        "The on-road price is 28 lakhs and I need the full amount financed.",
        "I am 32 years old, salaried at Wipro, monthly income 95,000, "
        "CIBIL score 740. I want a 7-year tenure.",
        "My name is Arjun Sharma. My mobile number is 9845012345 and "
        "email is arjun.sharma@wipro.com. I am male and available "
        "weekdays between 11 AM and 1 PM.",
        "What documents should I prepare before the RM calls me?",
    ],
    is_escalation=True,
))
time.sleep(SESSION_DELAY)

# ── 8. ESCALATION — Home Loan ₹2.2 Cr > ₹1.5 Cr ceiling ─────────────────────
sessions.append(run_session(
    "Session 8 — Meera Iyer | Home Loan ₹2.2 Cr | ESCALATION",
    [
        "I need a home loan of 2.2 crores to buy a 3BHK apartment in Pune. "
        "Tenure 25 years. My monthly income is 1.8 lakhs, age 38, "
        "salaried with HDFC Bank, CIBIL score 785.",
        "Meera Iyer, phone 7654321098, email meera.iyer@hdfcbank.com, "
        "female, prefer callbacks on Saturday mornings.",
        "Can I add my husband as a co-applicant to qualify for more? "
        "And what documents should we both prepare?",
    ],
    is_escalation=True,
))


# ── Flush Langfuse traces ─────────────────────────────────────────────────────
print(f"\n{'─'*64}")
print("Flushing Langfuse traces…")
flush()
time.sleep(3)  # allow flush to complete
print(f"{GREEN}✓ Traces flushed.{RESET}")


# ── Final report ──────────────────────────────────────────────────────────────
print(f"\n{'═'*64}")
print(f"{BOLD}SESSION REPORT{RESET}")
print(f"{'═'*64}")
for s in sessions:
    mark = YELLOW + "[ESC]" + RESET if s["is_escalation"] else "     "
    ok_marker = GREEN + "✓" + RESET if s["turns_ok"] == s["turns_total"] else RED + "✗" + RESET
    print(f"  {mark} {ok_marker}  {s['label'][:48]:<48}  sid={s['hex_id'][:16]}…")

# Show escalation records saved
data = json.loads(esc_path.read_text(encoding="utf-8"))
print(f"\nEscalation records saved to escalations.json: {len(data)}")
for r in data:
    sid = r.get("session_id", "")
    hex_check = sid.replace("-","").lower() if sid else ""
    sid_valid = len(hex_check) == 32 and all(c in "0123456789abcdef" for c in hex_check)
    print(f"  {r['escalation_id']} | {r.get('customer_name','?'):22s} | "
          f"{'✓ real sid' if sid_valid else '✗ no sid':12s} | "
          f"{len(r.get('conversation_history',[]))} turns")

print(f"\n{GREEN}Done.{RESET}")
print(f"\nView traces at: https://cloud.langfuse.com")
for s in sessions:
    if s["is_escalation"]:
        print(f"  {s['label'].split('|')[0].strip():35s}  "
              f"https://cloud.langfuse.com/traces/{s['hex_id']}")
