"""
Phase 9 evaluation runner.

Usage:
    python scripts/run_evaluation.py --suite rag
    python scripts/run_evaluation.py --suite tools
    python scripts/run_evaluation.py --suite safety
    python scripts/run_evaluation.py --suite all
"""
import argparse
from agent.core_agent import LoanCopilotAgent
from evaluation.test_harness import run_rag_eval, run_tool_eval, run_safety_eval


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", choices=["rag", "tools", "safety", "all"], default="all")
    args = parser.parse_args()

    agent = LoanCopilotAgent(phase=5)

    if args.suite in ("rag", "all"):
        result = run_rag_eval(agent.chat)
        print("RAG eval:", result)

    if args.suite in ("tools", "all"):
        result = run_tool_eval(agent.chat)
        print("Tool eval:", result)

    if args.suite in ("safety", "all"):
        result = run_safety_eval(agent.chat)
        print("Safety eval:", result)


if __name__ == "__main__":
    main()
