"""
CLI entry point — interactive loan copilot session.

Usage (from project root):
    python scripts/run_agent.py [--phase 2]
"""
import argparse, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.core_agent import LoanCopilotAgent
from monitoring.langfuse_logger import flush


def main():
    parser = argparse.ArgumentParser(description="Loan Origination Copilot CLI")
    parser.add_argument("--phase", type=int, default=5, help="Agent phase (2–8)")
    args = parser.parse_args()

    agent = LoanCopilotAgent(phase=args.phase)
    print(f"\n[Loan Copilot — Phase {args.phase}]  Type 'quit' to exit, 'reset' to start over.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "bye"):
            print("Goodbye!")
            break
        if user_input.lower() in ("reset", "start over"):
            agent.reset()
            print("[Session reset]\n")
            continue

        response = agent.chat(user_input)
        print(f"\nCopilot: {response}\n")

    flush()


if __name__ == "__main__":
    main()
