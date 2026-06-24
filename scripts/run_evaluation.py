"""
Phase 9 evaluation runner.

Usage:
    python scripts/run_evaluation.py --suite rag
    python scripts/run_evaluation.py --suite tools
    python scripts/run_evaluation.py --suite safety
    python scripts/run_evaluation.py --suite all
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
from agent.core_agent import LoanCopilotAgent
from evaluation.test_harness import run_rag_eval, run_tool_eval, run_safety_eval


def _print_rag_summary(result: dict) -> None:
    if "error" in result:
        print(f"  ERROR: {result['error']}")
        return
    print(f"\n  RAG Evaluation Summary")
    print(f"  {'─' * 40}")
    print(f"  Questions : {result['total']}")
    print(f"  Passed    : {result['passed']}  |  Failed : {result['failed']}")
    print(f"  Pass rate : {result['pass_rate'] * 100:.0f}%  (target ≥ 70%)")
    print(f"  Avg faithfulness : {result['avg_faithfulness']:.2f}")
    print(f"  Avg relevance    : {result['avg_relevance']:.2f}")
    if result["failed"]:
        print(f"\n  Failing questions:")
        for r in result["results"]:
            if not r["passed"]:
                print(f"    [{r['id']}] F={r['faithfulness']:.2f} R={r['relevance']:.2f} "
                      f"safe={r['safety_compliant']}  — {r['reasoning']}")


def _print_tool_summary(result: dict) -> None:
    if "error" in result:
        print(f"  ERROR: {result['error']}")
        return
    print(f"\n  Tool Selection Summary")
    print(f"  {'─' * 40}")
    print(f"  Scenarios : {result['total']}")
    print(f"  Correct   : {result['correct']}  |  Incorrect : {result['incorrect']}")
    print(f"  Accuracy  : {result['overall_accuracy'] * 100:.0f}%  (target ≥ 80%)")
    print(f"\n  Per-tool breakdown:")
    for tool, stats in result["per_tool"].items():
        bar = "✓" * stats["correct"] + "✗" * (stats["total"] - stats["correct"])
        print(f"    {tool:<30} {stats['correct']}/{stats['total']}  [{bar}]")


def _print_safety_summary(result: dict) -> None:
    print(f"\n  Safety Gate Summary")
    print(f"  {'─' * 40}")
    print(f"  Prompts   : {result['total']}")
    print(f"  Blocked   : {result['blocked']}  |  Passed through : {result['not_blocked']}")
    print(f"  Block rate: {result['block_rate'] * 100:.0f}%  (target = 100%)")
    if result["not_blocked"] > 0:
        print(f"\n  Prompts NOT blocked (investigate!):")
        for r in result["results"]:
            if not r["blocked"]:
                print(f"    [{r['id']}] intent={r['intent']}  stage={r['actual_stage']}")
                print(f"         \"{r['prompt']}\"")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase 9 evaluation suites")
    parser.add_argument(
        "--suite",
        choices=["rag", "tools", "safety", "all"],
        default="all",
        help="Which evaluation suite to run",
    )
    args = parser.parse_args()

    agent = LoanCopilotAgent(phase=5)

    print("=" * 60)
    print("  Loan Copilot — Phase 9 Evaluation")
    print("=" * 60)

    if args.suite in ("rag", "all"):
        print("\n[Suite 1/3] RAG Quality — 20 questions, LLM-as-judge")
        result = run_rag_eval(agent.chat)
        _print_rag_summary(result)

    if args.suite in ("tools", "all"):
        print("\n[Suite 2/3] Tool Selection — 30 scenarios")
        result = run_tool_eval(agent.chat)
        _print_tool_summary(result)

    if args.suite in ("safety", "all"):
        print("\n[Suite 3/3] Safety Gate — 5 adversarial prompts")
        result = run_safety_eval()
        _print_safety_summary(result)

    print("\n" + "=" * 60)
    print("  Evaluation complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
