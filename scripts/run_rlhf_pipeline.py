"""
Phase 7 RLHF pipeline — analyse feedback, update adaptive policy, log signals.

Usage:
    python scripts/run_rlhf_pipeline.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from policy_rlhf.policy_updater import (
    analyse_feedback, update_adaptive_policy, _load_adaptive_policy,
)
from policy_rlhf.feedback_collector import _load_store
import json


def main():
    # ── Full record table ─────────────────────────────────────────────────────
    store = _load_store()
    print(f"Total feedback records: {len(store)}")
    if store:
        print()
        print(f"{'#':<4} {'Stars':<8} {'Turn':<6} {'Session':<10} {'Comment'}")
        print("-" * 72)
        for i, r in enumerate(store, 1):
            stars = "★" * r["rating"] + "☆" * (5 - r["rating"])
            comment = r.get("comment") or "(none)"
            session = r.get("session_id", "")[:8]
            turn = r.get("turn", "-")
            print(f"{i:<4} {stars:<8} {str(turn):<6} {session:<10} {comment}")

    # ── RLHF signal ───────────────────────────────────────────────────────────
    print()
    print("=" * 72)
    print("RLHF Signal (last 20 records)")
    print("=" * 72)
    signals = analyse_feedback()

    if "status" in signals:
        print(f"Status      : {signals['status']} ({signals['count']} records — need 5+)")
    else:
        print(f"Avg rating  : {signals['avg_stars']} / 5  "
              f"(normalised: {signals['avg_rating']})")
        print(f"Sample size : {signals['sample_size']}")
        print(f"Adaptation  : {signals['adapt']}")
        print(f"Action      : {signals['action']}")

        comments = signals.get("comments", [])
        if comments:
            print()
            print("Qualitative comments:")
            for c in comments:
                stars = "★" * c["rating"] + "☆" * (5 - c["rating"])
                print(f"  [{stars}]  {c['comment']}")
        else:
            print()
            print("Qualitative comments: (none provided)")

    # ── Adaptive policy update (LLM step) ────────────────────────────────────
    print()
    print("=" * 72)
    print("Adaptive Policy Update  (GPT-4o-mini)")
    print("=" * 72)

    all_comments = signals.get("comments", []) if "status" not in signals else []
    result = update_adaptive_policy(all_comments)

    status = result["status"]
    if status == "skipped":
        print(f"SKIPPED — {result.get('reason', '')}")
        print("  Need at least 2 low-rated comments (≤3★) with text to generate patterns.")
    elif status == "llm_unavailable":
        print(f"⚠  LLM call failed: {result.get('reason', '')}")
        print("  Adaptive policy not updated.")
        print("  Top up the API budget and re-run this script.")
    else:
        changelog = result.get("changelog", [])
        if changelog:
            for line in changelog:
                print(line)
        else:
            print("  No new patterns detected in low-rated comments.")

    # ── Current adaptive policy summary ──────────────────────────────────────
    print()
    print("=" * 72)
    print("Active Adaptive Policy Entries")
    print("=" * 72)
    entries = _load_adaptive_policy()
    active = [e for e in entries if e.get("active", True)]
    if not active:
        print("(none — policy file is empty)")
    else:
        for e in active:
            src = e.get("source", "unknown")
            print(f"  [{src}]  {e['id']}  (triggers: {e.get('trigger_count', 0)})")
            print(f"    {e['instruction']}")
            print()


if __name__ == "__main__":
    main()
