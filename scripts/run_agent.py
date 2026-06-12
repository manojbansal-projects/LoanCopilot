"""
CLI entry point — interactive loan copilot session.

Usage (from project root):
    python scripts/run_agent.py [--phase 2]
    python scripts/run_agent.py --no-feedback
"""
import argparse, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.core_agent import LoanCopilotAgent
from monitoring.langfuse_logger import flush


# ── Per-turn: thumbs up / down ────────────────────────────────────────────────
def _prompt_thumbs(agent: LoanCopilotAgent, response: str) -> None:
    """Quick thumbs signal after each response.  👍 = 4★,  👎 = 2★."""
    try:
        raw = input("  Helpful? [y/n or Enter to skip]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return
    if raw not in ("y", "n"):
        return

    rating = 4 if raw == "y" else 2
    thumb  = "👍" if raw == "y" else "👎"

    from policy_rlhf.feedback_collector import record_feedback
    record_feedback(
        session_id=agent.session_id,
        turn=agent.state.turn_count,
        agent_response=response,
        rating=rating,
        feedback_type="per_turn",
    )
    try:
        from monitoring.langfuse_logger import score_session
        score_session(
            trace_id=agent.session_id.replace("-", "").lower(),
            score_name="user_feedback",
            value=(rating - 1) / 4,
            comment=f"per-turn thumbs {thumb}",
        )
    except Exception:
        pass
    print(f"  {thumb}  Got it.\n")


# ── Session exit: overall 1-5 rating + optional comment ───────────────────────
def _prompt_session_rating(agent: LoanCopilotAgent) -> None:
    """Ask for an overall session rating when the user quits."""
    if agent.state.turn_count == 0:
        return  # nothing to rate
    print("\n─────────────────────────────────────────")
    print("  Before you go — how was this conversation overall?")
    try:
        raw = input("  Overall rating [1-5] or Enter to skip: ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if not raw:
        return
    try:
        rating = int(raw)
    except ValueError:
        print("  (Invalid — skipped)")
        return
    if not 1 <= rating <= 5:
        print("  (Must be 1–5 — skipped)")
        return

    try:
        comment = input("  Any comments? (Enter to skip): ").strip()
    except (EOFError, KeyboardInterrupt):
        comment = ""

    from policy_rlhf.feedback_collector import record_feedback
    record_feedback(
        session_id=agent.session_id,
        turn=agent.state.turn_count,
        agent_response="[session-level rating]",
        rating=rating,
        comment=comment,
        feedback_type="session",
    )
    try:
        from monitoring.langfuse_logger import score_session
        score_session(
            trace_id=agent.session_id.replace("-", "").lower(),
            score_name="session_rating",
            value=(rating - 1) / 4,
            comment=f"{rating}/5 stars" + (f': "{comment}"' if comment else ""),
        )
    except Exception:
        pass

    stars = "★" * rating + "☆" * (5 - rating)
    print(f"  [{stars}] Thank you for your feedback!")
    print("─────────────────────────────────────────")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Loan Origination Copilot CLI")
    parser.add_argument("--phase", type=int, default=5, help="Agent phase (2–8)")
    parser.add_argument("--no-feedback", action="store_true",
                        help="Disable all feedback prompts")
    args = parser.parse_args()

    agent = LoanCopilotAgent(phase=args.phase)
    feedback_on = not args.no_feedback

    print(f"\n{'─'*56}")
    print(f"  🏦  Loan Origination Copilot  [Phase {args.phase}]")
    print(f"{'─'*56}")
    print(
        "\nCopilot: Welcome! Which loan product can I help you with today?\n\n"
        "  🏠  Home Loan       (₹5L – ₹5 Cr, up to 30 years)\n"
        "  🚗  New Car Loan    (₹3L – ₹20L, up to 7 years)\n"
        "  💼  MSME Loan       (₹50K – ₹10 Cr, up to 15 years)\n"
        "  💳  Personal Loan   (₹50K – ₹40L, up to 5 years)\n\n"
        "  Type a product name to begin, or ask any loan-related question.\n"
        "  Type 'quit' to exit, 'reset' to start over.\n"
    )
    if feedback_on:
        print("  Tip: after each response type y/n to give a quick thumbs signal (or Enter to skip).\n")

    last_response = ""
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            if feedback_on:
                _prompt_session_rating(agent)
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "bye"):
            if feedback_on:
                _prompt_session_rating(agent)
            print("Goodbye!")
            break
        if user_input.lower() in ("reset", "start over"):
            agent.reset()
            last_response = ""
            print("[Session reset]\n")
            continue

        last_response = agent.chat(user_input)
        print(f"\nCopilot: {last_response}\n")

        if feedback_on:
            _prompt_thumbs(agent, last_response)

    flush()


if __name__ == "__main__":
    main()
